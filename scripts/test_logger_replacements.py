import json
import shutil
import tempfile
import unittest
from pathlib import Path

from logger import init_logger, ThesisLogger


class LoggerReplacementTest(unittest.TestCase):
    def setUp(self):
        ThesisLogger._instance = None
        ThesisLogger._initialized = False
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        logger = ThesisLogger._instance
        if logger is not None and hasattr(logger, "logger"):
            for handler in list(logger.logger.handlers):
                handler.close()
                logger.logger.removeHandler(handler)
        ThesisLogger._instance = None
        ThesisLogger._initialized = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_replacement_writes_jsonl_and_summary_log(self):
        workspace = self.tmp / "thesis-workspace"
        workspace.mkdir()

        logger = init_logger(workspace_path=str(workspace))
        logger.record_replacement(
            step=5,
            operation="synonym_replace",
            file="workspace/drafts/chapter_4.md",
            before="首先",
            after="先",
            reason="降低模板化表达",
        )

        replacement_log = workspace / "logs" / logger.session_name / "replacements.jsonl"
        self.assertTrue(replacement_log.exists())

        lines = replacement_log.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["operation"], "synonym_replace")
        self.assertEqual(payload["before"], "首先")
        self.assertEqual(payload["after"], "先")

        log_content = logger.get_log_content()
        self.assertIn("synonym_replace", log_content)
        self.assertIn("chapter_4.md", log_content)


if __name__ == "__main__":
    unittest.main()
