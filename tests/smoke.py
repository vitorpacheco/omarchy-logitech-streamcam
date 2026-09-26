#!/usr/bin/env python3
"""Load the plugin in an isolated Quickshell instance; --preview opens the camera."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Also check live frames from a connected StreamCam")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
    with tempfile.TemporaryDirectory(prefix="streamcam-smoke-") as directory:
        temp = Path(directory)
        # Only the disposable test shell uses symlinks, never the plugin itself.
        for name in ("Commons", "Ui"):
            (temp / name).symlink_to(shell / name, target_is_directory=True)
        for name in ("Widget.qml", "ControlRow.qml", "Preview.qml", "I18n.qml", "translations.json"):
            shutil.copy(repo / name, temp / name)
        shutil.copytree(repo / "backend", temp / "backend")
        (temp / "shell.qml").write_text("""import QtQuick
import Quickshell
ShellRoot {
  Widget { id: widget }
  I18n { id: translations }
  Timer { interval: 300; running: true; onTriggered: widget.open() }
  Timer { interval: 1500; running: true; onTriggered: widget.previewRequested = PREVIEW }
  Timer { interval: 6500; running: true; onTriggered: {
    console.log("CONTROLS_OK", widget.error === "" && widget.cameraState.controls.length > 0)
    console.log("VISIBLE_CONTROLS_OK", widget.visibleControls.length > 0)
    console.log("LOCALE_OK", widget.cameraState.controls.some(c => c.name === "brightness" && c.label === translations.t("Brightness")))
    console.log("PREVIEW_OK", widget.previewHasFrames, widget.previewError)
    widget.close()
    console.log("CLOSED_OK", !widget.opened && !widget.previewRequested && !widget.previewHasFrames)
  } }
  Timer { interval: 7500; running: true; onTriggered: widget.open() }
  Timer { interval: 8500; running: true; onTriggered: {
    console.log("REOPEN_OK", widget.opened && !widget.previewRequested && widget.error === "")
    widget.close(); Qt.quit()
  } }
}
""".replace("PREVIEW }", str(args.preview).lower() + " }"))
        result = subprocess.run(["quickshell", "-p", str(temp), "--no-color"], capture_output=True, text=True, timeout=20)
        output = result.stdout + result.stderr
        print(output)
        required = ["CONTROLS_OK true", "VISIBLE_CONTROLS_OK true", "LOCALE_OK true", "CLOSED_OK true", "REOPEN_OK true"]
        if args.preview:
            required.append("PREVIEW_OK true")
        if result.returncode or not all(marker in output for marker in required):
            raise SystemExit("Smoke test failed; inspect the log above. A connected StreamCam and Wayland session are required.")


if __name__ == "__main__":
    main()
