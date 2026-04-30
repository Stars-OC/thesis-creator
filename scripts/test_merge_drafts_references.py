# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

import yaml


scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from merge_drafts import DraftMerger  # noqa: E402


class DraftMergerReferencesTestCase(unittest.TestCase):
    def _create_references_yaml(self, path: Path):
        data = {
            "pool_id": "thesis_references",
            "generated_at": "2026-04-28",
            "total": 2,
            "selection_limit": 2,
            "references": [
                {
                    "id": "ref_001",
                    "title": "Paper One",
                    "authors": ["Alice"],
                    "year": 2024,
                    "doi": "10.1000/one",
                    "doi_url": "https://doi.org/10.1000/one",
                    "gb7714": "[1] Alice. Paper One[J]. 2024. [DOI](https://doi.org/10.1000/one)",
                },
                {
                    "id": "ref_002",
                    "title": "Paper Two",
                    "authors": ["Bob"],
                    "year": 2023,
                    "doi": "10.1000/two",
                    "doi_url": "https://doi.org/10.1000/two",
                    "gb7714": "[2] Bob. Paper Two[J]. 2023. [DOI](https://doi.org/10.1000/two)",
                },
            ],
        }
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def test_collect_cited_references_preserves_first_seen_order(self):
        merger = DraftMerger("drafts", "output.md")
        content = "引用A[ref_002]，引用B[ref_001]，再次引用A[ref_002]"

        cited = merger.collect_cited_references(content)

        self.assertEqual(["ref_002", "ref_001"], cited)

    def test_generate_references_md_warns_when_citations_exceed_pool_limits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            refs_yaml = tmpdir_path / "verified_references.yaml"
            self._create_references_yaml(refs_yaml)
            output_path = tmpdir_path / "参考文献.md"

            merger = DraftMerger(str(tmpdir_path), str(tmpdir_path / "论文终稿.md"), references_yaml=str(refs_yaml))
            merger.load_references_pool()
            merger.ref_pool["ref_003"] = {
                "id": "ref_003",
                "title": "Paper Three",
                "authors": ["Carol"],
                "year": 2022,
                "doi": "10.1000/three",
                "doi_url": "https://doi.org/10.1000/three",
                "gb7714": "[3] Carol. Paper Three[J]. 2022. [DOI](https://doi.org/10.1000/three)",
            }

            mapping = {"ref_001": 1, "ref_002": 2, "ref_003": 3}
            generated = merger.generate_references_md(mapping, output_path)
            content = output_path.read_text(encoding="utf-8")

        self.assertTrue(generated)
        self.assertEqual(3, merger.merge_report["references_count"])
        self.assertEqual(2, merger.merge_report["reference_pool_total"])
        self.assertEqual(2, merger.merge_report["reference_selection_limit"])
        self.assertTrue(any("超过文献池上限" in warning for warning in merger.merge_report["warnings"]))
        self.assertIn("[3] Carol. Paper Three", content)


if __name__ == "__main__":
    unittest.main()
