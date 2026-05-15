# -*- coding: utf-8 -*-

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.engines import graphviz  # noqa: E402
from charts.render import render_manifest  # noqa: E402


class FakeGraphvizSource:
    calls = []

    def __init__(self, code, format="png", engine="dot"):
        self.calls.append({"code": code, "format": format, "engine": engine})

    def render(self, filename, directory, cleanup=True):
        self.calls[-1].update({"filename": filename, "directory": directory, "cleanup": cleanup})
        output = Path(directory) / f"{Path(filename).name}.png"
        output.write_bytes(b"x")
        return str(output)


class ChartRendererDotTestCase(unittest.TestCase):
    def setUp(self):
        FakeGraphvizSource.calls = []

    def _patch_graphviz_source(self):
        return patch.dict(sys.modules, {"graphviz": types.SimpleNamespace(Source=FakeGraphvizSource)})

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

    def test_graph_level_layout_uses_whitelisted_engine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "image.dot"
            output = root / "image.png"
            source.write_text("digraph G {\n  graph [layout=neato];\n  A -> B;\n}\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual("neato", FakeGraphvizSource.calls[-1]["engine"])

    def test_graph_level_layout_can_appear_after_other_attributes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "image.dot"
            output = root / "image.png"
            source.write_text("digraph G {\n  graph [rankdir=LR, layout=neato];\n  A -> B;\n}\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual("neato", FakeGraphvizSource.calls[-1]["engine"])

    def test_graph_level_layout_can_be_quoted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "image.dot"
            output = root / "image.png"
            source.write_text("digraph G {\n  graph [layout=\"neato\"];\n  A -> B;\n}\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual("neato", FakeGraphvizSource.calls[-1]["engine"])

    def test_node_layout_text_does_not_select_engine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "image.dot"
            output = root / "image.png"
            source.write_text("digraph G {\n  node [layout=neato];\n  A [tooltip=\"layout=neato\"];\n  A -> B;\n}\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual("dot", FakeGraphvizSource.calls[-1]["engine"])

    def test_unknown_graph_level_layout_falls_back_to_dot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "image.dot"
            output = root / "image.png"
            source.write_text("digraph G {\n  graph [layout=unknown];\n  A -> B;\n}\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual("dot", FakeGraphvizSource.calls[-1]["engine"])

    def test_render_uses_absolute_filename_for_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="graphviz path ") as tmpdir:
            root = Path(tmpdir)
            source = root / "sources" / "image 8.dot"
            output = root / "final images" / "image 8.png"
            source.parent.mkdir(parents=True)
            source.write_text("digraph G { A -> B; }\n", encoding="utf-8")

            with self._patch_graphviz_source():
                graphviz.render(source, output)

            self.assertEqual(str(output.with_suffix("")), FakeGraphvizSource.calls[-1]["filename"])
            self.assertEqual(str(output.parent), FakeGraphvizSource.calls[-1]["directory"])


if __name__ == "__main__":
    unittest.main()
