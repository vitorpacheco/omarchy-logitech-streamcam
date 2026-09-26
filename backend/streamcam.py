#!/usr/bin/python3 -I
"""Small JSON boundary between the Omarchy widget and v4l2-ctl (no capture)."""

import argparse
import json
import importlib.util
from itertools import islice
import time
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from .i18n import tr
    from .process import run_bounded, trusted_v4l2, OutputLimitError
else:
    # -I excludes the script directory from sys.path. Load only these exact
    # plugin-owned modules; never add a search directory for other imports.
    def sibling(name):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().with_name(name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    tr = sibling("i18n").tr
    processes = sibling("process")
    run_bounded, trusted_v4l2, OutputLimitError = processes.run_bounded, processes.trusted_v4l2, processes.OutputLimitError

MAX_CONTROLS = 128
MAX_OPTIONS = 64
MAX_FIELD = 512
MAX_JSON = 512 * 1024
REQUEST_DEADLINE = None
LIMIT_MESSAGE = "Camera response exceeded the safety limits."


class CameraError(Exception):
    pass


# Labels only: availability, ranges, menu entries and flags always come from V4L2.
LABELS = {
    "brightness": ("Brightness", "image"),
    "contrast": ("Contrast", "image"),
    "saturation": ("Saturation", "image"),
    "gain": ("Gain", "image"),
    "sharpness": ("Sharpness", "image"),
    "backlight_compensation": ("Backlight compensation", "image"),
    "power_line_frequency": ("Anti-flicker", "image"),
    "white_balance_automatic": ("Automatic white balance", "color"),
    "white_balance_temperature_auto": ("Automatic white balance", "color"),
    "white_balance_temperature": ("Color temperature (K)", "color"),
    "auto_exposure": ("Exposure mode", "exposure"),
    "exposure_auto": ("Exposure mode", "exposure"),
    "exposure_time_absolute": ("Exposure (100 µs units)", "exposure"),
    "exposure_absolute": ("Exposure (100 µs units)", "exposure"),
    "exposure_dynamic_framerate": ("Allow variable frame rate", "exposure"),
    "exposure_auto_priority": ("Allow variable frame rate", "exposure"),
    "focus_automatic_continuous": ("Autofocus", "framing"),
    "focus_auto": ("Autofocus", "framing"),
    "focus_absolute": ("Manual focus", "framing"),
    "zoom_absolute": ("Zoom", "framing"),
    "pan_absolute": ("Horizontal pan", "framing"),
    "tilt_absolute": ("Vertical tilt", "framing"),
}


def v4l2(device, *args):
    try:
        timeout = min(8, REQUEST_DEADLINE - time.monotonic()) if REQUEST_DEADLINE is not None else 8
        result = run_bounded([trusted_v4l2(), "--device", device, *args], timeout=timeout)
    except OutputLimitError as exc:
        raise CameraError(tr(LIMIT_MESSAGE)) from exc
    except FileNotFoundError as exc:
        raise CameraError(tr("Install v4l-utils: omarchy pkg add v4l-utils")) from exc
    except subprocess.TimeoutExpired as exc:
        raise CameraError(tr("The camera timed out. Reconnect it and try again.")) from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:1024]
        raise CameraError(tr("Failed on {device}: {detail}", device=device, detail=detail))
    return result.stdout


def parse_controls(output):
    if len(output.encode("utf-8")) > 256 * 1024:
        raise CameraError(tr(LIMIT_MESSAGE))
    controls = []
    current = None
    for line in output.splitlines():
        if len(line) > MAX_FIELD:
            raise CameraError(tr(LIMIT_MESSAGE))
        match = re.match(r"\s*(\w+)\s+0x[0-9a-fA-F]+\s+\(([^)]+)\)\s*:\s*(.*)", line)
        if match:
            name, kind, fields = match.groups()
            values = {k: int(v) for k, v in re.findall(r"\b(min|max|step|default|value)=(-?\d+)", fields)}
            flags = fields.partition("flags=")[2].split(",") if "flags=" in fields else []
            flags = [flag.strip() for flag in flags]
            label, group = LABELS.get(name, (name.replace("_", " "), "other"))
            current = {
                "name": name, "type": kind.strip(), "label": tr(label), "group": group,
                "min": values.get("min", 0), "max": values.get("max", 1),
                "step": values.get("step", 1), "default": values.get("default"),
                "value": values.get("value"), "flags": flags, "options": [],
                "writable": not set(flags).intersection({"inactive", "disabled", "read-only", "grabbed"})
                and kind.strip() in {"int", "bool", "menu", "intmenu"}
                and "value" in values,
            }
            if len(controls) >= MAX_CONTROLS:
                raise CameraError(tr(LIMIT_MESSAGE))
            controls.append(current)
        elif current:
            option = re.match(r"\s+(-?\d+):\s*(.+)", line)
            if option:
                if len(current["options"]) >= MAX_OPTIONS:
                    raise CameraError(tr(LIMIT_MESSAGE))
                value, label = option.groups()
                current["options"].append({"value": int(value), "label": tr(label)})
    return controls


