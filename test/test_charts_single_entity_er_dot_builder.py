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
        self.assertIn("overlap=scale", dot)
        self.assertIn("splines=false", dot)
        self.assertNotIn("rank", dot)

    def test_entity_centered_with_pos(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('shape=rectangle', dot)
        self.assertIn('pos="0,0!"', dot)

    def test_attributes_are_ellipses_without_fixed_pos(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('shape=ellipse', dot)
        self.assertNotIn('[shape=ellipse, pos=', dot)

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

    def test_attribute_nodes_do_not_have_fixed_positions(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )
        self.assertEqual([], warnings)
        self.assertIn('"用户表" [shape=rectangle, pos="0,0!"', dot)
        self.assertIn('"user_id" [shape=ellipse];', dot)
        self.assertNotIn('"user_id" [shape=ellipse, pos=', dot)

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
        self.assertIn('len=1.4', dot)
        self.assertIn('"文档表" -- "doc_id" [len=1.4];', dot)
        self.assertNotIn('"doc_id" [shape=ellipse, pos=', dot)

    def test_single_entity_er_uses_readable_spread_field_ring(self):
        dot, warnings = build_single_entity_er_dot(
            BACKGROUND_TEXT, title="图4-8 用户表实体图", focus_hint="用户表"
        )

        self.assertEqual([], warnings)
        self.assertIn("margin=0", dot)
        self.assertIn("pad=0", dot)
        self.assertIn("nodesep=0.3", dot)
        self.assertIn('sep="+5"', dot)
        self.assertIn("fontsize=10", dot)
        self.assertIn('margin="0.08,0.04"', dot)
        self.assertIn('"用户表" -- "user_id" [len=1];', dot)
        self.assertNotIn('[shape=ellipse, pos=', dot)

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

    def test_chinese_fields_use_llm_supplied_display_names_without_script_rewriting(self):
        background = """
### API密钥表结构
| 字段名 | 显示名 | 类型 | 说明 |
| --- | --- | --- | --- |
| kb_scopes | 授权范围 | VARCHAR | 授权知识库ID列表，JSON数组 |
| rate_limit | 每分钟调用次数上限 | INT | 接口限流配置，由大模型判断是否需要保留较长字段名 |
| last_called_at | 最近调用时间 | DATETIME | 最近一次调用时间 |
"""
        dot, warnings = build_single_entity_er_dot(
            background, title="API密钥表实体图", focus_hint="API密钥表", field_language="chinese"
        )
        self.assertEqual([], warnings)
        self.assertIn('"授权范围" [shape=ellipse', dot)
        self.assertIn('"每分钟调用次数上限" [shape=ellipse', dot)
        self.assertIn('"最近调用时间" [shape=ellipse', dot)
        self.assertNotIn('"授权知识库ID列表，JSON数组" [shape=ellipse', dot)
        self.assertNotIn('"接口限流配置，由大模型判断是否需要保留较长字段名" [shape=ellipse', dot)

    def test_chinese_fields_do_not_infer_names_from_description_column(self):
        background = """
### API密钥表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| kb_scopes | VARCHAR | 授权知识库ID列表，JSON数组 |
"""
        dot, warnings = build_single_entity_er_dot(
            background, title="API密钥表实体图", focus_hint="API密钥表", field_language="chinese"
        )
        self.assertEqual([], warnings)
        self.assertIn('"kb_scopes" [shape=ellipse', dot)
        self.assertNotIn('"授权知识库ID列表，JSON数组" [shape=ellipse', dot)

    def test_many_fields_over_eight_are_farther_from_center(self):
        background = """
### API密钥表结构
| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| key_id | BIGINT | 密钥编号 |
| user_id | BIGINT | 用户编号 |
| api_key | VARCHAR | API密钥 |
| key_name | VARCHAR | 密钥名称 |
| kb_scopes | VARCHAR | 授权知识库范围 |
| rate_limit | INT | 每分钟调用次数上限 |
| call_count | BIGINT | 累计调用次数 |
| last_called_at | DATETIME | 最近一次调用时间 |
| status | TINYINT | 密钥状态 |
| expires_at | DATETIME | 过期时间 |
| created_at | DATETIME | 创建时间 |
"""
        dot, warnings = build_single_entity_er_dot(
            background, title="API密钥表实体图", focus_hint="API密钥表", field_language="chinese"
        )
        self.assertEqual([], warnings)
        self.assertIn('len=1.4', dot)
        self.assertIn('"API密钥表" -- "key_id" [len=1.4];', dot)
        self.assertNotIn('[shape=ellipse, pos=', dot)

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
        self.assertIn('"用户\\"表" -- "api\\\\key" [len=1];', dot)
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
            self.assertIn("overlap=scale", dot)
            self.assertIn("margin=0", dot)
            self.assertIn("nodesep=0.3", dot)
            self.assertIn('"用户表" -- "user_id" [len=1];', dot)
            self.assertIn('"user_id" [shape=ellipse];', dot)
            self.assertNotIn('[shape=ellipse, pos=', dot)
            self.assertIn('"username" [shape=ellipse', dot)
            self.assertIn('"password" [shape=ellipse', dot)
            validate_sources(manifest, root=root)


if __name__ == "__main__":
    unittest.main()
