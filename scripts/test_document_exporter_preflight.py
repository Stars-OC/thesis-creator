import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from document_exporter import parse_markdown, preflight_validate_images


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

    def test_rejects_export_when_image_placeholder_remains(self):
        markdown_path = self.base_dir / "paper.md"
        markdown_path.write_text("正文中仍有 [image_1] 占位符", encoding="utf-8")

        ok, message = preflight_validate_images(markdown_path)

        self.assertFalse(ok)
        self.assertIn("[image_1]", message)

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
