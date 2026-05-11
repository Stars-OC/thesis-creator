# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.schemas import ImageItem, load_manifest  # noqa: E402
from charts.source_writer import PLACEHOLDER_MARKER, prepare_sources, validate_sources  # noqa: E402
from llm_chart_generator import HybridChartGenerator  # noqa: E402


class ChartModulesTestCase(unittest.TestCase):
    def test_hybrid_chart_generator_keeps_architecture_as_user_placeholder(self):
        output = HybridChartGenerator().generate("架构图", "展示系统分层", "", "图4-1", "系统架构图")

        self.assertIn("source=user", output)
        self.assertIn("用户自行生成", output)
        self.assertNotIn("```mermaid", output)
        self.assertNotIn("graph LR", output)

    def test_hybrid_chart_generator_does_not_force_er_mermaid(self):
        output = HybridChartGenerator().generate("E-R图", "展示用户表", "", "图4-2", "用户ER图")

        self.assertIn(".thesis-config.yaml", output)
        self.assertIn("Graphviz DOT", output)
        self.assertNotIn("```mermaid", output)
        self.assertNotIn("erDiagram", output)

    def test_hybrid_chart_generator_uses_plantuml_for_flowchart(self):
        output = HybridChartGenerator().generate("流程图", "展示注册流程", "", "图5-1", "注册流程图")

        self.assertIn("@startuml", output)
        self.assertIn("start", output)
        self.assertNotIn("```mermaid", output)
        self.assertNotIn("flowchart", output)

    def test_hybrid_chart_generator_uses_plantuml_for_uml_diagrams(self):
        for chart_type in ("用例图", "时序图"):
            with self.subTest(chart_type=chart_type):
                output = HybridChartGenerator().generate(chart_type, "展示核心交互", "", "图3-1", chart_type)

                self.assertIn("@startuml", output)
                self.assertNotIn("```mermaid", output)

    def test_source_writer_creates_expected_files_for_all_ai_engines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources_dir = root / "workspace" / "final" / "images" / "sources"
            items = [
                ImageItem.from_dict(
                    {
                        "id": "image_1",
                        "title": "图4-1 架构图",
                        "chapter": "第4章",
                        "section": "4.1",
                        "source": "ai",
                        "diagram_type": "architecture",
                        "purpose": "展示架构",
                        "fact_source": "background.md",
                        "placement": "架构说明之后",
                        "status": "pending",
                        "description": "系统架构",
                    }
                ),
                ImageItem.from_dict(
                    {
                        "id": "image_2",
                        "title": "图4-2 ER图",
                        "chapter": "第4章",
                        "section": "4.4",
                        "source": "ai",
                        "diagram_type": "er",
                        "purpose": "展示实体关系",
                        "fact_source": "background.md",
                        "placement": "数据库设计之后",
                        "status": "pending",
                        "description": "用户实体",
                    }
                ),
                ImageItem.from_dict(
                    {
                        "id": "image_3",
                        "title": "图3-1 用例图",
                        "chapter": "第3章",
                        "section": "3.2",
                        "source": "ai",
                        "diagram_type": "usecase",
                        "purpose": "展示用例",
                        "fact_source": "outline.md",
                        "placement": "需求分析之后",
                        "status": "pending",
                        "description": "用户用例",
                    }
                ),
            ]
            from charts.schemas import dump_manifest
            dump_manifest(manifest, items)

            prepare_sources(manifest, sources_dir)

            er_dot = (sources_dir / "image_2.dot").read_text(encoding="utf-8")
            self.assertFalse((sources_dir / "image_1.mmd").exists())
            self.assertIn("digraph", er_dot)
            self.assertNotIn(PLACEHOLDER_MARKER, er_dot)
            self.assertIn(PLACEHOLDER_MARKER, (sources_dir / "image_3.puml").read_text(encoding="utf-8"))
            engines = [item.engine for item in load_manifest(manifest)]
            self.assertEqual(["user", "graphviz", "plantuml"], engines)

    def test_validate_sources_rejects_placeholder_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources_dir = root / "workspace" / "final" / "images" / "sources"
            item = ImageItem.from_dict(
                {
                    "id": "image_1",
                    "title": "图5-1 流程图",
                    "chapter": "第5章",
                    "section": "5.1",
                    "source": "ai",
                    "diagram_type": "flowchart",
                    "purpose": "展示流程",
                    "fact_source": "background.md",
                    "placement": "流程说明之后",
                    "status": "pending",
                    "description": "业务流程",
                }
            )
            from charts.schemas import dump_manifest
            dump_manifest(manifest, [item])
            prepare_sources(manifest, sources_dir)

            with self.assertRaisesRegex(ValueError, "仍是占位源码"):
                validate_sources(manifest, root=root)

            (sources_dir / "image_1.puml").write_text("@startuml\nstart\n:处理;\nstop\n@enduml\n", encoding="utf-8")
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
