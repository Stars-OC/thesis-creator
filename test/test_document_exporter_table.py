import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
