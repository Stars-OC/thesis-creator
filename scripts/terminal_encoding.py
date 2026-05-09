# -*- coding: utf-8 -*-
from __future__ import annotations

import locale
import os
import sys


def get_terminal_encoding() -> str:
    pythonioencoding = os.environ.get("PYTHONIOENCODING", "").strip()
    if pythonioencoding:
        return pythonioencoding.split(":", 1)[0] or "utf-8"

    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding:
            return encoding

    return locale.getpreferredencoding(False) or "utf-8"


def subprocess_text_kwargs() -> dict:
    return {"text": True, "encoding": get_terminal_encoding(), "errors": "replace"}
