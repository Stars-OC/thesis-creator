# -*- coding: utf-8 -*-

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from aigc.reduce_workflow import (  # noqa: E402
    PaperReducer,
    build_aigc_comparison_report,
    build_clause_preservation_summary,
    detect_chapter_type,
    extract_clause_markers,
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

    def test_review_prompt_uses_thesis_style_quality_guidelines(self):
        reducer = PaperReducer(whitelist={"系统"}, ratio=0.5)

        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_path = Path(tmpdir) / "review_prompt.md"
            prompt_text = reducer.generate_review_prompt(
                "# 第4章 系统设计\n\n系统采用分层架构。",
                "# 第4章 系统设计\n\n系统采用分层架构。",
                str(prompt_path),
                "system_design",
                get_chapter_strategy("system_design"),
            )

        self.assertIn("软件工程方向毕业论文风格", prompt_text)
        self.assertIn("在保证语义不变的前提下进行重写，而不是简单同义替换", prompt_text)
        self.assertIn("避免大量使用“系统应……从而……”这类标准答案式句式", prompt_text)
        self.assertIn("控制句式多样性", prompt_text)
        self.assertIn("适当保留自然表达", prompt_text)
        self.assertIn("允许使用自然承接语和少量轻冗余词", prompt_text)
        self.assertIn("信息密度过高的句子应先拆出主干", prompt_text)
        self.assertIn("删除口语化、评价性或宣传性表达", prompt_text)
        self.assertIn("不引入额外技术术语或扩展内容", prompt_text)
        self.assertIn("以学术表达质量和语义准确性为目标", prompt_text)
        self.assertIn("AIGC 降低处理计划", prompt_text)
        self.assertIn("场景化重写、结构重组、细节注入、自然承接与轻冗余、高密度句拆句解释、语言去模板化", prompt_text)
        self.assertIn("显性转接词", prompt_text)
        self.assertIn("原句骨架", prompt_text)
        self.assertIn("场景或系统细节充足", prompt_text)
        self.assertIn("处理完成自检", prompt_text)
        self.assertIn("条款编号与顺序保留", prompt_text)
        self.assertIn("未新增虚构信息", prompt_text)
        self.assertIn("100% 疑似条款", prompt_text)
        self.assertNotIn("降低 AIGC 检测率", prompt_text)
        self.assertNotIn("通过常规论文查重与AI检测", prompt_text)

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
            self.assertTrue(Path(result["comparison_report_path"]).exists())
            comparison = Path(result["comparison_report_path"]).read_text(encoding="utf-8")
            self.assertIn("AIGC 降低前后量化对比报告", comparison)
            self.assertIn("条款保留检查", comparison)

    def test_clause_marker_extraction_preserves_numbered_items(self):
        text = "（1）用户与角色管理功能：内容。\n（2）权限管理功能：内容。\n（4）系统监控功能：内容。"

        self.assertEqual(["（1）", "（2）", "（4）"], extract_clause_markers(text))

    def test_clause_preservation_summary_reports_missing_markers(self):
        before = "（1）用户与角色管理功能：内容。\n（2）权限管理功能：内容。"
        after = "（1）用户与角色管理功能：内容。"

        summary = build_clause_preservation_summary(before, after)

        self.assertEqual(2, summary["total_before"])
        self.assertEqual(1, summary["total_after"])
        self.assertEqual(["（2）"], summary["missing"])
        self.assertEqual("未通过", summary["status"])

    def test_aigc_comparison_report_contains_metrics_and_self_check(self):
        before_result = {
            "overall_score": 82.4,
            "burstiness": {"score": 70.0, "detail": "句长波动不足"},
            "vocabulary": {"score": 40.0, "detail": "TTR 偏低"},
            "transition": {"score": 55.0, "detail": "过渡词偏高"},
            "structure": {"score": 60.0, "detail": "结构偏工整"},
            "high_risk_paragraphs": [2, 4],
            "rewrite_self_check": {
                "template_words": {"status": "fail", "detail": "仍存在模板词残留"}
            },
        }
        after_result = {
            "overall_score": 46.7,
            "burstiness": {"score": 42.5, "detail": "句长有波动"},
            "vocabulary": {"score": 35.0, "detail": "TTR 改善"},
            "transition": {"score": 20.0, "detail": "过渡词较少"},
            "structure": {"score": 25.0, "detail": "结构风险下降"},
            "high_risk_paragraphs": [4],
            "rewrite_self_check": {
                "template_words": {"status": "pass", "detail": "模板词残留减少"}
            },
        }
        clause_summary = {
            "status": "通过",
            "total_before": 2,
            "total_after": 2,
            "missing": [],
            "kept": ["（1）", "（2）"],
        }

        report = build_aigc_comparison_report(
            before_result,
            after_result,
            clause_summary,
            input_path="before.md",
            output_path="after.md",
        )

        self.assertIn("# AIGC 降低前后量化对比报告", report)
        self.assertIn("| 整体 AIGC 检测率 | 82.4 | 46.7 | -35.7 |", report)
        self.assertIn("（1）、（2）", report)
        self.assertIn("模板词残留减少", report)
        self.assertIn("语义与术语未改变", report)
        self.assertIn("自然承接语使用", report)
        self.assertIn("轻冗余控制", report)
        self.assertIn("高密度句已拆解", report)
        self.assertIn("原句骨架已重组", report)
        self.assertIn("场景或系统细节充足", report)
        self.assertIn("未新增虚构信息", report)
    def test_aigc_comparison_report_tolerates_missing_fields(self):
        report = build_aigc_comparison_report(
            {},
            {},
            {},
            input_path="before.md",
            output_path="after.md",
        )

        self.assertIn("# AIGC 降低前后量化对比报告", report)
        self.assertIn("检查状态：需人工确认", report)
        self.assertIn("缺失条款：无", report)


if __name__ == "__main__":
    unittest.main()
