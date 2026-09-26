import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from backend import i18n, streamcam

ROOT = Path(__file__).resolve().parents[1]


class LocalizationTests(unittest.TestCase):
    def test_system_locale_selection(self):
        cases = [({}, "en"), ({"LANG": "pt_BR.UTF-8"}, "pt"),
                 ({"LANG": "pt_PT.UTF-8"}, "pt"), ({"LANG": "PT-br"}, "pt"),
                 ({"LANG": "pt@custom"}, "pt"), ({"LANG": "pt"}, "pt"),
                 ({"LANG": "en_GB.UTF-8"}, "en"), ({"LANG": "de_DE.UTF-8"}, "en"),
                 ({"LANG": "C.UTF-8"}, "en"), ({"LANG": "POSIX"}, "en"),
                 ({"LANG": "pt_BR.UTF-8", "LC_MESSAGES": "en_US.UTF-8"}, "en"),
                 ({"LANG": "en_US.UTF-8", "LC_MESSAGES": "pt_PT.UTF-8", "LC_ALL": ""}, "pt"),
                 ({"LANG": "pt_BR.UTF-8", "LC_MESSAGES": "pt", "LC_ALL": "C"}, "en")]
        for environment, expected in cases:
            with self.subTest(environment=environment):
                self.assertEqual(i18n.language(environment), expected)

    def test_catalog_and_placeholders_match(self):
        self.assertEqual(set(i18n.CATALOG["en"]), set(i18n.CATALOG["pt"]))
        for key, english in i18n.CATALOG["en"].items():
            self.assertTrue(i18n.CATALOG["pt"][key])
            self.assertEqual(re.findall(r"\{\w+\}", english), re.findall(r"\{\w+\}", i18n.CATALOG["pt"][key]))
        for label, _ in streamcam.LABELS.values():
            self.assertIn(label, i18n.CATALOG["en"])

    def test_missing_translation_and_parameter_fallback(self):
        with patch.dict(os.environ, {"LC_ALL": "pt_BR.UTF-8"}), patch.object(i18n, "CATALOG", {"en": {"Close": "Close"}, "pt": {}}):
            self.assertEqual(i18n.tr("Close"), "Close")
            self.assertEqual(i18n.tr("Unknown driver label"), "Unknown driver label")
        with patch.dict(os.environ, {"LC_ALL": "pt"}):
            self.assertEqual(i18n.tr("Restore default: {value}", value=128), "Restaurar padrão: 128")

    def test_controls_have_localized_labels_and_stable_ids(self):
        fixture = (ROOT / "tests/fixtures/streamcam-controls.txt").read_text()
        for locale, label in [("pt_BR.UTF-8", "Brilho"), ("pt_PT.UTF-8", "Brilho"), ("en_US.UTF-8", "Brightness"), ("fr_FR.UTF-8", "Brightness")]:
            with self.subTest(locale=locale), patch.dict(os.environ, {"LC_ALL": locale}):
                controls = streamcam.parse_controls(fixture)
                brightness = next(c for c in controls if c["name"] == "brightness")
                self.assertEqual(brightness["label"], label)
                self.assertEqual(brightness["group"], "image")
                exposure = next(c for c in controls if c["name"] == "auto_exposure")
                self.assertEqual(exposure["options"][0]["label"], "Manual" if locale.startswith("pt") else "Manual Mode")
                with self.assertRaisesRegex(streamcam.CameraError, "Valor fora" if locale.startswith("pt") else "outside"):
                    streamcam.validate_value(brightness, 999)

    @unittest.skipUnless(shutil.which("quickshell"), "Quickshell is needed for QML locale tests")
    def test_qml_and_python_locale_parity(self):
        with tempfile.TemporaryDirectory(prefix="streamcam-i18n-") as directory:
            temp = Path(directory)
            shutil.copy(ROOT / "I18n.qml", temp)
            catalog = json.loads((ROOT / "translations.json").read_text())
            del catalog["pt"]["Close"]  # Exercise a missing individual translation.
            (temp / "translations.json").write_text(json.dumps(catalog))
            (temp / "shell.qml").write_text('''import QtQuick
import Quickshell
ShellRoot {
  I18n { id: translations }
  Timer { interval: 100; running: true; onTriggered: {
    console.log("I18N_RESULT " + JSON.stringify({
      language: translations.language,
      label: translations.t("Brightness"),
      missing: translations.t("Close"),
      parameter: translations.t("Restore default: {value}", { value: 128 })
    }))
    Qt.quit()
  } }
}
''')
            cases = [{"LANG": "pt_BR.UTF-8"}, {"LANG": "pt_PT.UTF-8"},
                     {"LANG": "en_US.UTF-8"}, {"LANG": "fr_FR.UTF-8"}, {},
                     {"LANG": "pt", "LC_MESSAGES": "en_US.UTF-8"},
                     {"LANG": "en", "LC_MESSAGES": "pt", "LC_ALL": ""},
                     {"LANG": "pt", "LC_ALL": "C"}]
            for locale in cases:
                with self.subTest(locale=locale):
                    env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")}
                    env.update(locale)
                    env["QT_QPA_PLATFORM"] = "offscreen"
                    result = subprocess.run(["quickshell", "-p", str(temp), "--no-color"], env=env, capture_output=True, text=True, timeout=10)
                    output = result.stdout + result.stderr
                    match = re.search(r"I18N_RESULT (\{[^\n]+\})", output)
                    self.assertIsNotNone(match, output)
                    actual = json.loads(match.group(1))
                    expected = i18n.language(locale)
                    self.assertEqual(actual["language"], expected)
                    self.assertEqual(actual["label"], "Brilho" if expected == "pt" else "Brightness")
                    self.assertEqual(actual["missing"], "Close")
                    self.assertEqual(actual["parameter"], "Restaurar padrão: 128" if expected == "pt" else "Restore default: 128")


if __name__ == "__main__":
    unittest.main()
