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


class ChartRendererDotTestCase(unittest.TestCase):
    def test_render_manifest_dispatches_graphviz_dot_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "final" / "images" / "sources" / "image_4_3.dot"
            output = root / "workspace" / "final" / "images" / "image_4_3.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_text('digraph ER { "用户" [shape=box]; }', encoding="utf-8")
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_4_3",
                                "title": "图4-3 用户概念ER图",
                                "chapter": "第4章",
                                "section": "4.4.1",
                                "source": "ai",
                                "diagram_type": "er",
                                "purpose": "展示用户实体属性",
                                "fact_source": "background.md",
                                "placement": "数据库设计说明之后",
                                "status": "pending",
                                "description": "用户实体包含编号、用户名和状态",
                                "engine": "graphviz",
                                "source_file": "workspace/final/images/sources/image_4_3.dot",
                                "output_file": "workspace/final/images/image_4_3.png",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            def fake_graphviz_render(source_path, output_path):
                self.assertEqual(source, source_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"x" * 2048)

            with patch("charts.render.graphviz.render", side_effect=fake_graphviz_render):
                report = render_manifest(manifest, root=root)

            self.assertEqual(1, report["rendered"])
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
