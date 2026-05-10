# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.markdown_updater import update_markdown  # noqa: E402


class ChartGeneratorMarkdownReplaceTest(unittest.TestCase):
    def test_update_markdown_replaces_rendered_placeholder_with_relative_image_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "workspace" / "final" / "论文终稿.md"
            output = root / "workspace" / "final" / "images" / "image_1.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            paper.parent.mkdir(parents=True)
            output.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            paper.write_text("系统架构如 [image_1] 所示。", encoding="utf-8")
            output.write_bytes(b"x" * 2048)
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

            updated = update_markdown(paper, manifest, in_place=True, root=root)

            self.assertIn("![图4-1 系统架构图](images/image_1.png)", updated)
            self.assertNotIn("[image_1]", paper.read_text(encoding="utf-8"))

    def test_update_markdown_keeps_pending_user_placeholder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            paper.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            paper.write_text("用户截图待补 [image_5_1]。", encoding="utf-8")
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_5_1",
                                "title": "图5-1 系统截图",
                                "chapter": "第5章",
                                "section": "5.1",
                                "source": "user",
                                "diagram_type": "screenshot",
                                "purpose": "展示界面",
                                "fact_source": "用户提供截图",
                                "placement": "界面说明之后",
                                "status": "pending_user",
                                "description": "用户补图",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            updated = update_markdown(paper, manifest, root=root)

            self.assertEqual("用户截图待补 [image_5_1]。", updated)


if __name__ == "__main__":
    unittest.main()
