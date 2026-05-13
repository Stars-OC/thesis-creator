# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
import sys
import tempfile

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.single_entity_er_dot_builder import build_single_entity_er_dot
from charts.source_writer import prepare_sources, validate_sources


BACKGROUND_TEXT = """
### 用户表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| user_id | BIGINT | 用户编号 |
| username | VARCHAR | 用户名 |
| password | VARCHAR | 密码 |
| email | VARCHAR | 邮箱 |
| phone | VARCHAR | 手机号 |
| role_id | BIGINT | 角色编号 |
| status | TINYINT | 状态 |
| created_at | DATETIME | 创建时间 |

### 角色表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| role_id | BIGINT | 角色编号 |
| role_name | VARCHAR | 角色名称 |

用户表.role_id 外键关联 角色表.role_id。
"""


class BuildSingleEntityErDotTest(unittest.TestCase):
    def test_output_is_graph_er_not_digraph(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn("graph ER", dot)
        self.assertNotIn("digraph", dot)

    def test_uses_neato_layout_without_rank(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn("layout=neato", dot)
        self.assertIn("overlap=true", dot)
        self.assertIn("splines=true", dot)
        self.assertNotIn("rank", dot)

    def test_entity_centered_with_pos(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('shape=rectangle', dot)
        self.assertIn('pos="0,0!"', dot)

    def test_attributes_are_ellipses_with_pos(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('shape=ellipse', dot)

    def test_no_diamond_in_single_entity(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertNotIn("diamond", dot)

    def test_edges_use_double_dash(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn(" -- ", dot)
        self.assertNotIn(" -> ", dot)

    def test_no_label_assignment(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertNotIn("label=", dot)

    def test_attributes_surround_entity_in_all_four_directions(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        import re
        positions = re.findall(r'pos="(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)!"', dot)
        has_above = any(float(y) > 0 for _, y in positions)
        has_below = any(float(y) < 0 for _, y in positions)
        has_left = any(float(x) < 0 for x, _ in positions)
        has_right = any(float(x) > 0 for x, _ in positions)
        self.assertTrue(has_above, "No attribute above entity")
        self.assertTrue(has_below, "No attribute below entity")
        self.assertTrue(has_left, "No attribute left of entity")
        self.assertTrue(has_right, "No attribute right of entity")

    def test_many_fields_still_surround_not_top_stacked(self):
        background = """
### 文档表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| doc_id | BIGINT | 文档编号 |
| kb_id | BIGINT | 知识库编号 |
| uploader_id | BIGINT | 上传者编号 |
| filename | VARCHAR | 文件名 |
| file_type | VARCHAR | 文件类型 |
| file_size | BIGINT | 文件大小 |
| storage_path | VARCHAR | 存储路径 |
| parse_status | TINYINT | 解析状态 |
| segment_count | INT | 分段数量 |
| error_message | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |
"""
        dot, warnings = build_single_entity_er_dot(
            background, title="文档表实体图", focus_hint="文档表"
        )
        self.assertEqual([], warnings)
        import re
        positions = re.findall(r'pos="(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)!"', dot)
        has_above = any(float(y) > 0 for _, y in positions)
        has_below = any(float(y) < 0 for _, y in positions)
        has_left = any(float(x) < 0 for x, _ in positions)
        has_right = any(float(x) > 0 for x, _ in positions)
        self.assertTrue(has_above)
        self.assertTrue(has_below)
        self.assertTrue(has_left)
        self.assertTrue(has_right)

    def test_single_entity_er_uses_more_compact_field_ring(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )

        self.assertEqual([], warnings)
        self.assertIn("margin=0", dot)
        self.assertIn("pad=0", dot)
        self.assertIn("nodesep=0.15", dot)
        self.assertIn("sep=0.08", dot)
        self.assertIn("fontsize=10", dot)
        self.assertIn('margin="0.04,0.02"', dot)
        self.assertIn('pos="0.0,1.8!"', dot)
        self.assertNotIn('pos="0,3!"', dot)

    def test_single_table_only_no_other_tables(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn("用户表", dot)
        self.assertNotIn("角色表", dot)

    def test_multi_table_hint_fails_closed(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="用户与角色实体关系图", focus_hint="用户表与角色表"
        )
        self.assertTrue(warnings)
        self.assertNotIn("用户表", dot)
        self.assertNotIn("角色表", dot)

    def test_no_match_fails_closed(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="权限管理图", focus_hint="权限管理核心"
        )
        self.assertTrue(warnings)
        self.assertNotIn("用户表", dot)
        self.assertNotIn("角色表", dot)

    def test_ellipse_nodes_use_field_names_not_comments(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('"user_id" [shape=ellipse', dot)
        self.assertIn('"username" [shape=ellipse', dot)
        self.assertNotIn('"用户编号" [shape=ellipse', dot)
        self.assertNotIn('"用户名" [shape=ellipse', dot)

    def test_single_entity_er_escapes_table_and_field_dot_ids(self):
        background = """
### 用户"表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| api\\key | VARCHAR | API密钥 |
| token"hash | VARCHAR | 令牌摘要 |
"""
        dot, warnings = build_single_entity_er_dot(
            background, title="特殊字符实体图", focus_hint="用户表"
        )

        self.assertEqual([], warnings)
        self.assertIn('"用户\\"表" [shape=rectangle', dot)
        self.assertIn('"api\\\\key" [shape=ellipse', dot)
        self.assertIn('"token\\"hash" [shape=ellipse', dot)
        self.assertIn('"用户\\"表" -- "api\\\\key";', dot)
        self.assertNotIn('"token"hash"', dot)


class PrepareSourcesSingleEntityErTest(unittest.TestCase):
    MANIFEST_TEXT = """
images:
  - id: image_20
    title: 图5-1 用户表实体图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: single_entity_er
    engine: graphviz
    purpose: 展示用户表实体字段结构
    fact_source: references/prompt/background.md
    placement: 用户表说明之后
    status: pending
    description: 用户表单实体ER图
"""

    def test_prepare_sources_writes_dot_for_single_entity_er(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            background = root / "references" / "prompt" / "background.md"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(self.MANIFEST_TEXT.strip(), encoding="utf-8")
            background.write_text(BACKGROUND_TEXT, encoding="utf-8")

            prepare_sources(manifest, sources)
            dot_path = sources / "image_20.dot"
            self.assertTrue(dot_path.exists())
            dot = dot_path.read_text(encoding="utf-8")
            self.assertIn("graph ER", dot)
            self.assertIn("layout=neato", dot)
            self.assertIn("overlap=true", dot)
            self.assertIn("margin=0", dot)
            self.assertIn("nodesep=0.15", dot)
            self.assertIn('pos="0.0,1.8!"', dot)
            self.assertIn('"user_id" [shape=ellipse', dot)
            self.assertIn('"username" [shape=ellipse', dot)
            self.assertIn('"password" [shape=ellipse', dot)
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
