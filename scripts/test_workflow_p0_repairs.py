import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = ROOT / "SKILL.md"
WORKFLOWS_DIR = ROOT / "workflows"


class WorkflowP0RepairsTest(unittest.TestCase):
    def test_skill_entry_rules_include_workspace_image_and_reference_updates(self):
        content = SKILL_FILE.read_text(encoding="utf-8")
        self.assertIn("工作区不存在直接初始化", content)
        self.assertIn("[image_1]", content)
        self.assertIn("references/images.yaml", content)
        self.assertIn("verified_metadata_only", content)

    def test_step_0_init_uses_direct_workspace_initialization(self):
        content = (WORKFLOWS_DIR / "step_0_init.md").read_text(encoding="utf-8")
        self.assertIn("工作区不存在时直接初始化", content)
        self.assertIn("填写 references/prompt/background.md", content)
        self.assertNotIn("是否初始化工作区", content)

    def test_reference_workflow_and_step_7_use_layered_verification_states(self):
        reference_workflow = (WORKFLOWS_DIR / "reference_workflow.md").read_text(encoding="utf-8")
        step7 = (WORKFLOWS_DIR / "step_7_merge_detect.md").read_text(encoding="utf-8")
        self.assertIn("verified_metadata_only", reference_workflow)
        self.assertIn("broken_doi_metadata_ok", reference_workflow)
        self.assertIn("文献本身没有 DOI", reference_workflow)
        self.assertIn("missing_doi_unverified", step7)
        self.assertIn("invalid_reference", step7)

    def test_step_4_writing_uses_image_manifest_flow(self):
        content = (WORKFLOWS_DIR / "step_4_writing.md").read_text(encoding="utf-8")
        self.assertIn("[image_1]", content)
        self.assertIn("references/images.yaml", content)
        self.assertIn("Step 4 只负责记录图片需求", content)
        self.assertNotIn("<!-- 图表占位符", content)

    def test_step_8_and_step_9_use_manifest_driven_image_flow(self):
        step8 = (WORKFLOWS_DIR / "step_8_image.md").read_text(encoding="utf-8")
        step9 = (WORKFLOWS_DIR / "step_9_export.md").read_text(encoding="utf-8")
        self.assertIn("读取 references/images.yaml", step8)
        self.assertIn("将 [image_N] 替换为 Markdown 图片引用", step8)
        self.assertIn("正文不得残留 [image_N]", step9)


if __name__ == "__main__":
    unittest.main()
