# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from charts.render import render_manifest  # noqa: E402


class ChartRendererReportTestCase(unittest.TestCase):
    def test_render_manifest_writes_report_and_updates_manifest_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "final" / "images" / "sources" / "image_1.mmd"
            output = root / "workspace" / "final" / "images" / "image_1.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            report_path = root / "workspace" / "final" / "images" / "render_report.md"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_text("graph LR\nA-->B\n", encoding="utf-8")
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
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            def fake_mermaid_render(source_path, output_path, method="auto"):
                self.assertEqual(source, source_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"x" * 2048)

            with patch("charts.render.mermaid.render", side_effect=fake_mermaid_render):
                report = render_manifest(manifest, root=root, method="auto", report_path=report_path)

            self.assertEqual({"total": 1, "rendered": 1, "failed": 0, "skipped": 0}, report)
            self.assertTrue(output.exists())
            self.assertIn("渲染成功: 1", report_path.read_text(encoding="utf-8"))
            updated = yaml.safe_load(manifest.read_text(encoding="utf-8"))["images"][0]
            self.assertEqual("rendered", updated["render_status"])


if __name__ == "__main__":
    unittest.main()
