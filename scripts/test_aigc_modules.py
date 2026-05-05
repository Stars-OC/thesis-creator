# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


class AIGCModulesTestCase(unittest.TestCase):
    def test_aigc_package_exports_general_detector(self):
        from aigc import AIGCDetector, detect_text
        from aigc.detect import AIGCDetector as DirectDetector

        self.assertIs(AIGCDetector, DirectDetector)
        result = detect_text("首先，系统具有重要意义。此外，本文旨在分析相关问题。", output_format="json")

        self.assertIn("overall_score", result)
        self.assertIn("high_risk_paragraphs", result)

    def test_aigc_package_exports_technical_detector(self):
        from aigc import TechnicalPaperAIGCDetector
        from aigc.technical_detect import TechnicalPaperAIGCDetector as DirectDetector

        self.assertIs(TechnicalPaperAIGCDetector, DirectDetector)
        detector = TechnicalPaperAIGCDetector()
        result = detector.detect("首先，系统具有重要意义。此外，本文旨在分析相关问题。")

        self.assertEqual("technical", result["mode"])
        self.assertIn("overall_score", result)

    def test_legacy_wrappers_still_export_core_classes(self):
        import aigc_detect
        import aigc_detect_technical
        from aigc.detect import AIGCDetector
        from aigc.technical_detect import TechnicalPaperAIGCDetector

        self.assertIs(aigc_detect.AIGCDetector, AIGCDetector)
        self.assertIs(aigc_detect_technical.TechnicalPaperAIGCDetector, TechnicalPaperAIGCDetector)

    def test_aigc_index_lists_modules_and_resources(self):
        index_path = scripts_dir / "aigc" / "_index.yaml"

        self.assertTrue(index_path.exists())
        index_text = index_path.read_text(encoding="utf-8")
        for expected in ("detect.py", "technical_detect.py", "term_whitelist.txt"):
            self.assertIn(expected, index_text)


if __name__ == "__main__":
    unittest.main()
