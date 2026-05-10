# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.er_dot_builder import build_er_dot_from_background
from charts.source_writer import PLACEHOLDER_MARKER, prepare_sources, validate_sources


BACKGROUND_TEXT = """
# 数据库设计

| 表名 | 字段 | 说明 |
| --- | --- | --- |
| 用户表 | id, username, password, role_id | 存储用户账号信息 |
| 角色表 | id, role_name | 存储角色信息 |

用户表.role_id 外键关联 角色表.id。
"""


MANIFEST_TEXT = """
images:
  - id: image_1
    title: 图4-1 用户角色ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    engine: graphviz
    purpose: 展示用户和角色表关系
    fact_source: references/prompt/background.md
    placement: 数据库设计说明之后
    status: pending
    description: 用户表和角色表ER图
"""


class ChartsErDotBuilderTest(unittest.TestCase):
    def test_build_er_dot_from_background_extracts_tables_fields_and_relations(self):
        dot, warnings = build_er_dot_from_background(BACKGROUND_TEXT, title="用户角色ER图")

        self.assertEqual([], warnings)
        self.assertIn("digraph", dot)
        self.assertIn("用户表", dot)
        self.assertIn("username", dot)
        self.assertIn("角色表", dot)
        self.assertIn("role_name", dot)
        self.assertIn('"用户表" -> "角色表"', dot)
        self.assertNotIn("label=", dot)

    def test_build_er_dot_quotes_graph_and_table_names_with_special_characters(self):
        background = """
| 表名 | 字段 | 说明 |
| --- | --- | --- |
| 用户表（sys_user） | id, username, role_id | 存储用户账号信息 |
| 角色表（sys_role） | id, role_name | 存储角色信息 |

用户表（sys_user）.role_id 外键关联 角色表（sys_role）.id。
"""

        dot, warnings = build_er_dot_from_background(background, title="图4-1 用户角色 ER 图")

        self.assertEqual([], warnings)
        self.assertIn('digraph "图4-1 用户角色 ER 图"', dot)
        self.assertIn('"用户表（sys_user）" [shape=box', dot)
        self.assertIn('"角色表（sys_role）" [shape=box', dot)
        self.assertIn('"用户表（sys_user）" -> "角色表（sys_role）";', dot)
        self.assertNotIn("label=", dot)

    def test_build_er_dot_from_background_returns_minimal_dot_with_warning_when_tables_missing(self):
        dot, warnings = build_er_dot_from_background("系统采用关系型数据库保存业务数据。", title="图4-1 最小 ER 图")

        self.assertIn('digraph "图4-1 最小 ER 图"', dot)
        self.assertIn('"图4-1 最小 ER 图" [shape=box', dot)
        self.assertTrue(warnings)
        self.assertNotIn("label=", dot)

    def test_prepare_sources_writes_real_er_dot_from_fact_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            background = root / "references" / "prompt" / "background.md"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            background.write_text(BACKGROUND_TEXT, encoding="utf-8")

            prepare_sources(manifest, sources)
            dot_path = sources / "image_1.dot"
            dot = dot_path.read_text(encoding="utf-8")

            self.assertTrue(dot_path.exists())
            self.assertIn("digraph", dot)
            self.assertIn("用户表", dot)
            self.assertIn("角色表", dot)
            self.assertNotIn(PLACEHOLDER_MARKER, dot)
            self.assertNotIn("label=", dot)
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
