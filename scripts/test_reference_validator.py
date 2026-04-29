import unittest

from reference_validator import Reference, ReferenceValidator
from reference_engine import VerifiedReference


class FakeCrossRefSearcher:
    def __init__(self, doi_results=None, search_results=None, reachable=None):
        self.doi_results = doi_results or {}
        self.search_results = search_results or []
        self.reachable = reachable or {}

    def verify_doi(self, doi):
        return self.doi_results.get(doi, (False, None))

    def search(self, keywords, year_range=(2020, 2025), limit=5):
        return list(self.search_results)

    def check_doi_reachable(self, doi):
        return self.reachable.get(doi, (False, 404))


class FakeOpenAlexSearcher:
    def __init__(self, results=None):
        self.results = results or []

    def search(self, keywords, year_range=(2020, 2025), limit=5):
        return list(self.results)


class ReferenceValidatorVerificationStatesTest(unittest.TestCase):
    def make_reference(self, doi=""):
        return Reference(
            index=1,
            raw_text="[1] 示例参考文献",
            ref_type="J",
            authors=["张三"],
            title="基于知识图谱的推荐系统研究",
            journal="计算机工程",
            year=2024,
            volume=None,
            issue=None,
            pages=None,
            publisher=None,
            doi=doi,
            url=None,
        )

    def test_sets_verified_metadata_only_when_reference_has_no_doi_but_metadata_matches(self):
        validator = ReferenceValidator(enable_online_validation=False)
        validator.crossref_searcher = FakeCrossRefSearcher(
            search_results=[
                VerifiedReference(
                    title="基于知识图谱的推荐系统研究",
                    authors=["张三"],
                    year=2024,
                    doi="",
                    doi_url="",
                )
            ]
        )
        validator.openalex_searcher = FakeOpenAlexSearcher([])
        validator.searcher = None

        ref = self.make_reference(doi="")
        issues = validator._validate_online(ref)

        self.assertEqual(issues, [])
        self.assertEqual(ref.verification_status, "verified_metadata_only")
        self.assertTrue(ref.metadata_verified)
        self.assertFalse(ref.doi_reachable)

    def test_sets_broken_doi_metadata_ok_when_doi_404_but_metadata_matches(self):
        matched = VerifiedReference(
            title="基于知识图谱的推荐系统研究",
            authors=["张三"],
            year=2024,
            doi="10.1234/example",
            doi_url="https://doi.org/10.1234/example",
        )
        validator = ReferenceValidator(enable_online_validation=False, check_404=True)
        validator.crossref_searcher = FakeCrossRefSearcher(
            doi_results={"10.1234/example": (True, matched)},
            reachable={"10.1234/example": (False, 404)},
        )
        validator.openalex_searcher = FakeOpenAlexSearcher([])
        validator.searcher = None

        ref = self.make_reference(doi="10.1234/example")
        issues = validator._validate_online(ref)

        self.assertEqual(issues, [])
        self.assertEqual(ref.verification_status, "broken_doi_metadata_ok")
        self.assertTrue(ref.metadata_verified)
        self.assertFalse(ref.doi_reachable)

    def test_sets_missing_doi_unverified_when_no_doi_and_no_metadata_match(self):
        validator = ReferenceValidator(enable_online_validation=False)
        validator.crossref_searcher = FakeCrossRefSearcher(search_results=[])
        validator.openalex_searcher = FakeOpenAlexSearcher([])
        validator.searcher = None

        ref = self.make_reference(doi="")
        issues = validator._validate_online(ref)

        self.assertTrue(issues)
        self.assertEqual(ref.verification_status, "missing_doi_unverified")
        self.assertFalse(ref.metadata_verified)
        self.assertFalse(ref.doi_reachable)


if __name__ == "__main__":
    unittest.main()
