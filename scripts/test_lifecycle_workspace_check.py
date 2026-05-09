# -*- coding: utf-8 -*-

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from lifecycle import check_workspace_preflight, ensure_workspace_structure  # noqa: E402
from status_manager import ThesisStatusManager  # noqa: E402


class LifecycleWorkspaceCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = self.tmp / "thesis-workspace"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_prepare_runtime_creates_required_workspace_files(self):
        ensure_workspace_structure(str(self.workspace), sync_scripts=True)

        self.assertTrue((self.workspace / "scripts").is_dir())
        self.assertTrue((self.workspace / "scripts" / "charts" / "render.py").exists())
        self.assertTrue((self.workspace / "scripts" / "charts" / "source_writer.py").exists())
        self.assertTrue((self.workspace / "scripts" / "charts" / "engines" / "plantuml.py").exists())
        self.assertTrue((self.workspace / "scripts" / "charts" / "engines" / "graphviz.py").exists())
        self.assertTrue((self.workspace / "scripts" / "references" / "reference_engine.py").exists())
        self.assertTrue((self.workspace / "scripts" / "aigc" / "detect.py").exists())
        self.assertFalse((self.workspace / "scripts" / "test_lifecycle_workspace_check.py").exists())
        self.assertTrue((self.workspace / "logs").is_dir())
        self.assertTrue((self.workspace / ".thesis-config.yaml").exists())
        self.assertTrue((self.workspace / "references" / "prompt" / "background.md").exists())
        self.assertTrue((self.workspace / ".thesis-status.json").exists())
        self.assertTrue((self.workspace / "workspace" / "drafts").is_dir())
        self.assertTrue((self.workspace / "workspace" / "final").is_dir())
        self.assertTrue((self.workspace / "workspace" / "final" / "images").is_dir())
        self.assertTrue((self.workspace / "workspace" / "final" / "images" / "sources").is_dir())
        self.assertTrue((self.workspace / "workspace" / "reports").is_dir())
        self.assertTrue((self.workspace / "workspace" / "references" / "images.yaml").exists())
        self.assertTrue((self.workspace / "references" / "templates" / "README.md").exists())
        self.assertTrue((self.workspace / "references" / "examples" / "README.md").exists())
        self.assertTrue((self.workspace / "references" / "guidelines" / "README.md").exists())
        self.assertTrue((self.workspace / "references" / "reference" / "doc" / "README.md").exists())

        report = check_workspace_preflight(self.workspace)
        self.assertTrue(report["ok"])
        self.assertFalse(report["missing"])
        self.assertFalse(report["incomplete"])

    def test_init_and_check_prepares_runtime_and_passes_when_background_exists(self):
        from lifecycle import init_and_check_workspace

        report = init_and_check_workspace(str(self.workspace), sync_scripts=True)

        self.assertTrue((self.workspace / ".thesis-config.yaml").exists())
        self.assertTrue((self.workspace / ".thesis-status.json").exists())
        self.assertTrue((self.workspace / "references" / "templates" / "README.md").exists())
        self.assertTrue(report["ok"])
        self.assertFalse(report["missing"])
        self.assertFalse(report["incomplete"])

    def test_check_workspace_preflight_reports_missing_required_artifacts(self):
        ensure_workspace_structure(str(self.workspace), sync_scripts=True)
        (self.workspace / "references" / "prompt" / "background.md").unlink()
        (self.workspace / "scripts" / "charts" / "render.py").unlink(missing_ok=True)
        shutil.rmtree(self.workspace / "workspace" / "final" / "images" / "sources", ignore_errors=True)

        report = check_workspace_preflight(self.workspace)

        self.assertFalse(report["ok"])
        self.assertIn("references/prompt/background.md", report["missing"])
        self.assertIn("scripts/charts/render.py", report["missing"])
        self.assertIn("workspace/final/images/sources", report["missing"])
        self.assertNotIn(".thesis-config.yaml", report["missing"])
        self.assertNotIn("workspace/references/images.yaml", report["missing"])
        self.assertIn("python scripts/lifecycle.py --workspace thesis-workspace/ --prepare-runtime", report["suggestions"])

    def test_check_workspace_preflight_allows_unfilled_background_template(self):
        ensure_workspace_structure(str(self.workspace), sync_scripts=True)
        background = self.workspace / "references" / "prompt" / "background.md"
        background.write_text("请填写以下信息\n(描述研究领域的现状和问题)", encoding="utf-8")

        report = check_workspace_preflight(self.workspace)

        self.assertTrue(report["ok"])
        self.assertFalse(report["missing"])
        self.assertFalse(report["incomplete"])


if __name__ == "__main__":
    unittest.main()
