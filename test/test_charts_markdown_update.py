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
    title: 图5-1 登录流程图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: flowchart
    purpose: 展示登录业务流程
    fact_source: chapter_5.md
    placement: 图前说明，图后分析
    status: pending
    description: 登录流程图
    engine: plantuml
    source_file: workspace/final/images/sources/image_1.puml
    output_file: workspace/final/images/image_1.png
    render_status: rendered
  - id: image_2
    title: 图5-2 登录截图
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


PER_ACTOR_MANIFEST_TEXT = """
images:
  - id: image_3_1
    placeholder_id: image_3
    title: 图4-3 系统用例图（普通用户）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示普通用户功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 普通用户用例图
    engine: plantuml
    source_file: workspace/final/images/sources/image_3_1.puml
    output_file: workspace/final/images/image_3_1.png
    render_status: rendered
  - id: image_3_2
    placeholder_id: image_3
    title: 图4-4 系统用例图（知识库管理员）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示知识库管理员功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 知识库管理员用例图
    engine: plantuml
    source_file: workspace/final/images/sources/image_3_2.puml
    output_file: workspace/final/images/image_3_2.png
    render_status: rendered
  - id: image_3_3
    placeholder_id: image_3
    title: 图4-5 系统用例图（系统管理员）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示系统管理员功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 系统管理员用例图
    engine: plantuml
    source_file: workspace/final/images/sources/image_3_3.puml
    output_file: workspace/final/images/image_3_3.png
    render_status: rendered
"""


class ChartsMarkdownUpdateTest(unittest.TestCase):
    def test_update_markdown_keeps_legacy_architecture_as_user_image(self):
        manifest_text = """
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
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            image = root / "workspace" / "final" / "images" / "image_1.png"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            md.write_text("[image_1]", encoding="utf-8")
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            image.write_bytes(b"x" * 2048)

            updated = update_markdown(md, manifest, in_place=True, root=root)

            self.assertIn("[image_1]", updated)
            self.assertNotIn("![图4-1 系统整体架构图](images/image_1.png)", updated)

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
title: 图5-1 登录流程图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: flowchart
purpose: 展示登录业务流程
fact_source: chapter_5.md
placement: 图前说明，图后分析
status: pending
description: 登录流程图
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

            self.assertIn("![图5-1 登录流程图](images/image_1.png)", updated)
            self.assertIn("[image_2]", updated)
            self.assertIn("id: image_2", updated)
            self.assertNotIn("[image_1]", updated)
            self.assertNotIn("id: image_1", updated)
            self.assertNotIn("purpose: 展示登录业务流程", updated)
            self.assertNotIn("description: 登录流程图", updated)

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
            source = root / "workspace" / "final" / "images" / "sources" / "image_1.puml"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True)
            md.write_text("![图5-1 登录流程图](images/image_1.png)\n[image_2]", encoding="utf-8")
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            image.write_bytes(b"x" * 2048)
            source.write_text("@startuml\nstart\n:登录;\nstop\n@enduml\n", encoding="utf-8")

            report = validate_pipeline(md, manifest, root=root)

            self.assertEqual(report["errors"], [])
            self.assertEqual(report["user_required"], ["image_2"])

    def test_update_markdown_replaces_one_usecase_placeholder_with_multiple_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            images_dir = root / "workspace" / "final" / "images"
            sources_dir = images_dir / "sources"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            images_dir.mkdir(parents=True)
            sources_dir.mkdir(parents=True)
            md.write_text("如图所示。\n[image_3]\n图后继续分析。", encoding="utf-8")
            manifest.write_text(PER_ACTOR_MANIFEST_TEXT.strip(), encoding="utf-8")
            for image_id in ["image_3_1", "image_3_2", "image_3_3"]:
                (images_dir / f"{image_id}.png").write_bytes(b"x" * 2048)
                (sources_dir / f"{image_id}.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")

            updated = update_markdown(md, manifest, in_place=True, root=root)

            self.assertNotIn("[image_3]", updated)
            self.assertEqual(updated.count("![图4-"), 3)
            self.assertLess(updated.index("image_3_1.png"), updated.index("image_3_2.png"))
            self.assertLess(updated.index("image_3_2.png"), updated.index("image_3_3.png"))
            self.assertIn("图后继续分析。", updated)

    def test_validate_pipeline_accepts_grouped_usecase_placeholder_after_replacement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            images_dir = root / "workspace" / "final" / "images"
            sources_dir = images_dir / "sources"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            images_dir.mkdir(parents=True)
            sources_dir.mkdir(parents=True)
            md.write_text(
                "![图4-3 系统用例图（普通用户）](images/image_3_1.png)\n\n"
                "![图4-4 系统用例图（知识库管理员）](images/image_3_2.png)\n\n"
                "![图4-5 系统用例图（系统管理员）](images/image_3_3.png)",
                encoding="utf-8",
            )
            manifest.write_text(PER_ACTOR_MANIFEST_TEXT.strip(), encoding="utf-8")
            for image_id in ["image_3_1", "image_3_2", "image_3_3"]:
                (images_dir / f"{image_id}.png").write_bytes(b"x" * 2048)
                (sources_dir / f"{image_id}.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")

            report = validate_pipeline(md, manifest, root=root)

            self.assertEqual(report["errors"], [])
            self.assertEqual(report["user_required"], [])

    def test_validate_pipeline_reports_grouped_usecase_placeholder_once_when_unreplaced(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            images_dir = root / "workspace" / "final" / "images"
            sources_dir = images_dir / "sources"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            images_dir.mkdir(parents=True)
            sources_dir.mkdir(parents=True)
            md.write_text("[image_3]", encoding="utf-8")
            manifest.write_text(PER_ACTOR_MANIFEST_TEXT.strip(), encoding="utf-8")
            for image_id in ["image_3_1", "image_3_2", "image_3_3"]:
                (images_dir / f"{image_id}.png").write_bytes(b"x" * 2048)
                (sources_dir / f"{image_id}.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")

            report = validate_pipeline(md, manifest, root=root)

            self.assertEqual(len(report["errors"]), 1)
            self.assertIn("image_3", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
