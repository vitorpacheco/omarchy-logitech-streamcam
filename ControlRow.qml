import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui as Ui

ColumnLayout {
  id: root
  I18n { id: i18n }
  required property var control
  property bool busy: false
  signal setValue(int value)
  readonly property bool writable: control.writable && !busy
  spacing: Style.space(6)

  RowLayout {
    Layout.fillWidth: true
    Text {
      Layout.fillWidth: true
      text: root.control.label
      wrapMode: Text.Wrap
      color: Color.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.bold: true
    }
    Ui.PanelActionButton {
      iconText: "󰑓"
      tooltipText: i18n.t("Restore default: {value}", { value: root.control.default })
      focusable: true
      enabled: root.writable && root.control.default !== null
      onClicked: root.setValue(root.control.default)
    }
  }

  Ui.Toggle {
    Layout.fillWidth: true
    visible: root.control.type === "bool"
    enabled: root.writable
    label: root.control.value ? i18n.t("On") : i18n.t("Off")
    checked: root.control.value === 1
    onClicked: root.setValue(root.control.value ? 0 : 1)
  }

  Ui.Dropdown {
    Layout.fillWidth: true
    visible: root.control.type === "menu" || root.control.type === "intmenu"
    enabled: root.writable
    opacity: enabled ? 1 : 0.5
    options: root.control.options
    value: String(root.control.value)
    onChanged: function(value) { root.setValue(Number(value)) }
  }

  RowLayout {
    Layout.fillWidth: true
    visible: root.control.type === "int"
    opacity: root.writable ? 1 : 0.5
    Ui.PanelSlider {
      id: slider
      Layout.fillWidth: true
      enabled: root.writable
      minimum: root.control.min
      maximum: root.control.max
      step: root.control.step
      integer: true
      value: root.control.value === null ? 0 : root.control.value
      activeFocusOnTab: true
      // PanelSlider does not snap pointer movement to step on its own.
      function snap(value) {
        return Math.max(minimum, Math.min(maximum, minimum + Math.round((value - minimum) / step) * step))
      }
      onReleased: function(value) { root.setValue(snap(value)) }
      Keys.onLeftPressed: root.setValue(Math.max(minimum, value - step))
      Keys.onRightPressed: root.setValue(Math.min(maximum, value + step))
    }
    Text {
      Layout.preferredWidth: Style.space(65)
      horizontalAlignment: Text.AlignRight
      text: slider.dragging ? slider.snap(slider.liveValue) : root.control.value
      color: Color.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
    }
  }

  Text {
    Layout.fillWidth: true
    visible: !root.control.writable
    text: root.control.flags.indexOf("inactive") !== -1
      ? i18n.t("Disable the corresponding automatic mode to adjust.")
      : i18n.t("Not writable: {reason}", { reason: root.control.flags.join(", ") || root.control.type })
    wrapMode: Text.Wrap
    color: Color.foreground
    opacity: 0.6
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
  }
}
