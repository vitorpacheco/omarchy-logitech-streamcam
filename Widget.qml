import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui as Ui

Ui.Panel {
  id: root
  I18n { id: i18n }
  moduleName: "io.github.vitorpacheco.streamcam"
  manageIpc: false

  property var cameraState: ({ devices: [], controls: [], device: null, warnings: [] })
  property string selectedDevice: ""
  property string group: "image"
  property string error: ""
  property string formats: ""
  property bool previewRequested: false
  readonly property bool previewHasFrames: previewLoader.item ? previewLoader.item.hasFrames : false
  readonly property string previewError: previewLoader.status === Loader.Error
    ? i18n.t("Preview unavailable. Install qt6-multimedia and qt6-multimedia-ffmpeg.")
    : (previewLoader.item ? previewLoader.item.errorMessage : "")
  readonly property bool busy: worker.running
  readonly property var visibleControls: cameraState.controls.filter(c => c.group === root.group)
  readonly property var deviceOptions: cameraState.devices.map(d => ({ value: d.path, label: d.name + " · " + d.node }))
  readonly property string helperPath: decodeURIComponent(Qt.resolvedUrl("backend/streamcam.py").toString().replace(/^file:\/\//, ""))

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  function request(action, name, value) {
    if (worker.running) return
    error = ""
    var args = ["/usr/bin/python3", "-I", root.helperPath, action]
    if (selectedDevice) args.push("--device", selectedDevice)
    if (action === "set") args.push("--control", name, "--value", String(value))
    worker.command = args
    worker.running = true
  }

  function refresh() {
    if (busy) return
    selectedDevice = ""
    formats = ""
    request("inspect")
  }

  onOpenedChanged: {
    if (opened) request("inspect")
    else previewRequested = false
  }
  onSelectedDeviceChanged: previewRequested = false

  Process {
    id: worker
    clearEnvironment: true
    environment: ({ PATH: "/usr/bin", LANG: i18n.language === "pt" ? "pt_BR.UTF-8" : "C.UTF-8", LC_ALL: i18n.language === "pt" ? "pt_BR.UTF-8" : "C.UTF-8" })
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var result = JSON.parse(text)
          if (!result.ok) {
            root.error = result.error
            // Stale controls must never remain actionable after disconnect.
            root.cameraState = { devices: [], controls: [], device: null, warnings: [] }
            return
          }
          root.cameraState = result
          root.selectedDevice = result.device ? result.device.path : ""
          if (result.formats !== undefined) root.formats = result.formats
        } catch (e) {
          root.error = i18n.t("Invalid camera helper response. Check Python and v4l-utils.")
        }
      }
    }
    stderr: StdioCollector { id: errors; waitForEnd: true }
    onExited: function(code) {
      if (code !== 0 && root.error === "") root.error = errors.text.trim() || i18n.t("Could not run the camera helper.")
    }
  }

  Ui.WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰄀"
    tooltipText: "Logitech StreamCam"
    onPressed: function(buttonCode) { if (buttonCode === Qt.LeftButton) root.toggle() }
  }

  Ui.KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: content
    contentWidth: panel.fittedContentWidth(Style.space(460))
    contentHeight: panel.fittedContentHeight(Style.space(root.previewRequested ? 790 : 590))

    FocusScope {
      id: content
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.close()

      ColumnLayout {
        anchors.fill: parent
        spacing: Style.space(12)

        RowLayout {
          Layout.fillWidth: true
          ColumnLayout {
            Layout.fillWidth: true
            Text {
              text: "STREAMCAM"
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.subtitle
              font.bold: true
              font.letterSpacing: 2
            }
            Text {
              text: root.busy ? i18n.t("Querying camera…") : i18n.t("Settings applied directly to the webcam")
              color: Color.foreground
              opacity: 0.65
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
          Ui.PanelActionButton {
            iconText: "󰑐"
            tooltipText: i18n.t("Detect cameras and refresh values")
            focusable: true
            enabled: !root.busy
            onClicked: root.refresh()
          }
          Ui.PanelActionButton {
            iconText: "󰅖"
            tooltipText: i18n.t("Close")
            focusable: true
            onClicked: root.close()
          }
        }

        Text {
          Layout.fillWidth: true
          visible: root.error !== "" || root.cameraState.warnings.length > 0
          text: root.error || root.cameraState.warnings.join("\n")
          textFormat: Text.PlainText
          wrapMode: Text.Wrap
          color: Color.urgent
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
        }

        Text {
          Layout.fillWidth: true
          visible: !root.cameraState.device && !root.busy && !root.error
          text: i18n.t("Connect a Logitech StreamCam and click refresh.")
          wrapMode: Text.Wrap
          color: Color.foreground
          font.family: Style.font.family
          font.pixelSize: Style.font.body
        }

        Ui.Dropdown {
          Layout.fillWidth: true
          visible: root.cameraState.devices.length > 1
          enabled: !root.busy
          options: root.deviceOptions
          value: root.selectedDevice
          onChanged: function(value) {
            root.selectedDevice = value
            root.formats = ""
            root.request("inspect")
          }
        }

        Ui.Button {
          Layout.fillWidth: true
          visible: !!root.cameraState.device
          focusable: true
          bordered: true
          text: root.previewRequested ? i18n.t("Turn preview off") : i18n.t("Enable live preview")
          iconText: "󰄀"
          onClicked: root.previewRequested = !root.previewRequested
        }

        Loader {
          id: previewLoader
          Layout.fillWidth: true
          Layout.preferredHeight: Style.space(200)
          visible: active
          active: root.previewRequested && root.opened && !!root.cameraState.device
          source: Qt.resolvedUrl("Preview.qml")
          onLoaded: item.deviceNode = root.cameraState.device.node
        }

        Text {
          Layout.fillWidth: true
          visible: root.previewRequested && root.previewError !== ""
          text: root.previewError
          textFormat: Text.PlainText
          wrapMode: Text.Wrap
          color: Color.urgent
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
        }

        Ui.Dropdown {
          Layout.fillWidth: true
          visible: !!root.cameraState.device
          options: [{ value: "image", label: i18n.t("Image") },
            { value: "color", label: i18n.t("Color") },
            { value: "exposure", label: i18n.t("Exposure") },
            { value: "framing", label: i18n.t("Framing") },
            { value: "other", label: i18n.t("Other") },
            { value: "information", label: i18n.t("Information") }]
          value: root.group
          onChanged: function(value) {
            root.group = value
            if (value === "information" && !root.busy) root.request("formats")
          }
        }

        Controls.ScrollView {
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          contentWidth: availableWidth
          Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff

          Column {
            width: parent.width
            spacing: Style.space(14)

            Repeater {
              model: root.group === "information" ? [] : root.visibleControls
              delegate: ControlRow {
                required property var modelData
                width: parent.width
                control: modelData
                busy: root.busy
                onSetValue: function(value) { root.request("set", modelData.name, value) }
              }
            }

            Text {
              width: parent.width
              visible: root.group !== "information" && root.visibleControls.length === 0 && !!root.cameraState.device
              text: i18n.t("No controls in this category.")
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.body
            }

            Text {
              width: parent.width
              visible: root.group === "information" && !!root.cameraState.device
              text: root.cameraState.device
                ? root.cameraState.device.node + " · USB " + (root.cameraState.device.usbSpeed || "?") + " Mbit/s\n\n"
                  + i18n.t("Resolution and frame rate are chosen by the capture application. The list below shows the modes advertised on this connection.\n\n")
                  + (root.cameraState.device.usbSpeed === "480" ? i18n.t("USB 2.0: connect through a USB 3 port and connection path to check for 60 fps modes.\n\n") : "")
                  + i18n.t("Pan/tilt and zoom depend on the crop supported by the firmware; there is no motorized movement.\n\n")
                  + root.formats : ""
              textFormat: Text.PlainText
              wrapMode: Text.Wrap
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
            }
          }
        }

        Text {
          Layout.fillWidth: true
          text: i18n.t("Preview uses the camera while the panel is open.\nRefresh to read changes made by other applications.")
          wrapMode: Text.Wrap
          color: Color.foreground
          opacity: 0.6
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
        }
      }
    }
  }
}
