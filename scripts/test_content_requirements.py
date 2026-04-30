# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from format_checker import FormatChecker  # noqa: E402


SKILL_ROOT = Path(__file__).resolve().parent.parent


class ThesisContentRequirementTestCase(unittest.TestCase):
    def test_thesis_structure_should_match_content_requirements(self):
        content = (SKILL_ROOT / "prompts" / "thesis_structure.md").read_text(encoding="utf-8")

        self.assertIn("国内外研究现状(合并写法", content)
        self.assertIn("550字左右", content)
        self.assertIn("每张表前后均需有文字说明", content)
        self.assertIn("用例图(LLM生成)", content)
        self.assertIn("6.1 测试目的", content)
        self.assertNotIn("4.5 接口设计", content)
        self.assertNotIn("6.1 测试环境", content)
        self.assertNotIn("6.4 测试结论", content)

    def test_writer_guidelines_should_match_content_requirements(self):
        content = (SKILL_ROOT / "prompts" / "writer_guidelines.md").read_text(encoding="utf-8")

        self.assertIn("550字左右", content)
        self.assertIn("用例图由 LLM 生成", content)
        self.assertIn("流程图不要固定为单一方向", content)
        self.assertIn("每张数据表都要配套文字说明", content)
        self.assertIn("测试目的", content)
        self.assertNotIn("测试环境", content)
        self.assertNotIn("测试结论", content)

    def test_image_generation_prompt_should_require_llm_usecase_and_sparse_flowcharts(self):
        content = (SKILL_ROOT / "prompts" / "image_generation.md").read_text(encoding="utf-8")

        self.assertIn("用例图由 LLM 生成", content)
        self.assertIn("不要固定为单一方向", content)
        self.assertIn("避免节点过于密集", content)
        self.assertIn("系统总体需求分析", content)
        self.assertIn("系统设计", content)

    def test_format_checker_should_accept_550_char_abstract(self):
        abstract_text = "研" * 550
        english_text = "abstract text"
        content = f"# 摘要\n{abstract_text}\n关键词：系统；设计；实现\n# Abstract\n{english_text}\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "paper.md"
            file_path.write_text(content, encoding="utf-8")

            checker = FormatChecker()
            checker.load_file(str(file_path))
            result = checker.check_abstract()

        self.assertTrue(result.passed)
        self.assertEqual("摘要检查", result.name)

    def test_format_checker_should_flag_oversized_abstract(self):
        abstract_text = "研" * 700
        english_text = "abstract text"
        content = f"# 摘要\n{abstract_text}\n关键词：系统；设计；实现\n# Abstract\n{english_text}\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "paper.md"
            file_path.write_text(content, encoding="utf-8")

            checker = FormatChecker()
            checker.load_file(str(file_path))
            result = checker.check_abstract()

        self.assertFalse(result.passed)
        self.assertTrue(any("中文摘要过长" in detail for detail in (result.details or [])))


if __name__ == "__main__":
    unittest.main()
