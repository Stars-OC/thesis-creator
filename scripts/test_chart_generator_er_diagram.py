# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from charts.schemas import ImageItem, default_source_file, infer_engine, source_suffix  # noqa: E402


class ChartGeneratorERDiagramTestCase(unittest.TestCase):
    def test_er_diagram_defaults_to_graphviz_dot_source(self):
        item = ImageItem.from_dict(
            {
                "id": "image_4_3",
                "title": "图4-3 用户概念ER图",
                "chapter": "第4章",
                "section": "4.4.1",
                "source": "ai",
                "diagram_type": "er",
                "purpose": "展示用户实体及其属性",
                "fact_source": "thesis-workspace/references/prompt/background.md",
                "placement": "数据库概念结构说明之后",
                "status": "pending",
                "description": "用户实体包含编号、用户名、手机号、状态等属性",
            }
        )

        self.assertEqual("graphviz", item.engine)
        self.assertEqual("workspace/final/images/sources/image_4_3.dot", item.source_file)
        self.assertEqual("workspace/final/images/image_4_3.png", item.output_file)

    def test_engine_suffixes_include_plantuml_and_mermaid(self):
        self.assertEqual(".dot", source_suffix("graphviz"))
        self.assertEqual(".mmd", source_suffix("mermaid"))
        self.assertEqual(".puml", source_suffix("plantuml"))
        self.assertEqual("", source_suffix("user"))

    def test_infer_engine_keeps_user_screenshots_unrendered(self):
        self.assertEqual("user", infer_engine({"source": "user", "diagram_type": "screenshot"}))
        self.assertEqual("", default_source_file("image_5_1", "user"))


if __name__ == "__main__":
    unittest.main()
