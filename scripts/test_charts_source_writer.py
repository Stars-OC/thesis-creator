# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.schemas import load_manifest
from charts.source_writer import prepare_sources, validate_sources


MANIFEST_TEXT = """
images:
  - id: image_1
    title: 图4-1 系统整体架构图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: architecture
    purpose: 展示系统整体分层
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 架构图需求
  - id: image_2
    title: 图4-2 用户表ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    purpose: 展示用户表字段
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: ER图需求
  - id: image_3
    title: 图5-1 登录时序图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: sequence
    purpose: 展示登录调用顺序
    fact_source: chapter_5.md
    placement: 图前说明，图后分析
    status: pending
    description: 时序图需求
  - id: image_4
    title: 图5-2 登录截图
    chapter: 第5章
    section: "5.1"
    source: user
    diagram_type: screenshot
    purpose: 展示系统界面
    fact_source: 用户运行截图
    placement: 图前说明，图后分析
    status: pending_user
    description: 用户补充截图
"""


class ChartsSourceWriterTest(unittest.TestCase):
    def test_prepare_sources_creates_engine_specific_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")

            items = prepare_sources(manifest, sources)

            self.assertTrue((sources / "image_1.mmd").exists())
            self.assertTrue((sources / "image_2.dot").exists())
            self.assertTrue((sources / "image_3.puml").exists())
            self.assertFalse((sources / "image_4").exists())
            self.assertIn("source_file: workspace/final/images/sources/image_1.mmd", manifest.read_text(encoding="utf-8"))
            self.assertEqual(load_manifest(manifest)[0].source_file, "workspace/final/images/sources/image_1.mmd")
            self.assertEqual(items[3].engine, "user")

    def test_validate_sources_rejects_placeholder_only_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            prepare_sources(manifest, sources)

            with self.assertRaisesRegex(ValueError, "仍是占位源码"):
                validate_sources(manifest, root)

    def test_validate_sources_accepts_filled_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            prepare_sources(manifest, sources)
            (sources / "image_1.mmd").write_text("flowchart LR\nA-->B\n", encoding="utf-8")
            (sources / "image_2.dot").write_text("digraph G { A -> B }\n", encoding="utf-8")
            (sources / "image_3.puml").write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")

            validate_sources(manifest, root)


if __name__ == "__main__":
    unittest.main()
