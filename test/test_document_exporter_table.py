import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from document_exporter.docx_writer import calculate_image_size, convert_md_to_docx


class DocumentExporterTableTest(unittest.TestCase):
    def test_calculate_image_size_falls_back_for_missing_image(self):
        width, height = calculate_image_size("missing.png")
        self.assertEqual(width, 14.0)
        self.assertIsNone(height)

    def test_convert_md_to_docx_exports_minimal_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "paper.md"
            docx_path = temp_path / "paper.docx"
            markdown_path.write_text("# 标题\n\n正文", encoding="utf-8")

            success, message = convert_md_to_docx(str(markdown_path), str(docx_path))

            self.assertTrue(success, message)
            self.assertTrue(docx_path.exists())

    def test_convert_md_to_docx_uses_export_image_width_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "image_8.png"
            markdown_path = temp_path / "paper.md"
            docx_path = temp_path / "paper.docx"
            image_path.write_bytes(b"fake image")
            markdown_path.write_text("![图4-8 总体ER图](image_8.png)", encoding="utf-8")

            with patch("document_exporter.docx_writer.preflight_validate_images", return_value=(True, "ok")), \
                    patch("document_exporter.docx_writer.add_image", return_value=True) as add_image_mock:
                success, message = convert_md_to_docx(str(markdown_path), str(docx_path))

            self.assertTrue(success, message)
            _, kwargs = add_image_mock.call_args
            self.assertEqual(12.0, kwargs["width_cm"])
            self.assertEqual(14.0, kwargs["max_width_cm"])
            self.assertEqual(18.0, kwargs["max_height_cm"])


if __name__ == "__main__":
    unittest.main()
