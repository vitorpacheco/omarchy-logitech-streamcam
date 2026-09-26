from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from backend import streamcam as camera
FIXTURE = (ROOT / "tests/fixtures/streamcam-controls.txt").read_text()
DEVICE = {"path": "/dev/video0", "node": "/dev/video0", "name": "Logitech StreamCam"}


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.controls = {c["name"]: c for c in camera.parse_controls(FIXTURE)}

    def test_real_hardware_fixture(self):
        self.assertEqual(len(self.controls), 17)
        self.assertEqual(self.controls["pan_absolute"]["min"], -36000)
        self.assertEqual(self.controls["pan_absolute"]["step"], 3600)
        self.assertFalse(self.controls["white_balance_temperature"]["writable"])
        self.assertEqual(self.controls["focus_automatic_continuous"]["max"], 1)

    def test_sparse_menu_rejects_holes(self):
        control = self.controls["auto_exposure"]
        self.assertEqual([o["value"] for o in control["options"]], [1, 3])
        camera.validate_value(control, 1)
        with self.assertRaises(camera.CameraError):
            camera.validate_value(control, 2)

    def test_integer_range_and_step(self):
        control = self.controls["pan_absolute"]
        for value in (-36000, 0, 3600, 36000):
            camera.validate_value(control, value)
        for value in (-36001, 36001, 1):
            with self.assertRaises(camera.CameraError):
                camera.validate_value(control, value)

    def test_inactive_control_is_not_written(self):
        with patch.object(camera, "discover", return_value=([DEVICE], [])), patch.object(camera, "v4l2", return_value=FIXTURE) as run:
            with self.assertRaises(camera.CameraError):
                camera.execute("set", control_name="focus_absolute", value=10)
            self.assertEqual(run.call_count, 1)

    def test_unknown_control_and_injection_are_rejected(self):
        with patch.object(camera, "discover", return_value=([DEVICE], [])), patch.object(camera, "v4l2", return_value=FIXTURE) as run:
            with self.assertRaises(camera.CameraError):
                camera.execute("set", control_name="brightness=10,contrast", value=10)
            self.assertEqual(run.call_count, 1)

    def test_set_refreshes_automatic_dependencies(self):
        updated = FIXTURE.replace("value=4000 flags=inactive, has-min-max", "value=4000 flags=has-min-max")
        with patch.object(camera, "discover", return_value=([DEVICE], [])), patch.object(camera, "v4l2", side_effect=[FIXTURE, "", updated]) as run:
            state = camera.execute("set", control_name="white_balance_automatic", value=0)
            self.assertIn(unittest.mock.call("/dev/video0", "--set-ctrl=white_balance_automatic=0"), run.call_args_list)
            self.assertTrue(next(c for c in state["controls"] if c["name"] == "white_balance_temperature")["writable"])

    def test_flags_and_unknown_type(self):
        for kind, flag in [("int", "read-only"), ("int", "grabbed"), ("int", "disabled"), ("string", "")]:
            control = camera.parse_controls(f"future_control 0x00123456 ({kind}) : min=0 max=10 value=2 flags={flag}")[0]
            self.assertFalse(control["writable"])

    def test_disconnected_camera_does_not_select_another(self):
        with self.assertRaises(camera.CameraError):
            camera.select_device([DEVICE], "/dev/video99")
        with patch.object(camera, "discover", return_value=([], [])):
            self.assertIsNone(camera.execute("inspect")["device"])
            with self.assertRaises(camera.CameraError):
                camera.execute("set", control_name="brightness", value=0)

    def test_timeout_missing_tool_and_driver_failure(self):
        for failure in [FileNotFoundError(), subprocess.TimeoutExpired("v4l2-ctl", 8)]:
            with patch.object(camera.subprocess, "run", side_effect=failure):
                with self.assertRaises(camera.CameraError):
                    camera.v4l2("/dev/video0", "--info")
        with patch.object(camera.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "Permission denied")):
            with self.assertRaisesRegex(camera.CameraError, "Permission denied"):
                camera.v4l2("/dev/video0", "--info")

    def test_subprocess_uses_argv_and_fixed_locale(self):
        with patch.object(camera.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as run:
            self.assertEqual(camera.v4l2("/dev/a path", "--info"), "ok")
            self.assertEqual(run.call_args.args[0], ["v4l2-ctl", "--device", "/dev/a path", "--info"])
            self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")
            self.assertNotIn("shell", run.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
