# -*- coding: utf-8 -*-

from aigc.detect import AIGCDetector, detect_directory, detect_file, detect_text
from aigc.technical_detect import TechnicalPaperAIGCDetector

__all__ = [
    "AIGCDetector",
    "TechnicalPaperAIGCDetector",
    "detect_directory",
    "detect_file",
    "detect_text",
]
