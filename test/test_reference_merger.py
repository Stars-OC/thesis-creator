# -*- coding: utf-8 -*-

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from references.reference_merger import assess_reference_quality, save_yaml, select_top  # noqa: E402


class ReferenceMergerTestCase(unittest.TestCase):
    def _make_ref(self, title: str, language: str, relevance: float, citations: int = 0, year: int = 2025):
        return {
            "title": title,
            "language": language,
            "relevance_score": relevance,
            "citation_count": citations,
            "year": year,
            "cross_verified": True,
            "verified": True,
            "doi": f"10.1000/{title}",
        }

    def test_select_top_keeps_limit_when_supplementing_missing_language(self):
        refs = [
            self._make_ref("English A", "en", 0.99, 900),
            self._make_ref("English B", "en", 0.98, 800),
            self._make_ref("English C", "en", 0.97, 700),
            self._make_ref("中文文献D", "zh", 0.96, 600),
            self._make_ref("中文文献E", "zh", 0.95, 500),
        ]

        selected = select_top(refs, 3)

        self.assertEqual(3, len(selected))
        self.assertGreaterEqual(sum(1 for ref in selected if ref.get("language") == "zh"), 1)
        self.assertLessEqual(len(selected), 3)

    def test_select_top_uses_plain_truncation_when_languages_already_balanced(self):
        refs = [
            self._make_ref("English A", "en", 0.99, 900),
            self._make_ref("中文文献B", "zh", 0.98, 800),
            self._make_ref("English C", "en", 0.97, 700),
            self._make_ref("中文文献D", "zh", 0.96, 600),
        ]

        selected = select_top(refs, 3)

        self.assertEqual(["English A", "中文文献B", "English C"], [ref["title"] for ref in selected])
        self.assertEqual(3, len(selected))

    def test_save_yaml_persists_selection_metadata(self):
        refs = [
            self._make_ref("English A", "en", 0.99, 900),
            self._make_ref("中文文献B", "zh", 0.98, 800),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "verified_references.yaml"
            save_yaml(
                refs,
                output_path,
                pool_id="test_pool",
                selection_limit=25,
                language_balance={"zh": 1, "en": 1},
            )
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("selection_limit: 25", content)
        self.assertIn("language_balance:", content)
        self.assertIn("zh: 1", content)
        self.assertIn("en: 1", content)

    def test_save_yaml_escapes_titles_with_colons_and_brackets(self):
        refs = [
            self._make_ref("RAG: Retrieval-Augmented Generation (Survey): 2024", "en", 0.99, 100),
            self._make_ref("中文文献：系统设计（实践）", "zh", 0.98, 90),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "verified_references.yaml"
            save_yaml(refs, output_path)
            parsed = yaml.safe_load(output_path.read_text(encoding="utf-8"))

        self.assertEqual("RAG: Retrieval-Augmented Generation (Survey): 2024", parsed["references"][0]["title"])
        self.assertEqual("中文文献：系统设计（实践）", parsed["references"][1]["title"])

    def test_assess_reference_quality_warns_when_zh_ratio_is_not_strictly_above_threshold(self):
        refs = [
            self._make_ref("中文文献A", "zh", 0.99),
            self._make_ref("English B", "en", 0.98),
            self._make_ref("English C", "en", 0.97),
        ]

        report = assess_reference_quality(refs)

        self.assertFalse(report["ok"])
        self.assertLessEqual(report["zh_ratio"], 0.65)
        self.assertIn("中文文献占比", report["warnings"][0])
        self.assertIn("CNKI", report["suggestions"][0])

    def test_select_top_emits_warning_when_available_refs_cannot_meet_zh_ratio(self):
        refs = [
            self._make_ref("English A", "en", 0.99, 900),
            self._make_ref("English B", "en", 0.98, 800),
            self._make_ref("中文文献C", "zh", 0.97, 700),
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            selected = select_top(refs, 3)

        self.assertEqual(3, len(selected))
        self.assertIn("CNKI", output.getvalue())
        self.assertIn("人工补充", output.getvalue())


if __name__ == "__main__":
    unittest.main()
