# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from chart_generator import ChartGenerator, ChartPlaceholder  # noqa: E402
from llm_chart_generator import LLMChartGenerator, HybridChartGenerator  # noqa: E402


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class ChartLayoutConfigTestCase(unittest.TestCase):
    def test_flowchart_should_vary_direction_by_default(self):
        generator = ChartGenerator(output_dir=str(Path(__file__).parent / "test_output"))
        generator.logger = DummyLogger()

        placeholder_a = ChartPlaceholder(
            raw_text="",
            chart_type="流程图",
            chart_id="图5-1",
            chart_name="登录流程图",
            description="""
内容描述：
1）用户输入账号密码；
2）系统校验账号密码；
3）判断是否通过；
4）返回结果。
""",
        )
        placeholder_b = ChartPlaceholder(
            raw_text="",
            chart_type="流程图",
            chart_id="图5-2",
            chart_name="订单处理流程图",
            description="""
内容描述：
1）用户提交订单；
2）系统校验库存；
3）生成订单记录；
4）返回处理结果。
""",
        )

        mermaid_a = generator.generate_mermaid(placeholder_a)
        mermaid_b = generator.generate_mermaid(placeholder_b)

        direction_a = next(line.split()[1] for line in mermaid_a.splitlines() if line.startswith("flowchart "))
        direction_b = next(line.split()[1] for line in mermaid_b.splitlines() if line.startswith("flowchart "))

        self.assertIn(direction_a, {"LR", "RL", "TB", "BT"})
        self.assertIn(direction_b, {"LR", "RL", "TB", "BT"})
        self.assertNotEqual(direction_a, direction_b)

    def test_architecture_prompt_should_use_left_to_right_layout(self):
        prompt = LLMChartGenerator.CHART_PROMPTS["架构图"]
        self.assertIn("graph LR", prompt)
        self.assertNotIn("graph TB", prompt)

    def test_flowchart_prompt_should_require_varied_directions_and_sparse_layout(self):
        prompt = LLMChartGenerator.CHART_PROMPTS["流程图"]
        self.assertIn("不要固定为单一方向", prompt)
        self.assertIn("避免节点过于密集", prompt)
        self.assertIn("LR", prompt)
        self.assertIn("TB", prompt)

    def test_hybrid_default_architecture_should_use_left_to_right_layout(self):
        hybrid = HybridChartGenerator()
        mermaid = hybrid._generate_default("架构图", "图2-1", "系统架构图", "Web系统")

        self.assertIn("graph LR", mermaid)
        self.assertNotIn("graph TB", mermaid)

    def test_hybrid_default_flowchart_should_support_non_lr_direction(self):
        hybrid = HybridChartGenerator()
        mermaid = hybrid._generate_default("流程图", "图2-2", "登录流程图", "登录业务")

        self.assertIn("flowchart TB", mermaid)
        self.assertNotIn("flowchart LR", mermaid)

    def test_usecase_diagram_should_delegate_to_hybrid_generator_first(self):
        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="用例图",
            chart_id="图3-1",
            chart_name="用户管理用例图",
            description="普通用户可以登录、查询数据，管理员可以审核与导出报告。",
        )

        generator = ChartGenerator(output_dir=str(Path(__file__).parent / "test_output"))
        generator.logger = DummyLogger()

        with patch("chart_generator.HybridChartGenerator") as hybrid_cls:
            hybrid_instance = hybrid_cls.return_value
            hybrid_instance.generate.return_value = "```mermaid\ngraph TB\nUser((用户)) --> UC1((登录))\n```"

            mermaid = generator.generate_mermaid(placeholder)

        hybrid_cls.assert_called_once()
        hybrid_instance.generate.assert_called_once()
        self.assertIn("graph TB", mermaid)

    def test_architecture_diagram_should_delegate_to_hybrid_generator_first(self):
        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="架构图",
            chart_id="图5-2",
            chart_name="系统架构图",
            description="前后端分离架构",
        )

        generator = ChartGenerator(output_dir=str(Path(__file__).parent / "test_output"))
        generator.logger = DummyLogger()

        with patch("chart_generator.HybridChartGenerator") as hybrid_cls:
            hybrid_instance = hybrid_cls.return_value
            hybrid_instance.generate.return_value = "```mermaid\ngraph LR\nA-->B\n```"

            mermaid = generator.generate_mermaid(placeholder)

        hybrid_cls.assert_called_once()
        hybrid_instance.generate.assert_called_once()
        self.assertIn("graph LR", mermaid)

