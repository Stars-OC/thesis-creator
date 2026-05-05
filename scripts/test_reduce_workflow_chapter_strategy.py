# -*- coding: utf-8 -*-

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from reduce_workflow import (  # noqa: E402
    PaperReducer,
    detect_chapter_type,
    get_chapter_strategy,
    run_workflow,
)


class ReduceWorkflowChapterStrategyTestCase(unittest.TestCase):
    def test_detect_chapter_type_for_abstract(self):
        chapter_type = detect_chapter_type("摘要.md", "# 摘要\n\n本文围绕系统设计展开。")
        self.assertEqual("abstract", chapter_type)

    def test_detect_chapter_type_for_acknowledgement(self):
        chapter_type = detect_chapter_type("致谢.md", "感谢导师和同学的帮助。")
        self.assertEqual("acknowledgement", chapter_type)

    def test_detect_chapter_type_for_system_design(self):
        chapter_type = detect_chapter_type("chapter_4.md", "# 第4章 系统设计\n\n系统采用分层架构。")
        self.assertEqual("system_design", chapter_type)

    def test_detect_chapter_type_for_system_implementation(self):
        chapter_type = detect_chapter_type("chapter_5.md", "# 第5章 系统实现\n\n接口调用流程如下。")
        self.assertEqual("system_implementation", chapter_type)

    def test_detect_chapter_type_for_testing_analysis(self):
        chapter_type = detect_chapter_type("chapter_6.md", "# 第6章 系统测试\n\n测试环境如下。")
        self.assertEqual("testing_analysis", chapter_type)

    def test_detect_chapter_type_for_conclusion_outlook(self):
        chapter_type = detect_chapter_type("chapter_7.md", "# 第7章 总结与展望\n\n本文完成了系统设计与实现。")
        self.assertEqual("conclusion_outlook", chapter_type)

    def test_detect_chapter_type_prefers_heading_over_filename_fallback(self):
        chapter_type = detect_chapter_type("chapter_4.md", "# 第7章 总结与展望\n\n后续工作如下。")
        self.assertEqual("conclusion_outlook", chapter_type)

    def test_detect_chapter_type_returns_generic_without_hints(self):
        chapter_type = detect_chapter_type("notes.md", "这里是普通说明文字，没有章节提示词。")
        self.assertEqual("generic", chapter_type)

    def test_get_chapter_strategy_returns_generic_fallback(self):
        strategy = get_chapter_strategy("unknown_type")
        self.assertEqual("通用章节", strategy["label"])

    def test_replace_text_does_not_chain_replace_design_into_implementation_term(self):
        reducer = PaperReducer(whitelist=set(), ratio=1.0)

        with patch("reduce_workflow.random.sample", side_effect=lambda population, k: population[:k]), patch(
            "reduce_workflow.random.choice",
            side_effect=["开发", "开发实现"],
        ):
            replaced_text, replacements = reducer.replace_text("设计")

        self.assertEqual("开发", replaced_text)
        self.assertEqual([("设计", "开发")], replacements)

    def test_run_workflow_writes_chapter_aware_prompt_report_and_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_file = tmpdir_path / "chapter_4.md"
            output_dir = tmpdir_path / "reduced"
            input_file.write_text(
                "# 第4章 系统设计\n\n系统设计部分重点说明模块划分、数据库表结构与接口关系。",
                encoding="utf-8",
            )

            result = run_workflow(str(input_file), str(output_dir), ratio=0.2)

            self.assertEqual("system_design", result["chapter_type"])
            self.assertEqual("系统设计", result["chapter_label"])

            prompt_text = Path(result["prompt_path"]).read_text(encoding="utf-8")
            report_text = Path(result["report_path"]).read_text(encoding="utf-8")
            record_data = json.loads(Path(result["record_path"]).read_text(encoding="utf-8"))

            self.assertIn("识别章节类型：system_design", prompt_text)
            self.assertIn("本章优先策略", prompt_text)
            self.assertIn("本章禁用策略", prompt_text)
            self.assertIn("优先局部修正，不要整章重写", prompt_text)
            self.assertIn("章节类型 | system_design |", report_text)
            self.assertIn("章节标签 | 系统设计 |", report_text)
            self.assertIn("优先策略", report_text)
            self.assertIn("禁用策略", report_text)
            self.assertEqual("system_design", record_data["chapter_type"])
            self.assertEqual("系统设计", record_data["chapter_label"])
            self.assertEqual(get_chapter_strategy("system_design")["goal"], record_data["chapter_goal"])


if __name__ == "__main__":
    unittest.main()
