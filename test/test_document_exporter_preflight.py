import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from document_exporter.markdown import clean_markdown_content, parse_markdown
from document_exporter.preflight import preflight_validate_images


class DocumentExporterPreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_markdown_remains_available_for_docx_export(self):
        elements = parse_markdown("# 标题\n\n正文")
        self.assertEqual(elements[0], ("title", "标题"))
        self.assertEqual(elements[1], ("para", "正文"))

    def test_parse_markdown_extracts_block_style_markdown_image(self):
        elements = parse_markdown(
            "> **![系统整体架构图](images/系统整体架构图.png)：系统整体架构图**\n"
            "> - 图表编号：图4-1\n"
        )

        self.assertIn(("image", "images/系统整体架构图.png", "系统整体架构图"), elements)

        markdown_path = self.base_dir / "paper.md"
        markdown_path.write_text("正文中仍有 [image_1] 占位符", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertFalse(ok)
        self.assertIn("[image_1]", message)

    def test_allows_pending_user_screenshot_placeholders_declared_in_manifest(self):
        markdown_path = self.base_dir / "paper.md"
        references_dir = self.base_dir / "workspace" / "references"
        references_dir.mkdir(parents=True)
        (references_dir / "images.yaml").write_text(
            """
images:
  - id: image_1
    title: 图5-1 登录功能界面截图
    source: user
    diagram_type: screenshot
    status: pending_user
    description: 用户后续补充实际运行截图
""",
            encoding="utf-8",
        )
        markdown_path.write_text("第5章截图保留 [image_1] 待用户补图。", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertTrue(ok)
        self.assertIn("用户待补图片", message)

    def test_clean_markdown_content_removes_pending_image_placeholders(self):
        cleaned = clean_markdown_content("第5章截图 [image_5] 待补充。")

        self.assertNotIn("[image_5]", cleaned)
        self.assertIn("第5章截图", cleaned)

    def test_allows_pending_user_screenshot_placeholders_with_chapter_prefix(self):
        markdown_path = self.base_dir / "paper.md"
        references_dir = self.base_dir / "workspace" / "references"
        references_dir.mkdir(parents=True)
        (references_dir / "images.yaml").write_text(
            """
images:
  - id: image_5_1
    title: 图5-1 登录功能界面截图
    source: user
    diagram_type: screenshot
    status: pending_user
    description: 用户后续补充实际运行截图
""",
            encoding="utf-8",
        )
        markdown_path.write_text("第5章截图保留 [image_5_1] 待用户补图。", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertTrue(ok)
        self.assertIn("[image_5_1]", message)

    def test_rejects_export_when_markdown_image_is_missing(self):
        markdown_path = self.base_dir / "paper.md"
        markdown_path.write_text("![图4-1](images/图4-1.png)", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertFalse(ok)
        self.assertIn("images/图4-1.png", message)

    def test_passes_preflight_when_all_images_exist(self):
        markdown_path = self.base_dir / "paper.md"
        image_dir = self.base_dir / "images"
        image_dir.mkdir()
        (image_dir / "图4-1.png").write_bytes(b"a" * 2048)
        markdown_path.write_text("![图4-1](images/图4-1.png)", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertTrue(ok)
        self.assertIn("通过", message)


if __name__ == "__main__":
    unittest.main()
