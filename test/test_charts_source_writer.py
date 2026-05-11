# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.schemas import load_manifest
from charts.source_writer import prepare_sources, validate_sources


MANIFEST_TEXT = """
images:
  - id: image_1
    title: 图4-1 系统整体架构图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: architecture
    purpose: 展示系统整体分层
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 架构图需求
  - id: image_2
    title: 图4-2 用户表ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    purpose: 展示用户表字段
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: ER图需求
  - id: image_3
    title: 图5-1 登录时序图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: sequence
    purpose: 展示登录调用顺序
    fact_source: chapter_5.md
    placement: 图前说明，图后分析
    status: pending
    description: 时序图需求
  - id: image_4
    title: 图5-2 登录流程图
    chapter: 第5章
    section: "5.1"
    source: ai
    diagram_type: flowchart
    purpose: 展示登录流程
    fact_source: chapter_5.md
    placement: 图前说明，图后分析
    status: pending
    description: 流程图需求
  - id: image_5
    title: 图5-3 登录截图
    chapter: 第5章
    section: "5.1"
    source: user
    diagram_type: screenshot
    purpose: 展示系统界面
    fact_source: 用户运行截图
    placement: 图前说明，图后分析
    status: pending_user
    description: 用户补充截图
"""


class ChartsSourceWriterTest(unittest.TestCase):
    def test_prepare_sources_creates_engine_specific_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")

            items = prepare_sources(manifest, sources)

            self.assertFalse((sources / "image_1.mmd").exists())
            self.assertTrue((sources / "image_2.dot").exists())
            self.assertTrue((sources / "image_3.puml").exists())
            self.assertTrue((sources / "image_4.puml").exists())
            self.assertFalse((sources / "image_5").exists())
            self.assertNotIn("source_file: workspace/final/images/sources/image_1.mmd", manifest.read_text(encoding="utf-8"))
            self.assertEqual(load_manifest(manifest)[0].source_file, "")
            self.assertEqual(items[0].engine, "user")
            self.assertEqual(items[3].engine, "plantuml")
            self.assertEqual(items[4].engine, "user")

    def test_prepare_sources_uses_mermaid_only_when_er_graph_type_is_erd(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            (root / ".thesis-config.yaml").write_text("er_modeling:\n  graph_type: erd\n", encoding="utf-8")
            (root / "workspace" / "references" / "prompt").mkdir(parents=True)
            (root / "workspace" / "references" / "prompt" / "background.md").write_text("| 表名 | 字段 |\n| 用户表 | 用户ID, 用户名 |\n", encoding="utf-8")

            items = prepare_sources(manifest, sources)

            self.assertEqual(items[0].engine, "mermaid")
            self.assertTrue((sources / "image_1.mmd").exists())
            self.assertIn("erDiagram", (sources / "image_1.mmd").read_text(encoding="utf-8"))

    def test_prepare_sources_overrides_legacy_er_engine_from_config(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
    engine: mermaid
    source_file: workspace/final/images/sources/image_1.mmd
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            (root / ".thesis-config.yaml").write_text("er_modeling:\n  graph_type: dot\n", encoding="utf-8")

            items = prepare_sources(manifest, sources)

            self.assertEqual(items[0].engine, "graphviz")
            self.assertEqual(items[0].source_file, "workspace/final/images/sources/image_1.dot")
            self.assertTrue((sources / "image_1.dot").exists())
            self.assertFalse((sources / "image_1.mmd").exists())

    def test_prepare_sources_rewrites_legacy_er_dot_source(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
    engine: graphviz
    source_file: workspace/final/images/sources/image_1.dot
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            background = root / "references" / "prompt" / "background.md"
            manifest.parent.mkdir(parents=True)
            sources.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            background.write_text("| 表名 | 字段 |\n| --- | --- |\n| 用户表 | 用户ID, 用户名 |\n", encoding="utf-8")
            (sources / "image_1.dot").write_text('digraph G { 用户表 [label="旧ER"] }\n', encoding="utf-8")

            prepare_sources(manifest, sources)

            source = (sources / "image_1.dot").read_text(encoding="utf-8")
            self.assertIn("shape=box", source)
            self.assertNotIn("shape=ellipse", source)
            self.assertNotIn("label=", source)

    def test_prepare_sources_rewrites_legacy_overall_er_with_generic_relation_nodes(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
    engine: graphviz
    source_file: workspace/final/images/sources/image_1.dot
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            background = root / "references" / "prompt" / "background.md"
            manifest.parent.mkdir(parents=True)
            sources.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            background.write_text("""### 用户表结构
关联表：角色表
| 字段名 | 类型 |
| --- | --- |
| role_id | BIGINT |

### 角色表结构
| 字段名 | 类型 |
| --- | --- |
| role_id | BIGINT |
""", encoding="utf-8")
            (sources / "image_1.dot").write_text("""digraph \"图4-1 总体ER图\" {
  \"用户表\" [shape=box];
  \"角色表\" [shape=box];
  \"关联\" [shape=diamond];
  \"用户表\" -> \"关联\" [arrowhead=none, taillabel=\"N\", labeldistance=1.5];
  \"关联\" -> \"角色表\" [arrowhead=none, headlabel=\"1\", labeldistance=1.5];
}
""", encoding="utf-8")

            prepare_sources(manifest, sources)

            source = (sources / "image_1.dot").read_text(encoding="utf-8")
            self.assertIn('"拥有" [shape=diamond];', source)
            self.assertNotIn('"关联" [shape=diamond];', source)

    def test_prepare_sources_preserves_current_er_dot_without_relationships(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 用户ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    purpose: 展示用户实体字段
    fact_source: background.md
    placement: 数据库设计说明之后
    status: pending
    description: 用户实体ER图
    engine: graphviz
    source_file: workspace/final/images/sources/image_1.dot
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            sources.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            original = """digraph "图4-1 用户ER图" {
  graph [rankdir=LR, bgcolor=white];
  "用户表" [shape=box];
  "用户表_用户ID" [shape=ellipse];
  "用户表" -> "用户表_用户ID" [style=dotted, arrowhead=none];
}
"""
            (sources / "image_1.dot").write_text(original, encoding="utf-8")

            prepare_sources(manifest, sources)

            self.assertEqual(original, (sources / "image_1.dot").read_text(encoding="utf-8"))

    def test_prepare_sources_rewrites_legacy_single_er_relation_nodes(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 核心ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: er
    purpose: 展示核心实体字段与关系
    fact_source: background.md
    placement: 数据库设计说明之后
    status: pending
    description: 核心ER图
    engine: graphviz
    source_file: workspace/final/images/sources/image_1.dot
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            background = root / "references" / "prompt" / "background.md"
            manifest.parent.mkdir(parents=True)
            sources.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            background.write_text("""| 表名 | 字段 |
| --- | --- |
| 用户表 | user_id, role_id |
| 角色表 | role_id |

用户表.role_id 外键关联 角色表.role_id。
""", encoding="utf-8")
            (sources / "image_1.dot").write_text("""digraph "图4-1 核心ER图" {
  "用户表" [shape=box];
  "角色表" [shape=box];
  "用户表_role_id_关联_角色表" [shape=diamond];
  "用户表" -> "用户表_role_id_关联_角色表" [arrowhead=none];
  "用户表_role_id_关联_角色表" -> "角色表" [arrowhead=none];
}
""", encoding="utf-8")

            prepare_sources(manifest, sources)

            source = (sources / "image_1.dot").read_text(encoding="utf-8")
            self.assertIn('"拥有" [shape=diamond];', source)
            self.assertNotIn('"用户表_role_id_关联_角色表" [shape=diamond];', source)

    def test_prepare_sources_prefers_background_for_er_fact_source(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: chapter_4.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            background = root / "references" / "prompt" / "background.md"
            chapter = root / "chapter_4.md"
            manifest.parent.mkdir(parents=True)
            background.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")
            background.write_text("| 表名 | 字段 |\n| --- | --- |\n| 用户表 | 用户ID, 用户名 |\n", encoding="utf-8")
            chapter.write_text("| 表名 | 字段 |\n| --- | --- |\n| 订单表 | 订单ID, 用户ID |\n", encoding="utf-8")

            prepare_sources(manifest, sources)

            source = (sources / "image_1.dot").read_text(encoding="utf-8")
            self.assertIn("用户表", source)
            self.assertNotIn("订单表", source)

    def test_prepare_sources_sorts_overall_er_first_for_existing_manifest(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 模块图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: module
    purpose: 展示模块关系
    fact_source: background.md
    placement: 模块说明之后
    status: pending
    description: 模块图
  - id: image_2
    title: 图4-2 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")

            prepare_sources(manifest, sources)

            items = load_manifest(manifest)
            self.assertEqual("overall_er", items[0].diagram_type)

    def test_prepare_sources_keeps_non_overall_items_in_original_order(self):
        manifest_text = """
images:
  - id: image_10
    title: 图5-2 时序图
    chapter: 第5章
    section: "5.2"
    source: ai
    diagram_type: sequence
    purpose: 展示调用顺序
    fact_source: chapter_5.md
    placement: 时序说明之后
    status: pending
    description: 时序图
  - id: image_2
    title: 图4-2 总体ER图
    chapter: 第4章
    section: "4.4"
    source: ai
    diagram_type: overall_er
    purpose: 展示总体实体关系
    fact_source: background.md
    placement: 数据库设计开头展示
    status: pending
    description: 总体ER图
  - id: image_1
    title: 图4-1 模块图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: module
    purpose: 展示模块关系
    fact_source: background.md
    placement: 模块说明之后
    status: pending
    description: 模块图
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "workspace" / "references" / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(manifest_text.strip(), encoding="utf-8")

            prepare_sources(manifest, sources)

            self.assertEqual(["image_2", "image_10", "image_1"], [item.id for item in load_manifest(manifest)])

    def test_architecture_status_is_normalized_to_pending_user(self):
        manifest_text = """
images:
  - id: image_1
    title: 图4-1 系统整体架构图
    chapter: 第4章
    section: "4.1"
    source: ai
    diagram_type: architecture
    purpose: 展示系统整体分层
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 架构图需求
    engine: mermaid
    source_file: workspace/final/images/sources/image_1.mmd
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            manifest.write_text(manifest_text.strip(), encoding="utf-8")

            item = load_manifest(manifest)[0]

            self.assertEqual("pending_user", item.status)
            self.assertEqual("pending_user", item.render_status)
            self.assertEqual("user", item.engine)
            self.assertEqual("", item.source_file)

    def test_validate_sources_rejects_placeholder_only_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            prepare_sources(manifest, sources)

            with self.assertRaisesRegex(ValueError, "仍是占位源码"):
                validate_sources(manifest, root)

    def test_validate_sources_accepts_filled_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "workspace" / "final" / "images" / "sources"
            manifest.write_text(MANIFEST_TEXT.strip(), encoding="utf-8")
            prepare_sources(manifest, sources)
            (sources / "image_2.dot").write_text("digraph G { A -> B }\n", encoding="utf-8")
            (sources / "image_3.puml").write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")
            (sources / "image_4.puml").write_text("@startuml\nstart\n:登录;\nstop\n@enduml\n", encoding="utf-8")

            validate_sources(manifest, root)

    def test_prepare_sources_writes_usecase_prompt_hint(self):
        manifest_text = """
images:
  - id: image_6
    title: 图3-1 系统用例图
    chapter: 第3章
    section: "3.2"
    source: ai
    diagram_type: usecase
    purpose: 展示系统核心角色和用例
    fact_source: background.md
    placement: 需求分析后展示
    status: pending
    description: 用例图需求
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(manifest_text.strip(), encoding="utf-8")

            prepare_sources(manifest, sources)
            source = (sources / "image_6.puml").read_text(encoding="utf-8")

            self.assertIn("请基于以下业务描述，生成一个符合软件工程论文规范的 PlantUML 用例图", source)
            self.assertIn("left to right direction", source)
            self.assertIn("skinparam shadowing false", source)
            self.assertIn("skinparam defaultFontName Microsoft YaHei", source)

    def test_prepare_sources_writes_one_puml_per_actor_usecase_item(self):
        manifest_text = """
images:
  - id: image_3_1
    placeholder_id: image_3
    title: 图4-3 系统用例图（普通用户）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示普通用户功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 普通用户用例图
    prompt_hint: 仅绘制普通用户相关用例。
  - id: image_3_2
    placeholder_id: image_3
    title: 图4-4 系统用例图（知识库管理员）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示知识库管理员功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 知识库管理员用例图
    prompt_hint: 仅绘制知识库管理员相关用例。
  - id: image_3_3
    placeholder_id: image_3
    title: 图4-5 系统用例图（系统管理员）
    chapter: 第4章
    section: "4.2"
    source: ai
    diagram_type: usecase
    purpose: 展示系统管理员功能边界
    fact_source: background.md
    placement: 图前说明，图后分析
    status: pending
    description: 系统管理员用例图
    prompt_hint: 仅绘制系统管理员相关用例。
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            sources = root / "sources"
            manifest.write_text(manifest_text.strip(), encoding="utf-8")

            prepare_sources(manifest, sources)

            self.assertTrue((sources / "image_3_1.puml").exists())
            self.assertTrue((sources / "image_3_2.puml").exists())
            self.assertTrue((sources / "image_3_3.puml").exists())
            source_1 = (sources / "image_3_1.puml").read_text(encoding="utf-8")
            source_2 = (sources / "image_3_2.puml").read_text(encoding="utf-8")
            source_3 = (sources / "image_3_3.puml").read_text(encoding="utf-8")
            self.assertIn("请基于以下业务描述，生成一个符合软件工程论文规范的 PlantUML 用例图", source_1)
            self.assertIn("图4-3 系统用例图（普通用户）", source_1)
            self.assertIn("仅绘制普通用户相关用例。", source_1)
            self.assertIn("图4-4 系统用例图（知识库管理员）", source_2)
            self.assertIn("仅绘制知识库管理员相关用例。", source_2)
            self.assertIn("图4-5 系统用例图（系统管理员）", source_3)
            self.assertIn("仅绘制系统管理员相关用例。", source_3)


if __name__ == "__main__":
    unittest.main()
