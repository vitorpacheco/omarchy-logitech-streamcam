# Logitech StreamCam for Omarchy

A native **Omarchy Quattro (4.x)** bar widget for controlling the StreamCam through its Linux driver, with optional live preview. Tested on **Omarchy 4.0.4-1** with a real StreamCam. The manifest follows the [official plugin development guide](https://plugins.omarchy.org/develop.html) and [shell contract](https://github.com/omacom/omarchy/blob/quattro/shell/README.md).

## Installation

Required: Omarchy with `omarchy-shell`/Quickshell, Python 3, and `v4l-utils`. The helper uses only the Python standard library. The plugin needs no pip packages, background service, root privileges, or network access.

Live preview additionally requires **qt6-multimedia** and **qt6-multimedia-ffmpeg**. Camera controls remain available without these optional modules.

```bash
omarchy pkg add v4l-utils python
# Optional live preview dependencies:
omarchy pkg add qt6-multimedia qt6-multimedia-ffmpeg
omarchy plugin add https://github.com/vitorpacheco/omarchy-logitech-streamcam.git --enable
```

Installation, updates, and removal use the native Omarchy plugin manager. The plugin has no custom installer, installation hooks, or automatic dependency installation. Installing system packages may require administrator authentication; runtime camera access uses your existing session permissions.

```bash
omarchy plugin update io.github.vitorpacheco.streamcam
omarchy bar move io.github.vitorpacheco.streamcam --section right
omarchy-shell shell summon io.github.vitorpacheco.streamcam '{}'
omarchy-shell shell hide io.github.vitorpacheco.streamcam
omarchy plugin disable io.github.vitorpacheco.streamcam
omarchy plugin remove io.github.vitorpacheco.streamcam
```

## Language

The plugin automatically selects **English** or **Portuguese** from the system message locale. It uses the first nonempty variable in this order: **`LC_ALL` → `LC_MESSAGES` → `LANG`**. Portuguese locales such as `pt`, `pt_BR.UTF-8`, and `pt_PT.UTF-8` select Portuguese; English, unsupported locales, `C`/`POSIX`, and an unset locale use English.

A missing Portuguese translation also falls back to English. The interface, control labels, known menu options, and helper messages share `translations.json`. Internal category IDs remain independent of their translated labels. Driver diagnostics, raw video-format output, and unknown driver-provided labels remain in their original language; V4L2 output is deliberately queried in the C locale for reliable parsing. Static manifest metadata is English.

The interface uses the environment inherited by the Omarchy shell. After changing your system language, restart the shell or log in again. Setting a locale only on an `omarchy-shell` IPC command does not change the running shell's environment.

You can check helper localization without changing the system language:

```bash
LC_ALL=pt_BR.UTF-8 /usr/bin/python3 -I backend/streamcam.py inspect
LC_ALL=en_US.UTF-8 /usr/bin/python3 -I backend/streamcam.py inspect
LC_ALL=de_DE.UTF-8 /usr/bin/python3 -I backend/streamcam.py inspect  # English fallback
```

## Usage

Click the camera icon in the bar, choose a category, and adjust a control. Sliders apply their value when released; arrow keys adjust a focused slider. The reset button beside each control restores the default reported by the driver. Escape or clicking outside closes the panel.

**Enable live preview** displays the selected camera inside the panel while preserving its aspect ratio. Preview prefers a format up to 720p with at least 24 fps when available. **Turn preview off**, closing the panel, or switching cameras releases capture. Preview stays off when the panel is reopened. It does not record video, take photos, or capture audio. If another application occupies the camera, the panel shows an error; turn preview off before joining a call that requires exclusive camera access.

Values are read when the panel opens and after every change. Click refresh to detect reconnections or changes made by other applications. A device selector appears when multiple StreamCams are connected. The helper prefers stable `/dev/v4l/by-id` paths and ignores metadata nodes.

| Category | Confirmed controls |
| --- | --- |
| Image | Brightness, contrast, saturation, gain, sharpness, backlight compensation, 50/60 Hz anti-flicker |
| Color | Automatic white balance and manual color temperature, 2000–7500 K |
| Exposure | Automatic/manual mode, exposure time, and variable frame rate |
| Framing | Autofocus, manual focus, zoom, pan, and tilt |
| Information | USB speed and advertised formats, resolutions, and frame rates |

This device exposes **17 controls**. Availability, ranges, steps, defaults, and menu options are discovered at runtime. Driver-locked controls are disabled in the interface; turn off the corresponding automatic mode before adjusting manual focus, exposure, or white balance. Additional supported control types appear under “Other”.

## Limitations

- The inspected connection operates at **USB 2.0 (480 Mbit/s)** and advertises MJPEG up to **1080p30**, or YUYV up to **1080p5**. Logitech advertises 1080p60 with a suitable USB 3 connection; reconnect and check the advertised modes under Information.
- Recording and call resolution/frame rate are chosen by the application doing the capture. The preview format applies only to its viewing session.
- Zoom, pan, and tilt depend on firmware cropping; enumeration does not guarantee a visible effect at every zoom level. The StreamCam has no motorized movement.
- No Linux controls were exposed for the LED, HDR, rotation, mirroring, face tracking, or Logitech Capture auto-framing. Use the system audio panel for microphone controls.
- Camera settings are shared between applications. There is no automatic reapplication or persistent preset restoration after restart/disconnection; firmware or another application may reset values.

Full control ranges, Logitech/kernel sources, and research details are recorded in [docs/research.md](docs/research.md) (Portuguese).

## Diagnostics and development

```bash
/usr/bin/python3 -I backend/streamcam.py inspect
/usr/bin/python3 -I backend/streamcam.py formats
# This command changes the camera's brightness:
/usr/bin/python3 -I backend/streamcam.py set --device /dev/video0 --control brightness --value 128
python3 -m unittest discover -s tests -v
omarchy plugin validate .
qmllint -I /usr/share/omarchy/shell Widget.qml ControlRow.qml Preview.qml I18n.qml
# Isolated visual test: opens the camera briefly.
python3 tests/smoke.py --preview
```

`inspect` and `formats` are read-only. The helper outputs JSON; operation failures return `ok: false` and exit status 1. Unsupported ranges, steps, and menu options are rejected before writing. Each V4L2 call uses separate arguments and no shell. It has an eight-second deadline, bounded stdout (256 KiB) and stderr (16 KiB), and process-group cleanup on success or failure. Cleanup sends TERM, waits at most 100 ms before KILL, and reaps the leader only after signaling the group. The helper has a 20-second request budget for V4L2 calls.

The QML worker runs `/usr/bin/python3 -I` with a cleared environment containing only a fixed `PATH` and the selected locale. It loads helper modules by their exact plugin-relative paths. The backend resolves only `/usr/bin/v4l2-ctl`, verifies that the resolved executable and its ancestor directories are root-owned and not group/other-writable, and executes that exact path with only `PATH=/usr/bin`, `LANG=C`, and `LC_ALL=C`. No inherited Python or loader variables reach either child process.

Responses are limited to 128 controls, 64 options per control, 512-character control lines/device fields, 32 device nodes, 64 stable-path candidates per node, eight diagnostics of at most 1,024 characters each, and 512 KiB of serialized JSON. Oversized control responses fail with a translated error instead of silently applying a partial control definition.

The smoke test requires a Wayland session and a connected StreamCam. It runs a temporary Quickshell instance without installing the plugin or changing `shell.json`. Omit `--preview` to test only control reads and panel lifecycle. See the [validation record](docs/validation.md) (Portuguese).

If the camera does not appear, check `v4l2-ctl --list-devices` and your session's permissions on `/dev/video*`. QML logs are available with `quickshell log -p /usr/share/omarchy/shell --tail 100`.

Architecture: `Widget.qml` uses Omarchy's `qs.Ui.Panel`, `KeyboardPanel`, and themed components; `ControlRow.qml` renders enumerated controls; `backend/streamcam.py` discovers devices, validates changes, and wraps `v4l2-ctl`. `Preview.qml` loads on demand and uses Qt Multimedia's `Camera`, `CaptureSession`, and `VideoOutput`. `I18n.qml` and `backend/i18n.py` read the shared translation catalog. The manifest declares one `bar-widget` with an internal panel whose lifecycle is routed by the shell.

MIT license.
