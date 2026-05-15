# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts import render as render_module
from charts.engines.plantuml import _activity_to_dot, _usecase_to_dot, render


class PlantUMLFallbackTest(unittest.TestCase):
    def test_activity_fallback_keeps_yes_no_edges_and_single_end_node(self):
        dot = _activity_to_dot(
            """
@startuml
start
:提交申请;
if (审核通过?) then (Y)
:生成结果;
else (N)
:退回修改;
endif
stop
@enduml
""".strip()
        )

        self.assertIn("rankdir=TB", dot)
        self.assertIn("Microsoft YaHei", dot)
        self.assertIn("审核通过?", dot)
        self.assertIn("shape=diamond", dot)
        self.assertIn('label="Y"', dot)
        self.assertIn('label="N"', dot)
        self.assertIn("生成结果", dot)
        self.assertIn("退回修改", dot)
        self.assertEqual(1, dot.count('label="结束"'))
        self.assertRegex(dot, r'n\d+ -> n\d+ \[label="Y"\];')
        self.assertRegex(dot, r'n\d+ -> n\d+ \[label="N"\];')

    def test_usecase_fallback_renders_actor_as_person_not_box(self):
        dot = _usecase_to_dot(
            """
@startuml
left to right direction
actor "系统管理员" as SysAdmin
rectangle "在线AI知识库系统" {
    usecase "登录认证" as UC_Login
}
SysAdmin --> UC_Login
@enduml
""".strip()
        )

        self.assertIn("系统管理员", dot)
        self.assertNotIn('SysAdmin [label="系统管理员", shape=box', dot)
        self.assertNotIn('fillcolor="#FFF8E8"', dot)
        self.assertIn("shape=none", dot)
        self.assertIn("SysAdmin -> UC_Login", dot)

    def test_auto_uses_server_renderers_without_graphviz_fallback_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "flow.puml"
            output = Path(tmp) / "flow.png"
            source.write_text("@startuml\nstart\n:处理;\nstop\n@enduml\n", encoding="utf-8")

            with patch("charts.engines.plantuml._render_local", side_effect=RuntimeError("no cli")), \
                    patch("charts.engines.plantuml._render_kroki", side_effect=RuntimeError("kroki down")) as kroki, \
                    patch("charts.engines.plantuml._render_official_server") as official, \
                    patch("charts.engines.plantuml._render_graphviz_fallback") as fallback:
                render(source, output, method="auto")

        kroki.assert_called_once_with(source, output)
        official.assert_called_once_with(source, output)
        fallback.assert_not_called()

    def test_auto_uses_graphviz_fallback_only_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "flow.puml"
            output = Path(tmp) / "flow.png"
            source.write_text("@startuml\nstart\n:处理;\nstop\n@enduml\n", encoding="utf-8")

            with patch("charts.engines.plantuml._render_local", side_effect=RuntimeError("no cli")), \
                    patch("charts.engines.plantuml._render_kroki", side_effect=RuntimeError("kroki down")), \
                    patch("charts.engines.plantuml._render_official_server", side_effect=RuntimeError("official down")), \
                    patch("charts.engines.plantuml._render_graphviz_fallback") as fallback:
                render(source, output, method="auto", allow_fallback=True)

        fallback.assert_called_once_with(source, output)

    def test_kroki_method_uses_graphviz_fallback_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "flow.puml"
            output = Path(tmp) / "flow.png"
            source.write_text("@startuml\nstart\n:处理;\nstop\n@enduml\n", encoding="utf-8")

            with patch("charts.engines.plantuml._render_kroki", side_effect=RuntimeError("kroki down")) as kroki, \
                    patch("charts.engines.plantuml._render_official_server", side_effect=RuntimeError("official down")) as official, \
                    patch("charts.engines.plantuml._render_graphviz_fallback") as fallback:
                render(source, output, method="kroki", allow_fallback=True)

        kroki.assert_called_once_with(source, output)
        official.assert_called_once_with(source, output)
        fallback.assert_called_once_with(source, output)

    def test_manifest_renderer_reads_allow_graphviz_fallback_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".thesis-config.yaml").write_text(
                "plantuml_render:\n  method: auto\n  allow_graphviz_fallback: true\n",
                encoding="utf-8",
            )
            item = type("Item", (), {
                "engine": "plantuml",
                "source_file": "flow.puml",
                "output_file": "flow.png",
            })()

            with patch("charts.render.plantuml.render") as plantuml_render:
                self.assertTrue(render_module._render_item(item, root, method="auto"))

        plantuml_render.assert_called_once_with(root / "flow.puml", root / "flow.png", method="auto", allow_fallback=True)

    def test_manifest_renderer_does_not_apply_plantuml_config_to_mermaid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".thesis-config.yaml").write_text(
                "plantuml_render:\n  method: kroki\n  allow_graphviz_fallback: true\n",
                encoding="utf-8",
            )
            item = type("Item", (), {
                "engine": "mermaid",
                "source_file": "flow.mmd",
                "output_file": "flow.png",
            })()

            with patch("charts.render.mermaid.render") as mermaid_render:
                self.assertTrue(render_module._render_item(item, root, method="auto"))

        mermaid_render.assert_called_once_with(root / "flow.mmd", root / "flow.png", method="auto")


if __name__ == "__main__":
    unittest.main()
