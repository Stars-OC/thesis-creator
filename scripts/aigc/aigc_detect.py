#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from aigc.detect import AIGCDetector, detect_directory, detect_file, detect_text, main

__all__ = ["AIGCDetector", "detect_directory", "detect_file", "detect_text", "main"]


if __name__ == "__main__":
    main()
