# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from charts.schemas import ImageItem, load_manifest  # noqa: E402
from charts.source_writer import PLACEHOLDER_MARKER, prepare_sources, validate_sources  # noqa: E402


class ChartModulesTestCase(unittest.TestCase):
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

            self.assertIn(PLACEHOLDER_MARKER, (sources_dir / "image_1.mmd").read_text(encoding="utf-8"))
            self.assertIn(PLACEHOLDER_MARKER, (sources_dir / "image_2.dot").read_text(encoding="utf-8"))
            self.assertIn(PLACEHOLDER_MARKER, (sources_dir / "image_3.puml").read_text(encoding="utf-8"))
            engines = [item.engine for item in load_manifest(manifest)]
            self.assertEqual(["mermaid", "graphviz", "plantuml"], engines)

    def test_validate_sources_rejects_placeholder_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources_dir = root / "workspace" / "final" / "images" / "sources"
            item = ImageItem.from_dict(
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
            )
            from charts.schemas import dump_manifest
            dump_manifest(manifest, [item])
            prepare_sources(manifest, sources_dir)

            with self.assertRaisesRegex(ValueError, "仍是占位源码"):
                validate_sources(manifest, root=root)

            (sources_dir / "image_1.mmd").write_text("graph LR\nA-->B\n", encoding="utf-8")
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
