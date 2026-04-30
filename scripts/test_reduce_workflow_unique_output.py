# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from reduce_workflow import run_workflow  # noqa: E402


class ReduceWorkflowUniqueOutputTestCase(unittest.TestCase):
    def test_run_workflow_generates_unique_files_for_back_to_back_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_file = tmpdir_path / "chapter_4.md"
            output_dir = tmpdir_path / "reduced"
            input_file.write_text("这是一个用于降重测试的短文本。系统支持知识库检索与问答功能。", encoding="utf-8")

            first = run_workflow(str(input_file), str(output_dir), ratio=0.2)
            second = run_workflow(str(input_file), str(output_dir), ratio=0.2)

            self.assertNotEqual(first["output_paper"], second["output_paper"])
            self.assertNotEqual(first["prompt_path"], second["prompt_path"])
            self.assertNotEqual(first["record_path"], second["record_path"])
            self.assertNotEqual(first["report_path"], second["report_path"])

            for result in (first, second):
                self.assertTrue(Path(result["output_paper"]).exists())
                self.assertTrue(Path(result["prompt_path"]).exists())
                self.assertTrue(Path(result["record_path"]).exists())
                self.assertTrue(Path(result["report_path"]).exists())


if __name__ == "__main__":
    unittest.main()
