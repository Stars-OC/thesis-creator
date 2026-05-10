# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.validate import validate_pipeline  # noqa: E402


class ChartGeneratorImageValidationTest(unittest.TestCase):
    def test_validate_pipeline_counts_pending_user_screenshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            paper.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            paper.write_text("第5章界面占位 [image_5_1] 待用户补图。", encoding="utf-8")
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_5_1",
                                "title": "图5-1 知识库管理界面截图",
                                "chapter": "第5章",
                                "section": "5.1",
                                "source": "user",
                                "diagram_type": "screenshot",
                                "purpose": "展示系统实际运行界面",
                                "fact_source": "用户提供截图",
                                "placement": "界面功能说明之后",
                                "status": "pending_user",
                                "description": "用户后续补充系统实际运行截图",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            report = validate_pipeline(paper, manifest, root=root)

            self.assertEqual([], report["errors"])
            self.assertEqual(["image_5_1"], report["user_required"])

    def test_validate_pipeline_reports_rendered_placeholder_and_small_png(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "workspace" / "final" / "论文终稿.md"
            source = root / "workspace" / "final" / "images" / "sources" / "image_1.mmd"
            output = root / "workspace" / "final" / "images" / "image_1.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            paper.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            manifest.parent.mkdir(parents=True)
            paper.write_text("架构图仍残留 [image_1]。", encoding="utf-8")
            source.write_text("graph LR\nA-->B\n", encoding="utf-8")
            output.write_bytes(b"x" * 128)
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_1",
                                "title": "图4-1 系统架构图",
                                "chapter": "第4章",
                                "section": "4.1",
                                "source": "ai",
                                "diagram_type": "architecture",
                                "purpose": "展示系统架构",
                                "fact_source": "background.md",
                                "placement": "架构说明之后",
                                "status": "pending",
                                "description": "展示系统结构",
                                "engine": "mermaid",
                                "source_file": "workspace/final/images/sources/image_1.mmd",
                                "output_file": "workspace/final/images/image_1.png",
                                "render_status": "rendered",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            report = validate_pipeline(paper, manifest, root=root)

            self.assertTrue(any("仍残留占位符" in error for error in report["errors"]))
            self.assertTrue(any("小于等于 1KB" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
