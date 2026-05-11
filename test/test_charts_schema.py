# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.schemas import ImageItem, infer_engine, load_manifest


class ChartsSchemaTest(unittest.TestCase):
    def test_infer_engine_defaults(self):
        self.assertEqual(infer_engine({"source": "user", "diagram_type": "screenshot"}), "user")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "er"}), "graphviz")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "overall_er"}), "graphviz")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "sequence"}), "plantuml")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "usecase"}), "plantuml")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "flowchart"}), "plantuml")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "workflow"}), "plantuml")
        self.assertEqual(infer_engine({"source": "ai", "diagram_type": "流程图"}), "plantuml")

    def test_load_manifest_rejects_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "images.yaml"
            manifest.write_text("images:\n  - id: image_1\n    source: ai\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "缺少必填字段"):
                load_manifest(manifest)

    def test_load_manifest_adds_default_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "images.yaml"
            manifest.write_text(
                """
images:
  - id: image_1
    title: 图4-1 系统整体架构图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: architecture
    purpose: 展示系统整体分层
    fact_source: thesis-workspace/references/prompt/background.md
    placement: 图前说明，图后分析
    status: pending
    description: 架构图需求
""".strip(),
                encoding="utf-8",
            )

            items = load_manifest(manifest)

            self.assertIsInstance(items[0], ImageItem)
            self.assertEqual(items[0].source, "user")
            self.assertEqual(items[0].engine, "user")
            self.assertEqual(items[0].source_file, "")
            self.assertEqual(items[0].output_file, "workspace/final/images/image_1.png")
            self.assertEqual(items[0].render_status, "pending_user")


if __name__ == "__main__":
    unittest.main()
