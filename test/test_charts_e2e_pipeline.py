# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import charts.render as chart_render
from charts.manifest_builder import build_manifest
from charts.markdown_updater import update_markdown
from charts.source_writer import prepare_sources
from charts.validate import validate_pipeline


class ChartsE2EPipelineTest(unittest.TestCase):
    def test_manifest_source_render_update_validate_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            md = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            md.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            md.write_text(
                """
[image_1]
<!-- image-requirement
id: image_1
title: 图4-1 系统架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统架构
fact_source: background.md
placement: 图前说明，图后分析
status: pending
description: 架构图
-->
[image_2]
<!-- image-requirement
id: image_2
title: 图4-2 用户表ER图
chapter: 第4章
section: "4.4"
source: ai
diagram_type: er
purpose: 展示用户表字段
fact_source: background.md
placement: 图前说明，图后分析
status: pending
description: ER图
-->
[image_3]
<!-- image-requirement
id: image_3
title: 图5-1 登录时序图
chapter: 第5章
section: "5.1"
source: ai
diagram_type: sequence
purpose: 展示登录调用
fact_source: chapter_5.md
placement: 图前说明，图后分析
status: pending
description: 时序图
-->
""".strip(),
                encoding="utf-8",
            )

            build_manifest(md, manifest)
            prepare_sources(manifest, sources)
            image_1 = root / "workspace" / "final" / "images" / "image_1.png"
            image_1.parent.mkdir(parents=True, exist_ok=True)
            image_1.write_bytes(b"x" * 2048)
            (sources / "image_2.dot").write_text("digraph G { A -> B }\n", encoding="utf-8")
            (sources / "image_3.puml").write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")

            original_mermaid = chart_render.mermaid.render
            original_graphviz = chart_render.graphviz.render
            original_plantuml = chart_render.plantuml.render

            def fake_render(source, output, method="auto"):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"x" * 2048)

            def fake_graphviz(source, output):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"x" * 2048)

            try:
                chart_render.mermaid.render = fake_render
                chart_render.graphviz.render = fake_graphviz
                chart_render.plantuml.render = fake_render
                report = chart_render.render_manifest(manifest, root=root)
            finally:
                chart_render.mermaid.render = original_mermaid
                chart_render.graphviz.render = original_graphviz
                chart_render.plantuml.render = original_plantuml

            updated = update_markdown(md, manifest, in_place=True, root=root)
            validation = validate_pipeline(md, manifest, root=root)

            self.assertEqual(report["rendered"], 2)
            self.assertTrue((root / "workspace" / "final" / "images" / "image_1.png").exists())
            self.assertIn("[image_1]", updated)
            self.assertNotIn("[image_2]", updated)
            self.assertNotIn("[image_3]", updated)
            self.assertEqual(validation["errors"], [])


if __name__ == "__main__":
    unittest.main()
