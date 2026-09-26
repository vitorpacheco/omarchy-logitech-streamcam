import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
  id: root
  readonly property string systemLocale: Quickshell.env("LC_ALL") || Quickshell.env("LC_MESSAGES") || Quickshell.env("LANG") || "C"
  readonly property string language: /^pt(?:[-_.@]|$)/i.test(systemLocale) ? "pt" : "en"
  readonly property var messages: {
    try { return JSON.parse(catalog.text()) } catch (e) { return {} }
  }
  property FileView catalog: FileView {
    path: Qt.resolvedUrl("translations.json")
    blockLoading: true
  }

  function t(message, values) {
    var selected = messages[language] || {}
    var english = messages.en || {}
    var text = selected[message] || english[message] || message
    for (var key in (values || {})) text = text.split("{" + key + "}").join(String(values[key]))
    return text
  }
}