def read_field(path):
    with path.open() as stream:
        value = stream.read(MAX_FIELD + 1)
    if len(value) > MAX_FIELD:
        raise CameraError(tr(LIMIT_MESSAGE))
    return value.strip()


def discover():
    devices, errors = [], []
    for node in islice(Path("/sys/class/video4linux").glob("video*"), 32):
        try:
            name = read_field(node / "name")
            if "streamcam" not in name.lower():
                continue
            # UVC exposes a metadata node as well; it has no video format.
            path = "/dev/" + node.name
            info = v4l2(path, "--info")
            device_caps = re.search(r"Device Caps\s*:\s*(0x[\da-fA-F]+)", info)
            if device_caps:
                caps = int(device_caps.group(1), 16)
                if not caps & 1:  # V4L2_CAP_VIDEO_CAPTURE
                    continue
            else:
                v4l2(path, "--get-fmt-video")
            stable = next((str(p) for p in islice(Path("/dev/v4l/by-id").glob("*"), 64)
                           if p.resolve() == Path(path)), path)
            usb = node.resolve()
            speed = ""
            for parent in usb.parents:
                if (parent / "speed").exists():
                    speed = read_field(parent / "speed")
                    break
            if len(stable) > MAX_FIELD:
                raise CameraError(tr(LIMIT_MESSAGE))
            devices.append({"path": stable, "node": path, "name": name, "usbSpeed": speed})
        except (OSError, CameraError) as exc:
            if len(errors) < 8:
                errors.append(str(exc)[:1024])
    return devices, errors


def select_device(devices, requested):
    if requested:
        for device in devices:
            if Path(requested).resolve() == Path(device["path"]).resolve():
                return device
        raise CameraError(tr("The selected StreamCam was disconnected or is inaccessible. Refresh the list."))
    return devices[0] if devices else None


def validate_value(control, value):
    if not control["writable"]:
        raise CameraError(tr("The driver locked this control. Disable the corresponding automatic mode, if applicable."))
    if control["type"] in {"menu", "intmenu"}:
        if value not in [option["value"] for option in control["options"]]:
            raise CameraError(tr("This option is unavailable on this device."))
    elif not (control["min"] <= value <= control["max"]) or (value - control["min"]) % max(1, control["step"]):
        raise CameraError(tr("The value is outside the supported range or step."))


def execute(action, requested="", control_name=None, value=None):
    devices, errors = discover()
    device = select_device(devices, requested)
    state = {"ok": True, "devices": devices, "device": device, "controls": [], "warnings": errors}
    if device is None:
        if action == "set":
            raise CameraError(tr("No Logitech StreamCam found."))
        return state
    path = device["path"]
    controls = parse_controls(v4l2(path, "--list-ctrls-menus"))
    if not controls:
        raise CameraError(tr("The driver returned no V4L2 controls for this camera."))
    if action == "set":
        control = next((c for c in controls if c["name"] == control_name), None)
        if control is None:
            raise CameraError(tr("Control not found on this camera."))
        validate_value(control, value)
        v4l2(path, f"--set-ctrl={control_name}={value}")
        # Automatic modes change the inactive flags of dependent controls.
        controls = parse_controls(v4l2(path, "--list-ctrls-menus"))
    state["controls"] = controls
    if action == "formats":
        state["formats"] = v4l2(path, "--list-formats-ext")
    return state


def encode_result(result):
    encoded = json.dumps(result, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_JSON:
        raise CameraError(tr(LIMIT_MESSAGE))
    return encoded


def main():
    global REQUEST_DEADLINE
    REQUEST_DEADLINE = time.monotonic() + 20
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "set", "formats"])
    parser.add_argument("--device", default="")
    parser.add_argument("--control")
    parser.add_argument("--value", type=int)
    args = parser.parse_args()
    if args.action == "set" and (not args.control or args.value is None):
        parser.error(tr("set requires --control and --value"))
    try:
        result = encode_result(execute(args.action, args.device, args.control, args.value))
    except (CameraError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:1024]}, ensure_ascii=False))
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
