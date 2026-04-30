# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path


scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from reference_merger import save_yaml, select_top  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
