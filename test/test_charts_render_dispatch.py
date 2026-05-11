# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import charts.render as chart_render
from charts.engines import plantuml


MANIFEST_TEXT = """
images:
  - id: image_1
    title: 图4-1 模块图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: module
    purpose: 展示模块关系
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 模块图
    engine: mermaid
    source_file: workspace/final/images/sources/image_1.mmd
    output_file: workspace/final/images/image_1.png
  - id: image_2
    title: 图4-2 ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    purpose: 展示字段
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: ER图
    engine: graphviz
    source_file: workspace/final/images/sources/image_2.dot
    output_file: workspace/final/images/image_2.png
  - id: image_3
    title: 图5-1 时序图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: sequence
    purpose: 展示调用
    fact_source: chapter_5.md
    placement: 图前说明，图后分析
    status: pending
    description: 时序图
    engine: plantuml
    source_file: workspace/final/images/sources/image_3.puml
    output_file: workspace/final/images/image_3.png
  - id: image_4
    title: 图5-2 截图
    chapter: 第5章
    section: "5.1"
    source: user
    diagram_type: screenshot
    purpose: 展示界面
    fact_source: 用户截图
    placement: 图前说明，图后分析
    status: pending_user
    description: 截图
    engine: user
    source_file: ""
    output_file: workspace/final/images/image_4.png
"""


class ChartsRenderDispatchTest(unittest.TestCase):
    def test_render_dispatches_by_engine_and_skips_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            sources.mkdir(parents=True)
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            (sources / "image_1.mmd").write_text("flowchart LR\nA-->B\n", encoding="utf-8")
            (sources / "image_2.dot").write_text("digraph G { A -> B }\n", encoding="utf-8")
            (sources / "image_3.puml").write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")
            calls = []

            def fake_mermaid(source, output, method="auto"):
                calls.append("mermaid")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"png")

            def fake_graphviz(source, output):
                calls.append("graphviz")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"png")

            def fake_plantuml(source, output, method="auto"):
                calls.append("plantuml")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"png")

            original_mermaid = chart_render.mermaid.render
            original_graphviz = chart_render.graphviz.render
            original_plantuml = chart_render.plantuml.render
            try:
                chart_render.mermaid.render = fake_mermaid
                chart_render.graphviz.render = fake_graphviz
                chart_render.plantuml.render = fake_plantuml
                report = chart_render.render_manifest(manifest, root=root)
            finally:
                chart_render.mermaid.render = original_mermaid
                chart_render.graphviz.render = original_graphviz
                chart_render.plantuml.render = original_plantuml

            self.assertEqual(calls, ["mermaid", "graphviz", "plantuml"])
            self.assertEqual(report["rendered"], 3)
            self.assertEqual(report["skipped"], 1)
            self.assertIn("render_status: rendered", manifest.read_text(encoding="utf-8"))

    def test_plantuml_auto_tries_official_server_after_local_and_kroki(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "flow.puml"
            output = root / "flow.png"
            source.write_text("@startuml\nstart\n:开始;\nstop\n@enduml\n", encoding="utf-8")
            calls = []

            def failing_local(src, out):
                calls.append("local")
                raise FileNotFoundError("plantuml")

            def failing_kroki(src, out):
                calls.append("kroki")
                raise TimeoutError("kroki timeout")

            def succeeding_official(src, out):
                calls.append("official")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"png")

            original_local = plantuml._render_local
            original_kroki = plantuml._render_kroki
            original_official = plantuml._render_official_server
            try:
                plantuml._render_local = failing_local
                plantuml._render_kroki = failing_kroki
                plantuml._render_official_server = succeeding_official
                plantuml.render(source, output, method="auto")
            finally:
                plantuml._render_local = original_local
                plantuml._render_kroki = original_kroki
                plantuml._render_official_server = original_official

            self.assertTrue(output.exists())
            self.assertEqual(calls, ["local", "kroki", "official"])

    def test_plantuml_kroki_tries_official_server_after_kroki_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "flow.puml"
            output = root / "flow.png"
            source.write_text("@startuml\nstart\n:开始;\nstop\n@enduml\n", encoding="utf-8")
            calls = []

            def failing_kroki(src, out):
                calls.append("kroki")
                raise TimeoutError("kroki timeout")

            def succeeding_official(src, out):
                calls.append("official")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"png")

            original_kroki = plantuml._render_kroki
            original_official = plantuml._render_official_server
            try:
                plantuml._render_kroki = failing_kroki
                plantuml._render_official_server = succeeding_official
                plantuml.render(source, output, method="kroki")
            finally:
                plantuml._render_kroki = original_kroki
                plantuml._render_official_server = original_official

            self.assertTrue(output.exists())
            self.assertEqual(calls, ["kroki", "official"])

    def test_plantuml_rejects_graphviz_method(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "usecase.puml"
            output = root / "usecase.png"
            source.write_text("@startuml\nactor 用户 as U\nU --> (登录)\n@enduml\n", encoding="utf-8")

            with self.assertRaises(RuntimeError) as ctx:
                plantuml.render(source, output, method="graphviz")

            self.assertIn("PlantUML", str(ctx.exception))
            self.assertIn("graphviz", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
