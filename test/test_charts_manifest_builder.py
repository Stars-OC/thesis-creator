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
from charts.schemas import ImageItem, dump_manifest, load_manifest


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
            self.assertEqual(data["images"][0]["source"], "user")
            self.assertEqual(data["images"][0]["engine"], "user")
            self.assertNotIn("source_file", data["images"][0])
            self.assertEqual(data["images"][0]["render_status"], "pending_user")

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

    def test_build_manifest_puts_overall_er_before_other_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "workspace" / "final" / "论文终稿.md"
            output_file = root / "workspace" / "references" / "images.yaml"
            input_file.parent.mkdir(parents=True)
            input_file.write_text(
                """
第4章先说明架构图。
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统整体架构图
chapter: 第4章
section: "4.1"
source: user
diagram_type: architecture
purpose: 展示系统整体架构
fact_source: 用户自行生成
placement: 图前说明，图后分析
status: pending_user
description: 架构图由用户自行生成
-->
随后说明总体 ER 图。
[image_2]
<!-- image-requirement
id: image_2
title: 图4-2 总体ER图
chapter: 第4章
section: "4.4"
source: ai
diagram_type: overall_er
purpose: 展示系统总体实体关系
fact_source: thesis-workspace/references/prompt/background.md
placement: 数据库设计小节第一个展示
display_order: first
status: pending
description: 使用 DOT 实体-联系-实体结构展示总体 ER 图
-->
""".strip(),
                encoding="utf-8",
            )

            items = build_manifest(input_file, output_file)
            data = yaml.safe_load(output_file.read_text(encoding="utf-8"))

            self.assertEqual(items[0].id, "image_2")
            self.assertEqual(data["images"][0]["diagram_type"], "overall_er")
            self.assertEqual(data["images"][0]["engine"], "graphviz")
            self.assertEqual(data["images"][0]["source_file"], "workspace/final/images/sources/image_2.dot")

    def test_image_item_preserves_placeholder_id_when_dumping_and_loading(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_file = Path(tmpdir) / "images.yaml"
            item = ImageItem.from_dict(
                {
                    "id": "image_3_1",
                    "placeholder_id": "image_3",
                    "title": "图4-3 普通用户用例图",
                    "chapter": "第4章",
                    "section": "4.2",
                    "source": "ai",
                    "diagram_type": "usecase",
                    "purpose": "展示普通用户功能边界",
                    "fact_source": "thesis-workspace/references/prompt/background.md",
                    "placement": "图前说明，图后分析",
                    "status": "pending",
                    "description": "普通用户用例图",
                }
            )

            dump_manifest(manifest_file, [item])
            raw = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
            loaded = load_manifest(manifest_file)

            self.assertEqual(raw["images"][0]["placeholder_id"], "image_3")
            self.assertEqual(loaded[0].placeholder_id, "image_3")

    def test_build_manifest_expands_usecase_to_per_actor_items_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "workspace" / "final" / "论文终稿.md"
            output_file = root / "workspace" / "references" / "images.yaml"
            config_file = root / ".thesis-config.yaml"
            input_file.parent.mkdir(parents=True)
            config_file.write_text("usecase_modeling:\n  layout: per_actor\n", encoding="utf-8")
            input_file.write_text(
                """
如图4-3所示，系统用例图描述用户角色功能。
[image_3]
<!-- image-requirement
id: image_3
title: 图4-3 系统用例图
chapter: 第4章
section: "4.2"
source: ai
diagram_type: usecase
purpose: 展示系统用户角色与功能用例
fact_source: thesis-workspace/references/prompt/background.md
placement: 图前说明角色范围，图后分析核心用例
display_order: normal
status: pending
description: 展示普通用户、知识库管理员、系统管理员的系统用例
prompt_hint: 使用用例图表达三类角色与功能关系
-->
""".strip(),
                encoding="utf-8",
            )

            items = build_manifest(input_file, output_file)
            data = yaml.safe_load(output_file.read_text(encoding="utf-8"))

            self.assertEqual([item.id for item in items], ["image_3_1", "image_3_2", "image_3_3"])
            self.assertEqual([item.placeholder_id for item in items], ["image_3", "image_3", "image_3"])
            self.assertEqual([item.diagram_type for item in items], ["usecase", "usecase", "usecase"])
            titles = [item.title for item in items]
            self.assertIn("普通用户", titles[0])
            self.assertIn("知识库管理员", titles[1])
            self.assertIn("系统管理员", titles[2])
            self.assertEqual([image["placeholder_id"] for image in data["images"]], ["image_3", "image_3", "image_3"])
            self.assertEqual(data["images"][0]["source_file"], "workspace/final/images/sources/image_3_1.puml")


if __name__ == "__main__":
    unittest.main()
