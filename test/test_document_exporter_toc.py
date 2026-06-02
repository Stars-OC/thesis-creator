import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from document_exporter.docx_writer import convert_md_to_docx


def read_document_xml(docx_path: Path) -> str:
    with ZipFile(docx_path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


class DocumentExporterTocTest(unittest.TestCase):
    def test_inserts_word_toc_after_abstract_before_first_chapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "paper.md"
            output_path = temp_path / "paper.docx"
            markdown_path.write_text(
                "# 摘要\n\n"
                "这里是中文摘要。\n\n"
                "# Abstract\n\n"
                "This is the English abstract.\n\n"
                "# 第一章 绪论\n\n"
                "## 1.1 研究背景\n\n"
                "这里是研究背景。\n",
                encoding="utf-8",
            )

            success, message = convert_md_to_docx(str(markdown_path), str(output_path))

            self.assertTrue(success, message)
            document_xml = read_document_xml(output_path)
            self.assertIn('TOC \\o "1-4" \\h \\z \\u', document_xml)
            self.assertLess(document_xml.index("Abstract"), document_xml.index("TOC"))
            self.assertLess(document_xml.index("TOC"), document_xml.index("第一章 绪论"))

    def test_inserts_word_toc_after_chinese_abstract_when_no_english_abstract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "paper.md"
            output_path = temp_path / "paper.docx"
            markdown_path.write_text(
                "# 摘要\n\n"
                "这里是中文摘要。\n\n"
                "# 第一章 绪论\n\n"
                "正文开始。\n",
                encoding="utf-8",
            )

            success, message = convert_md_to_docx(str(markdown_path), str(output_path))

            self.assertTrue(success, message)
            document_xml = read_document_xml(output_path)
            self.assertLess(document_xml.index("摘要"), document_xml.index("TOC"))
            self.assertLess(document_xml.index("TOC"), document_xml.index("第一章 绪论"))


if __name__ == "__main__":
    unittest.main()
