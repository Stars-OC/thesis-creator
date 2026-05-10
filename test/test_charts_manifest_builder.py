# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.manifest_builder import build_manifest, parse_image_placeholders, parse_requirement_blocks


class ChartsManifestBuilderTest(unittest.TestCase):
    def test_parse_image_placeholders_keeps_order_and_uniqueness(self):
        content = "[image_1]\n正文\n[image_2]\n再次 [image_1]"
        self.assertEqual(parse_image_placeholders(content), ["image_1", "image_2"])

    def test_parse_requirement_blocks_reads_yaml_comment(self):
        content = """
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统整体架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统整体分层与组件关系
fact_source: thesis-workspace/references/prompt/background.md
placement: 图前说明架构目标，图后分析分层职责
status: pending
prompt_hint: 使用分层架构表达，不要使用默认模板
-->
"""
        blocks = parse_requirement_blocks(content)
        self.assertEqual(blocks["image_1"]["title"], "图4-1 系统整体架构图")
        self.assertEqual(blocks["image_1"]["prompt_hint"], "使用分层架构表达，不要使用默认模板")

    def test_build_manifest_writes_safe_yaml_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "workspace" / "final" / "论文终稿.md"
            output_file = root / "workspace" / "references" / "images.yaml"
            input_file.parent.mkdir(parents=True)
            input_file.write_text(
                """
如图4-1所示，系统架构用于说明整体分层。
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统整体架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统整体分层与组件关系
fact_source: thesis-workspace/references/prompt/background.md
placement: 图前说明架构目标，图后分析分层职责
status: pending
description: 展示系统整体分层、组件关系与数据流向
prompt_hint: 使用分层架构表达，不要使用默认模板
-->
""".strip(),
                encoding="utf-8",
            )

            items = build_manifest(input_file, output_file)
            data = yaml.safe_load(output_file.read_text(encoding="utf-8"))

            self.assertEqual(len(items), 1)
            self.assertEqual(data["images"][0]["id"], "image_1")
            self.assertEqual(data["images"][0]["engine"], "mermaid")
            self.assertEqual(data["images"][0]["source_file"], "workspace/final/images/sources/image_1.mmd")

    def test_build_manifest_removes_requirement_blocks_after_writing_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "workspace" / "final" / "论文终稿.md"
            output_file = root / "workspace" / "references" / "images.yaml"
            input_file.parent.mkdir(parents=True)
            input_file.write_text(
                """
如图4-1所示，系统架构用于说明整体分层。
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统整体架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统整体分层与组件关系
fact_source: thesis-workspace/references/prompt/background.md
placement: 图前说明架构目标，图后分析分层职责
status: pending
description: 展示系统整体分层、组件关系与数据流向
-->
后续继续说明模块职责。
""".strip(),
                encoding="utf-8",
            )

            build_manifest(input_file, output_file)
            cleaned = input_file.read_text(encoding="utf-8")
            data = yaml.safe_load(output_file.read_text(encoding="utf-8"))

            self.assertEqual(data["images"][0]["id"], "image_1")
            self.assertIn("[image_1]", cleaned)
            self.assertIn("后续继续说明模块职责。", cleaned)
            self.assertNotIn("image-requirement", cleaned)
            self.assertNotIn("purpose: 展示系统整体分层与组件关系", cleaned)
            self.assertNotIn("description: 展示系统整体分层、组件关系与数据流向", cleaned)

    def test_build_manifest_marks_missing_requirement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "workspace" / "final" / "论文终稿.md"
            output_file = root / "workspace" / "references" / "images.yaml"
            input_file.parent.mkdir(parents=True)
            input_file.write_text("[image_9]", encoding="utf-8")

            items = build_manifest(input_file, output_file)

            self.assertEqual(items[0].id, "image_9")
            self.assertEqual(items[0].status, "missing_requirement")
            self.assertEqual(items[0].render_status, "blocked")


if __name__ == "__main__":
    unittest.main()
