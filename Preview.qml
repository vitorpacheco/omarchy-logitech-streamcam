import QtQuick
import QtMultimedia
import qs.Commons

// Loaded on demand so missing Qt Multimedia never prevents camera controls.
Rectangle {
  id: root
  I18n { id: i18n }
  property string deviceNode: ""
  property string errorMessage: ""
  property bool hasFrames: false
  color: "#101010"
  clip: true

  function startSelectedCamera() {
    firstFrameTimeout.stop()
    camera.stop()
    hasFrames = false
    errorMessage = ""
    if (!deviceNode) return
    for (var i = 0; i < devices.videoInputs.length; i++) {
      var device = devices.videoInputs[i]
      // On Linux the V4L2 backend uses /dev/videoN as the camera ID.
      // Never fall back to the default camera (could be a different device).
      if (String(device.id) !== deviceNode) continue
      camera.cameraDevice = device
      // Keep preview modest: prefer a <=720p format with >=24fps.
      var best = null
      for (var j = 0; j < device.videoFormats.length; j++) {
        var format = device.videoFormats[j]
        if (format.resolution.width <= 1280 && format.resolution.height <= 720
            && format.maxFrameRate >= 24
            && (!best || format.resolution.width > best.resolution.width
                || (format.resolution.width === best.resolution.width && format.maxFrameRate > best.maxFrameRate))) best = format
      }
      if (best) camera.cameraFormat = best
      camera.start()
      firstFrameTimeout.restart()
      return
    }
    errorMessage = i18n.t("This StreamCam is unavailable for preview in Qt Multimedia.")
  }

  onDeviceNodeChanged: startSelectedCamera()
  Component.onDestruction: camera.stop()

  MediaDevices {
    id: devices
    onVideoInputsChanged: root.startSelectedCamera()
  }

  Camera {
    id: camera
    active: false
    onErrorOccurred: function(error, errorString) {
      root.errorMessage = i18n.t("Preview unavailable: {detail}. If the camera is in use, close it in the other application and try again.", { detail: errorString })
      firstFrameTimeout.stop()
      camera.stop()
    }
  }

  CaptureSession {
    camera: camera
    videoOutput: video
    // No audio input, recorder or image capture.
  }

  VideoOutput {
    id: video
    anchors.fill: parent
    fillMode: VideoOutput.PreserveAspectFit
  }

  Connections {
    target: video.videoSink
    function onVideoFrameChanged() {
      if (video.sourceRect.width > 0) {
        root.hasFrames = true
        firstFrameTimeout.stop()
      }
    }
  }

  Timer {
    id: firstFrameTimeout
    interval: 8000
    onTriggered: {
      if (!root.hasFrames) {
        root.errorMessage = i18n.t("The camera sent no frames. It may be busy; turn preview off and try again.")
        camera.stop()
      }
    }
  }

  Text {
    anchors.centerIn: parent
    width: parent.width - Style.space(24)
    visible: !root.hasFrames
    text: root.errorMessage ? i18n.t("Preview unavailable") : i18n.t("Starting camera…")
    color: "#ffffff"
    wrapMode: Text.Wrap
    horizontalAlignment: Text.AlignHCenter
    font.family: Style.font.family
    font.pixelSize: Style.font.body
  }
}
