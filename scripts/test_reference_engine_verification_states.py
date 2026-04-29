import unittest

from reference_engine import VerifiedReference, ReferenceFormatter


class ReferenceEngineVerificationStatesTest(unittest.TestCase):
    def test_verified_reference_to_dict_includes_verification_fields(self):
        ref = VerifiedReference(
            title="t",
            authors=["a"],
            year=2024,
            doi="",
            doi_url="",
        )
        ref.source_url = "https://example.com/ref"
        ref.verification_status = "verified_metadata_only"
        ref.verification_reason = "标题与作者匹配"
        ref.metadata_verified = True
        ref.doi_reachable = False

        payload = ref.to_dict()

        self.assertEqual(payload["source_url"], "https://example.com/ref")
        self.assertEqual(payload["verification_status"], "verified_metadata_only")
        self.assertEqual(payload["verification_reason"], "标题与作者匹配")
        self.assertTrue(payload["metadata_verified"])
        self.assertFalse(payload["doi_reachable"])

    def test_yaml_formatter_keeps_metadata_only_reference_without_filtering_it_out(self):
        ref = VerifiedReference(
            title="中文文献",
            authors=["作者甲"],
            year=2024,
            doi="",
            doi_url="",
            source_api="OpenAlex",
            language="zh",
        )
        ref.verification_status = "verified_metadata_only"
        ref.verification_reason = "文献本身没有 DOI，但元数据匹配通过"
        ref.metadata_verified = True
        ref.doi_reachable = False

        yaml_text = ReferenceFormatter.format_yaml([ref], pool_id="demo")

        self.assertIn("verification_status: \"verified_metadata_only\"", yaml_text)
        self.assertIn("verification_reason: \"文献本身没有 DOI，但元数据匹配通过\"", yaml_text)
        self.assertIn("metadata_verified: true", yaml_text)
        self.assertIn("doi_reachable: false", yaml_text)
        self.assertIn("title: \"中文文献\"", yaml_text)


if __name__ == "__main__":
    unittest.main()
