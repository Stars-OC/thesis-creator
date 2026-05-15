# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.manifest_builder import build_manifest  # noqa: E402
from charts.render import render_manifest  # noqa: E402
from charts.source_writer import prepare_sources, validate_sources  # noqa: E402


class ChartLayoutConfigTestCase(unittest.TestCase):
    def test_architecture_uses_user_source_and_flowchart_uses_plantuml_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paper = root / "workspace" / "final" / "论文终稿.md"
            manifest = root / "workspace" / "references" / "images.yaml"
            sources_dir = root / "workspace" / "final" / "images" / "sources"
            paper.parent.mkdir(parents=True)
            paper.write_text(
                """系统架构如 [image_1] 所示。
<!-- image-requirement
id: image_1
title: 图4-1 系统架构图
chapter: 第4章
section: "4.1"
source: ai
diagram_type: architecture
purpose: 展示系统架构
fact_source: background.md
placement: 架构说明之后
status: pending
description: 展示系统结构
-->
流程如 [image_2] 所示。
<!-- image-requirement
id: image_2
title: 图5-1 登录流程图
chapter: 第5章
section: "5.1"
source: ai
diagram_type: flowchart
purpose: 展示登录流程
fact_source: chapter_5.md
placement: 登录实现说明之后
status: pending
description: 用户登录流程
-->
""",
                encoding="utf-8",
            )

            items = build_manifest(paper, manifest)
            prepare_sources(manifest, sources_dir)

            self.assertEqual(["user", "plantuml"], [item.engine for item in items])
            self.assertFalse((sources_dir / "image_1.mmd").exists())
            self.assertTrue((sources_dir / "image_2.puml").exists())

    def test_plantuml_diagrams_dispatch_to_plantuml_renderer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "final" / "images" / "sources" / "image_3.puml"
            output = root / "workspace" / "final" / "images" / "image_3.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_text("@startuml\nactor 用户\n@enduml\n", encoding="utf-8")
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_3",
                                "title": "图3-1 用例图",
                                "chapter": "第3章",
                                "section": "3.2",
                                "source": "ai",
                                "diagram_type": "usecase",
                                "purpose": "展示系统用例",
                                "fact_source": "outline.md",
                                "placement": "需求分析之后",
                                "status": "pending",
                                "description": "用户和管理员参与系统用例",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            validate_sources(manifest, root=root)

            def fake_plantuml_render(source_path, output_path, method="auto", allow_fallback=False):
                self.assertEqual(source, source_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"x" * 2048)

            with patch("charts.render.plantuml.render", side_effect=fake_plantuml_render):
                report = render_manifest(manifest, root=root)

            self.assertEqual(1, report["rendered"])
            self.assertTrue(output.exists())

    def test_plantuml_renderer_uses_method_from_workspace_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "final" / "images" / "sources" / "image_3.puml"
            output = root / "workspace" / "final" / "images" / "image_3.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            config = root / ".thesis-config.yaml"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_text("@startuml\nactor 用户\n@enduml\n", encoding="utf-8")
            config.write_text(
                "plantuml_render:\n  method: kroki\n",
                encoding="utf-8",
            )
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_3",
                                "title": "图3-1 用例图",
                                "chapter": "第3章",
                                "section": "3.2",
                                "source": "ai",
                                "diagram_type": "usecase",
                                "purpose": "展示系统用例",
                                "fact_source": "outline.md",
                                "placement": "需求分析之后",
                                "status": "pending",
                                "description": "用户和管理员参与系统用例",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            validate_sources(manifest, root=root)
            methods = []

            def fake_plantuml_render(source_path, output_path, method="auto", allow_fallback=False):
                methods.append(method)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"x" * 2048)

            with patch("charts.render.plantuml.render", side_effect=fake_plantuml_render):
                report = render_manifest(manifest, root=root)

            self.assertEqual(1, report["rendered"])
            self.assertEqual(["kroki"], methods)
            self.assertTrue(output.exists())

    def test_plantuml_renderer_accepts_official_server_from_workspace_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "final" / "images" / "sources" / "image_3.puml"
            output = root / "workspace" / "final" / "images" / "image_3.png"
            manifest = root / "workspace" / "references" / "images.yaml"
            config = root / ".thesis-config.yaml"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_text("@startuml\nactor 用户\n@enduml\n", encoding="utf-8")
            config.write_text(
                "plantuml_render:\n  method: official_server\n",
                encoding="utf-8",
            )
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "images": [
                            {
                                "id": "image_3",
                                "title": "图3-1 用例图",
                                "chapter": "第3章",
                                "section": "3.2",
                                "source": "ai",
                                "diagram_type": "usecase",
                                "purpose": "展示系统用例",
                                "fact_source": "outline.md",
                                "placement": "需求分析之后",
                                "status": "pending",
                                "description": "用户和管理员参与系统用例",
                            }
                        ]
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            validate_sources(manifest, root=root)
            methods = []

            def fake_plantuml_render(source_path, output_path, method="auto", allow_fallback=False):
                methods.append(method)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"x" * 2048)

            with patch("charts.render.plantuml.render", side_effect=fake_plantuml_render):
                report = render_manifest(manifest, root=root)

            self.assertEqual(1, report["rendered"])
            self.assertEqual(["official_server"], methods)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
