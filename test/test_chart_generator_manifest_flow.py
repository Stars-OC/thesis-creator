# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.manifest_builder import build_manifest, parse_image_placeholders, parse_requirement_blocks  # noqa: E402


class ChartGeneratorManifestFlowTest(unittest.TestCase):
    def test_parse_image_placeholders_extracts_image_ids_in_order(self):
        markdown = "第一张图见 [image_1]。第二张图见 [image_2]。再次引用 [image_1]。"

        self.assertEqual(["image_1", "image_2"], parse_image_placeholders(markdown))

    def test_parse_requirement_blocks_reads_yaml_records(self):
        markdown = """[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统整体架构
fact_source: background.md
placement: 架构说明之后
status: pending
description: 展示前端、后端和数据库关系
-->
"""

        requirements = parse_requirement_blocks(markdown)

        self.assertEqual("图4-1 系统架构图", requirements["image_1"]["title"])
        self.assertEqual("architecture", requirements["image_1"]["diagram_type"])

    def test_build_manifest_marks_missing_requirement_as_blocked_ai_item(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "paper.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            paper.write_text("正文存在未说明图片 [image_5_1]。", encoding="utf-8")

            items = build_manifest(paper, manifest)

            self.assertEqual(1, len(items))
            self.assertEqual("image_5_1", items[0].id)
            self.assertEqual("mermaid", items[0].engine)
            self.assertEqual("missing_requirement", items[0].status)
            self.assertEqual("blocked", items[0].render_status)
            self.assertTrue(manifest.exists())


if __name__ == "__main__":
    unittest.main()
