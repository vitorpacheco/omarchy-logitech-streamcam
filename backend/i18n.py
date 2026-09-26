"""Shared English/Portuguese catalog and Linux message-locale selection."""

import json
import os
from pathlib import Path
import re

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "translations.json").read_text(encoding="utf-8"))


def language(environment=None):
    environment = os.environ if environment is None else environment
    locale = next((environment.get(key) for key in ("LC_ALL", "LC_MESSAGES", "LANG") if environment.get(key)), "C")
    return "pt" if re.match(r"^pt(?:[-_.@]|$)", locale, re.IGNORECASE) else "en"


def tr(message, **values):
    text = CATALOG.get(language(), {}).get(message) or CATALOG.get("en", {}).get(message) or message
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
