# -*- coding: utf-8 -*-
from pathlib import Path
import os
import sys
import unittest
from unittest.mock import Mock, patch

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import document_exporter
import enhanced_md_to_docx
from charts.engines import mermaid, plantuml
from terminal_encoding import get_terminal_encoding, subprocess_text_kwargs


class TerminalEncodingTest(unittest.TestCase):
    def test_get_terminal_encoding_prefers_pythonioencoding(self):
        with patch.dict(os.environ, {"PYTHONIOENCODING": "gbk:replace"}):
            self.assertEqual("gbk", get_terminal_encoding())

    def test_subprocess_text_kwargs_uses_replace_errors(self):
        kwargs = subprocess_text_kwargs()

        self.assertTrue(kwargs["text"])
        self.assertTrue(kwargs["encoding"])
        self.assertEqual("replace", kwargs["errors"])

    def test_enhanced_pandoc_commands_use_terminal_encoding(self):
        completed = Mock(returncode=0, stderr="")
        with patch("enhanced_md_to_docx.subprocess.run", return_value=completed) as run:
            enhanced_md_to_docx.check_pandoc_installed()

        self.assertEqual("replace", run.call_args.kwargs["errors"])
        self.assertEqual(subprocess_text_kwargs()["encoding"], run.call_args.kwargs["encoding"])

        with patch("enhanced_md_to_docx.check_pandoc_installed", return_value=True), \
                patch("enhanced_md_to_docx.subprocess.run", return_value=completed) as run:
            enhanced_md_to_docx.convert_with_pandoc("input.md", "output.docx")

        self.assertEqual("replace", run.call_args.kwargs["errors"])
        self.assertEqual(subprocess_text_kwargs()["encoding"], run.call_args.kwargs["encoding"])

    def test_document_exporter_pdf_command_uses_terminal_encoding(self):
        completed = Mock(returncode=1, stderr="")
        with patch.dict(sys.modules, {"docx2pdf": None}), \
                patch("document_exporter.sys.platform", "linux"), \
                patch("document_exporter.subprocess.run", return_value=completed) as run:
            document_exporter.convert_docx_to_pdf("paper.docx", "paper.pdf")

        self.assertEqual("replace", run.call_args.kwargs["errors"])
        self.assertEqual(subprocess_text_kwargs()["encoding"], run.call_args.kwargs["encoding"])

    def test_mermaid_and_plantuml_commands_use_terminal_encoding(self):
        completed = Mock(returncode=1, stderr="failed")
        source = Path("source.mmd")
        output = Path("output.png")

        with patch("charts.engines.mermaid.subprocess.run", return_value=completed) as run:
            with self.assertRaises(RuntimeError):
                mermaid._render_with_mmdc(source, output)
        self.assertEqual("replace", run.call_args.kwargs["errors"])
        self.assertEqual(subprocess_text_kwargs()["encoding"], run.call_args.kwargs["encoding"])

        with patch("charts.engines.plantuml.subprocess.run", return_value=completed) as run:
            with self.assertRaises(RuntimeError):
                plantuml._render_local(source, output)
        self.assertEqual("replace", run.call_args.kwargs["errors"])
        self.assertEqual(subprocess_text_kwargs()["encoding"], run.call_args.kwargs["encoding"])


if __name__ == "__main__":
    unittest.main()
