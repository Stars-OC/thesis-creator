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
        index_path = scripts_dir / "aigc" / "INDEX.md"

        self.assertTrue(index_path.exists())
        index_text = index_path.read_text(encoding="utf-8")
        for expected in ("detect.py", "technical_detect.py", "term_whitelist.txt"):
            self.assertIn(expected, index_text)

    def test_aigc_detect_returns_rewrite_self_check(self):
        from aigc.detect import detect_text

        text = (
            "首先，系统具有重要意义。其次，系统可以提升用户体验。最后，系统能够发挥重要作用。\n\n"
            "本文围绕该目标展开研究。系统具备一定的应用价值。综上所述，该系统具有良好前景。"
        )
        result = detect_text(text, output_format="json")

        self.assertIn("self_check", result)
        self.assertIn("sentence_rhythm", result["self_check"])
        self.assertIn("template_words", result["self_check"])
        self.assertIn("eight_part_style", result["self_check"])
        self.assertIn("rewrite_goal_checklist", result["self_check"])

    def test_self_check_flags_template_words_and_eight_part_style(self):
        from aigc.detect import AIGCDetector

        text = (
            "首先，系统具有重要意义。其次，系统可以提升用户体验。最后，系统能够发挥重要作用。\n\n"
            "本文围绕该目标展开研究。系统具备一定的应用价值。综上所述，该系统具有良好前景。"
        )
        result = AIGCDetector().detect(text)
        self_check = result["self_check"]

        self.assertGreater(self_check["template_words"]["total_count"], 0)
        self.assertTrue(self_check["eight_part_style"]["has_risk"])
        self.assertTrue(
            any(item["status"] == "未通过" for item in self_check["rewrite_goal_checklist"])
        )

    def test_extract_prose_removes_markdown_structural_content_before_inline_cleanup(self):
        from aigc.detect import _extract_prose_for_detection

        markdown = """# 第4章 系统设计

正文段落保留，用于检测自然语言表达。

[image_1]
[Image_2]
![系统架构图](https://example.com/arch.png)
图 4-1 系统架构图
<!-- image-requirement
id: image_1
-->

| 字段 | 含义 |
| --- | --- |
| user_id | 用户编号 |

## 7. 参考文献：
[1] 作者. 文献标题. 2025.
"""
        prose = _extract_prose_for_detection(markdown)

        self.assertIn("正文段落保留", prose)
        for unexpected in ("image_1", "Image_2", "系统架构图", "user_id", "参考文献", "文献标题"):
            self.assertNotIn(unexpected, prose)

    def test_transition_words_are_counted_once_when_word_list_contains_duplicates(self):
        from aigc import detect
        from aigc.detect import AIGCDetector

        try:
            detect.AI_TRANSITION_WORDS.append("由此可见")
            result = AIGCDetector()._template_word_details("由此可见，系统完成检测。")
        finally:
            detect.AI_TRANSITION_WORDS.pop()

        found = {item["word"]: item["count"] for item in result["found"]}
        self.assertEqual(1, found["由此可见"])
        self.assertEqual(1, result["total_count"])


if __name__ == "__main__":
    unittest.main()
