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
| 文档表 | id, kb_id, title | 存储文档信息 |
| 知识库表 | id, name | 存储知识库信息 |

用户表.role_id 外键关联 角色表.id。
文档表.kb_id 外键关联 知识库表.id。
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
        self.assertIn('"拥有" [shape=diamond', dot)
        self.assertIn('"用户表" -> "拥有" [arrowhead=none];', dot)
        self.assertIn('"拥有" -> "角色表" [arrowhead=none];', dot)
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
        self.assertIn('"用户表（sys_user）" -> "拥有" [arrowhead=none];', dot)
        self.assertIn('"拥有" -> "角色表（sys_role）" [arrowhead=none];', dot)
        self.assertNotIn("label=", dot)

    def test_build_er_dot_from_background_returns_minimal_dot_with_warning_when_tables_missing(self):
        dot, warnings = build_er_dot_from_background("系统采用关系型数据库保存业务数据。", title="图4-1 最小 ER 图")

        self.assertIn('digraph "图4-1 最小 ER 图"', dot)
        self.assertIn('"图4-1 最小 ER 图" [shape=box', dot)
        self.assertTrue(warnings)
        self.assertNotIn("label=", dot)

    def test_build_er_dot_uses_textbook_chen_shapes_for_core_er_diagram(self):
        dot, warnings = build_er_dot_from_background(BACKGROUND_TEXT, title="图4-1 核心ER图")

        self.assertEqual([], warnings)
        self.assertIn('"用户表" [shape=box', dot)
        self.assertIn('"角色表" [shape=box', dot)
        self.assertIn('"拥有" [shape=diamond', dot)
        self.assertIn('"用户表" -> "拥有" [arrowhead=none];', dot)
        self.assertIn('"拥有" -> "角色表" [arrowhead=none];', dot)
        self.assertIn('shape=ellipse', dot)

    def test_build_overall_er_dot_omits_fields_and_marks_cardinality(self):
        dot, warnings = build_er_dot_from_background(BACKGROUND_TEXT, title="图4-1 总体ER图")

        self.assertEqual([], warnings)
        self.assertIn('"用户表" [shape=box', dot)
        self.assertIn('"角色表" [shape=box', dot)
        self.assertIn('"拥有" [shape=diamond', dot)
        self.assertIn('"包含" [shape=diamond', dot)
        self.assertNotIn('"关联" [shape=diamond', dot)
        self.assertNotIn('"用户表_role_id_关联_角色表" [shape=diamond', dot)
        self.assertIn('taillabel="N"', dot)
        self.assertIn('headlabel="1"', dot)
        self.assertNotIn('shape=ellipse', dot)

    def test_build_overall_er_dot_uses_relation_verbs_for_relation_table_lines(self):
        background = """
### 用户表结构
关联表：角色表
| 字段名 | 类型 |
| --- | --- |
| role_id | BIGINT |

### 角色表结构
| 字段名 | 类型 |
| --- | --- |
| role_id | BIGINT |
"""

        dot, warnings = build_er_dot_from_background(background, title="图4-1 总体ER图")

        self.assertEqual([], warnings)
        self.assertIn('"拥有" [shape=diamond];', dot)
        self.assertNotIn('"关联" [shape=diamond];', dot)
        self.assertIn('taillabel="N"', dot)
        self.assertIn('headlabel="1"', dot)

    def test_build_overall_er_dot_does_not_add_generic_relation_from_relation_table_lines(self):
        background = """
### 对话会话表结构
关联表：用户表、知识库表
| 字段名 | 类型 |
| --- | --- |
| conversation_id | BIGINT |
| user_id | BIGINT |
| kb_id | BIGINT |

### 用户表结构
| 字段名 | 类型 |
| --- | --- |
| user_id | BIGINT |

### 知识库表结构
| 字段名 | 类型 |
| --- | --- |
| kb_id | BIGINT |
"""

        dot, warnings = build_er_dot_from_background(background, title="图4-1 总体ER图")

        self.assertEqual([], warnings)
        self.assertIn('"发起" [shape=diamond];', dot)
        self.assertIn('"基于" [shape=diamond];', dot)
        self.assertNotIn('"关联" [shape=diamond];', dot)

    def test_build_overall_er_dot_uses_non_generic_verb_for_unknown_user_relation(self):
        background = """
| 表名 | 字段 | 说明 |
| --- | --- | --- |
| 评论表 | comment_id, user_id, content | 存储评论内容 |
| 用户表 | user_id, username | 存储用户信息 |

评论表.user_id 外键关联 用户表.user_id。
"""

        dot, warnings = build_er_dot_from_background(background, title="图4-1 总体ER图")

        self.assertEqual([], warnings)
        self.assertIn('"归属" [shape=diamond];', dot)
        self.assertNotIn('"关联" [shape=diamond];', dot)

    def test_build_overall_er_dot_uses_non_generic_fallback_when_field_missing(self):
        background = """
| 表名 | 字段 | 说明 |
| --- | --- | --- |
| 订单表 | order_id, user_ref | 存储订单信息 |
| 用户表 | user_id, username | 存储用户信息 |

订单表 关联 用户表。
"""

        dot, warnings = build_er_dot_from_background(background, title="图4-1 总体ER图")

        self.assertEqual([], warnings)
        self.assertIn('"对应" [shape=diamond];', dot)
        self.assertNotIn('"关联" [shape=diamond];', dot)

    def test_prepare_sources_honors_erd_graph_type_from_thesis_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            background = root / "references" / "prompt" / "background.md"
            config = root / ".thesis-config.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            background.write_text(BACKGROUND_TEXT, encoding="utf-8")
            config.write_text("er_modeling:\n  graph_type: erd\n", encoding="utf-8")

            prepare_sources(manifest, sources)
            source = (sources / "image_1.mmd").read_text(encoding="utf-8")

            self.assertIn("erDiagram", source)
            self.assertFalse((sources / "image_1.dot").exists())
            validate_sources(manifest, root=root)

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

    def test_prepare_sources_rewrites_existing_overall_er_dot_without_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            background = root / "references" / "prompt" / "background.md"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            sources.mkdir(parents=True)
            manifest.write_text(MANIFEST_TEXT.strip().replace("diagram_type: er", "diagram_type: overall_er").replace("图4-1 用户角色ER图", "图4-1 总体ER图"), encoding="utf-8")
            background.write_text(BACKGROUND_TEXT, encoding="utf-8")
            dot_path = sources / "image_1.dot"
            dot_path.write_text("digraph \"图4-1 总体ER图\" {\n  \"用户表\" [shape=box];\n  \"角色表\" [shape=box];\n  \"用户表_role_id_关联_角色表\" [shape=diamond];\n  \"用户表\" -> \"用户表_role_id_关联_角色表\" [arrowhead=none, taillabel=\"N\", labeldistance=1.5];\n  \"用户表_role_id_关联_角色表\" -> \"角色表\" [arrowhead=none, headlabel=\"1\", labeldistance=1.5];\n}\n", encoding="utf-8")

            prepare_sources(manifest, sources)
            dot = dot_path.read_text(encoding="utf-8")

            self.assertIn('"拥有" [shape=diamond];', dot)
            self.assertIn('"包含" [shape=diamond];', dot)
            self.assertNotIn('"关联" [shape=diamond];', dot)
            self.assertNotIn('"用户表_role_id_关联_角色表" [shape=diamond];', dot)
            self.assertIn('taillabel="N"', dot)
            self.assertIn('headlabel="1"', dot)
            self.assertNotIn('shape=ellipse', dot)
            self.assertNotIn('style=dotted, arrowhead=none', dot)
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
