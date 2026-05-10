# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.markdown_updater import update_markdown
from charts.validate import validate_pipeline


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
    description: 架构图
    engine: mermaid
    source_file: workspace/final/images/sources/image_1.mmd
    output_file: workspace/final/images/image_1.png
    render_status: rendered
  - id: image_2
    title: 图5-1 登录截图
    chapter: 第5章
    section: "5.1"
    source: user
    diagram_type: screenshot
    purpose: 展示登录界面
    fact_source: 用户截图
    placement: 图前说明，图后分析
    status: pending_user
    description: 用户补充截图
    engine: user
    source_file: ""
    output_file: workspace/final/images/image_2.png
    render_status: pending
"""


class ChartsMarkdownUpdateTest(unittest.TestCase):
    def test_update_markdown_replaces_rendered_ai_and_keeps_pending_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            image = root / "workspace" / "final" / "images" / "image_1.png"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            md.write_text("[image_1]\n[image_2]", encoding="utf-8")
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            image.write_bytes(b"x" * 2048)

            updated = update_markdown(md, manifest, in_place=True, root=root)

            self.assertIn("![图4-1 系统整体架构图](images/image_1.png)", updated)
            self.assertIn("[image_2]", updated)
            self.assertNotIn("[image_1]", updated)

    def test_update_markdown_removes_rendered_ai_image_requirement_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            image = root / "workspace" / "final" / "images" / "image_1.png"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            md.write_text(
                """
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统整体架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统整体分层
fact_source: background.md
placement: 图前说明，图后分析
status: pending
description: 架构图
-->

[image_2]
<!-- image-requirement
id: image_2
title: 图5-1 登录截图
source: user
description: 用户补充截图
-->
                """.strip(),
                encoding="utf-8",
            )
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            image.write_bytes(b"x" * 2048)

            updated = update_markdown(md, manifest, in_place=True, root=root)

            self.assertIn("![图4-1 系统整体架构图](images/image_1.png)", updated)
            self.assertIn("[image_2]", updated)
            self.assertIn("id: image_2", updated)
            self.assertNotIn("[image_1]", updated)
            self.assertNotIn("id: image_1", updated)
            self.assertNotIn("purpose: 展示系统整体分层", updated)
            self.assertNotIn("description: 架构图", updated)

    def test_update_markdown_rejects_missing_png(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            md.write_text("[image_1]", encoding="utf-8")
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "图片文件缺失"):
                update_markdown(md, manifest, root=root)

    def test_validate_pipeline_checks_rendered_files_and_placeholders(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            image = root / "workspace" / "final" / "images" / "image_1.png"
            source = root / "workspace" / "final" / "images" / "sources" / "image_1.mmd"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True)
            md.write_text("![图4-1 系统整体架构图](images/image_1.png)\n[image_2]", encoding="utf-8")
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            image.write_bytes(b"x" * 2048)
            source.write_text("flowchart LR\nA-->B", encoding="utf-8")

            report = validate_pipeline(md, manifest, root=root)

            self.assertEqual(report["errors"], [])
            self.assertEqual(report["user_required"], ["image_2"])


if __name__ == "__main__":
    unittest.main()
