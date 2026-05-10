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
        self.assertIn("workspace/references/images.yaml", content)
        self.assertIn("verified_metadata_only", content)

    def test_step_0_init_uses_direct_workspace_initialization(self):
        content = (WORKFLOWS_DIR / "step_0_init.md").read_text(encoding="utf-8")
        self.assertIn("通过脚本初始化工作区", content)
        self.assertIn("python scripts/lifecycle.py --workspace thesis-workspace/ --prepare-runtime", content)
        self.assertIn("python scripts/lifecycle.py --workspace thesis-workspace/ --check-workspace", content)
        self.assertIn(".thesis-status.json", content)
        self.assertIn("logs/", content)
        self.assertIn("scripts/charts/render.py", content)
        self.assertIn("workspace/final/images/sources", content)
        self.assertIn("workspace/drafts", content)
        self.assertIn("workspace/reports", content)
        self.assertIn("填写 references/prompt/background.md", content)
        self.assertNotIn("是否初始化工作区", content)

    def test_skill_entry_requires_workspace_preflight_after_init(self):
        content = SKILL_FILE.read_text(encoding="utf-8")
        self.assertIn("python scripts/lifecycle.py --workspace thesis-workspace/ --check-workspace", content)
        self.assertIn("thesis-workspace/.thesis-status.json", content)
        self.assertIn("thesis-workspace/logs/", content)
        self.assertIn("thesis-workspace/scripts/charts/render.py", content)
        self.assertIn("thesis-workspace/workspace/final/images/sources", content)
        self.assertIn("thesis-workspace/workspace/references/images.yaml", content)

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
        self.assertIn("workspace/references/images.yaml", content)
        self.assertIn("正文只保留 `[image_N]`", content)
        self.assertIn("说明写入 `workspace/references/images.yaml`", content)
        self.assertIn("禁止把图片描述", content)
        self.assertIn("Step 4 只负责记录图片需求", content)
        self.assertNotIn("<!-- 图表占位符", content)

    def test_step_8_er_documentation_matches_current_dot_builder_scope(self):
        step8 = (WORKFLOWS_DIR / "step_8_image.md").read_text(encoding="utf-8")
        self.assertIn("从 `background.md` 启发式提取表名、字段和关联关系", step8)
        self.assertIn("图名、表名和字段节点会使用 DOT 安全引用", step8)
        self.assertIn("不承诺完整读取 `er_modeling` 布局配置", step8)
        self.assertIn("不承诺自动归一为英文物理表名", step8)
        self.assertNotIn("唯一配置源：`thesis-workspace/.thesis-config.yaml -> er_modeling`", step8)
        self.assertNotIn("实体居中、字段环绕", step8)
        self.assertNotIn("优先归一到英文物理表名", step8)

    def test_step_8_and_step_9_use_manifest_driven_image_flow(self):
        step8 = (WORKFLOWS_DIR / "step_8_image.md").read_text(encoding="utf-8")
        step9 = (WORKFLOWS_DIR / "step_9_export.md").read_text(encoding="utf-8")
        self.assertIn("workspace/references/images.yaml", step8)
        self.assertIn("回填 Markdown", step8)
        self.assertIn("scripts/charts/manifest_builder.py", step8)
        self.assertIn("scripts/charts/source_writer.py", step8)
        self.assertIn("scripts/charts/render.py", step8)
        self.assertIn("scripts/charts/markdown_updater.py", step8)
        self.assertIn("渲染 PNG", step8)
        self.assertIn("回填", step8)
        self.assertIn("将 [image_N] 替换为 Markdown 图片引用", step8)
        self.assertIn("同步从正文中删除 `image-requirement` 参数块", step8)
        self.assertIn("生成 images.yaml，并同步清除正文参数块", step8)
        self.assertNotIn("--no-render", step8)
        self.assertNotIn("生成模板", step8)
        self.assertIn("正文不得残留 [image_N]", step9)

    def test_reference_workflow_documents_manual_chinese_supplement_and_duplicate_blocking(self):
        reference_workflow = (WORKFLOWS_DIR / "reference_workflow.md").read_text(encoding="utf-8")
        step7 = (WORKFLOWS_DIR / "step_7_merge_detect.md").read_text(encoding="utf-8")
        self.assertIn("CNKI", reference_workflow)
        self.assertIn("万方", reference_workflow)
        self.assertIn("学校图书馆", reference_workflow)
        self.assertIn("禁止伪造", reference_workflow)
        self.assertIn("必须硬阻断", step7)
        self.assertIn("禁止带重复引用进入 AIGC 检测", step7)
    def test_skill_entry_documents_final_gate_and_reference_quality_rules(self):
        content = SKILL_FILE.read_text(encoding="utf-8")
        self.assertIn("scripts/charts/manifest_builder.py", content)
        self.assertIn("scripts/charts/source_writer.py", content)
        self.assertIn("scripts/charts/render.py", content)
        self.assertIn("scripts/charts/markdown_updater.py", content)
        self.assertIn("scripts/charts/validate.py", content)
        self.assertIn("yaml.safe_load", content)
        self.assertIn("CNKI", content)
        self.assertIn("万方", content)
        self.assertIn("学校图书馆", content)
        self.assertIn("必须硬阻断", content)
        self.assertIn("禁止带重复引用进入 AIGC 检测", content)


if __name__ == "__main__":
    unittest.main()
