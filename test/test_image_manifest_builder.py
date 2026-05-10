# -*- coding: utf-8 -*-

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from image_manifest_builder import build_image_manifest_from_markdown  # noqa: E402


class ImageManifestBuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.markdown_path = self.tmp / "workspace" / "drafts" / "chapter_4.md"
        self.markdown_path.parent.mkdir(parents=True)
        self.manifest_path = self.tmp / "workspace" / "references" / "images.yaml"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_manifest_extracts_standard_placeholders_with_context(self):
        self.markdown_path.write_text(
            """# 第4章 系统设计\n\n## 4.2 用户登录流程设计\n\n如图4-3所示，用户登录流程包含票据校验与状态写入。\n[image_1]\n图4-3 用户登录流程图\n绘图说明：展示扫码、读取票据、验证票据、写入登录态、跳转首页。\n""",
            encoding="utf-8",
        )

        result = build_image_manifest_from_markdown(self.markdown_path, self.manifest_path)

        self.assertEqual(["image_1"], [item["id"] for item in result])
        item = result[0]
        self.assertEqual("图4-3 用户登录流程图", item["title"])
        self.assertEqual("第4章", item["chapter"])
        self.assertEqual("4.2", item["section"])
        self.assertEqual("ai", item["source"])
        self.assertEqual("flowchart", item["diagram_type"])
        self.assertIn("扫码", item["description"])

        data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("image_1", data["images"][0]["id"])


    def test_build_manifest_extracts_block_style_placeholder_context(self):
        self.markdown_path.write_text(
            """# 第4章 系统设计\n\n## 4.1 系统架构设计\n\n如图4-1所示，系统采用分层架构。\n> **[image_4_1]：系统整体架构图**\n> - 图表编号：图4-1\n> - 图表名称：系统整体架构图\n> - 图表类型：架构图\n> - 内容描述：展示表示层、接口层、业务层、数据访问层与基础设施层之间的协同关系。\n""",
            encoding="utf-8",
        )

        result = build_image_manifest_from_markdown(self.markdown_path, self.manifest_path)

        self.assertEqual(["image_4_1"], [item["id"] for item in result])
        item = result[0]
        self.assertEqual("系统整体架构图", item["title"])
        self.assertEqual("architecture", item["diagram_type"])
        self.assertIn("表示层", item["description"])
        self.markdown_path.write_text(
            """# 第5章 系统实现\n\n## 5.2 登录功能实现\n\n登录页面效果如图5-1所示。\n[image_1]\n图5-1 登录功能界面截图\n图片说明：此处需要用户补充系统实际运行截图。\n截图要求：展示账号输入、验证码和登录按钮。\n后续继续说明核心代码。\n""",
            encoding="utf-8",
        )

        result = build_image_manifest_from_markdown(self.markdown_path, self.manifest_path, clean=True)

        item = result[0]
        self.assertEqual("user", item["source"])
        self.assertEqual("screenshot", item["diagram_type"])
        self.assertEqual("pending_user", item["status"])
        self.assertIn("登录功能界面截图", item["title"])

        cleaned = self.markdown_path.read_text(encoding="utf-8")
        self.assertIn("[image_1]", cleaned)
        self.assertNotIn("图片说明：", cleaned)
        self.assertNotIn("截图要求：", cleaned)
        self.assertIn("后续继续说明核心代码。", cleaned)


if __name__ == "__main__":
    unittest.main()
