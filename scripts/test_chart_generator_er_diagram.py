# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from chart_generator import ChartGenerator, ChartPlaceholder, _load_er_modeling_config  # noqa: E402


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class ChartGeneratorERDiagramTestCase(unittest.TestCase):
    def setUp(self):
        self._original_cwd = Path.cwd()
        os.chdir(Path(__file__).parent)

    def tearDown(self):
        os.chdir(self._original_cwd)

    def _build_generator(self, **kwargs):
        if "er_modeling_config" not in kwargs and "input_path" not in kwargs and "config_path" not in kwargs:
            kwargs["er_modeling_config"] = {"graph_type": "chen", "diagram_scope": "single"}
        generator = ChartGenerator(output_dir=str(Path(__file__).parent / "test_output"), **kwargs)
        generator.logger = DummyLogger()
        return generator

    def test_default_er_modeling_config_should_use_dot_graph_type(self):
        with patch("chart_generator.resolve_config_candidates", return_value=[]):
            config, _ = _load_er_modeling_config()

        self.assertEqual("dot", config["graph_type"])
        self.assertEqual("single", config["diagram_scope"])

    def test_generate_single_table_er_diagram_from_structured_description(self):
        generator = self._build_generator()

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-8",
            chart_name="用户概念ER图",
            description="""
图表编号：图4-8
图表名称：用户概念ER图
图表类型：概念ER图
内容描述：
1）实体：用户、角色；
2）用户属性：PK_user_id、用户名、手机号、注册时间、状态；
3）角色属性：PK_role_id、角色名、权限级别；
4）联系：用户-拥有-角色（多对一）；
5）外键：用户实体包含 FK_role_id 指向角色实体主键。
绘图要求：数据库表ER图，线是直线，一个表只有一个图。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("flowchart LR", mermaid)
        self.assertIn("[用户]", mermaid)
        self.assertIn("((编号))", mermaid)
        self.assertIn("((用户名))", mermaid)
        self.assertIn("A1 --- E1", mermaid)
        self.assertIn("E1 --- A", mermaid)
        self.assertNotIn("[角色]", mermaid)
        self.assertNotIn("---|拥有|", mermaid)
        self.assertNotIn("erDiagram", mermaid)
        self.assertNotIn("((PK_", mermaid)
        self.assertNotIn("((FK_", mermaid)

    def test_er_diagram_should_wrap_single_entity_with_top_and_bottom_attributes(self):
        generator = self._build_generator()

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-9",
            chart_name="知识库概念ER图",
            description="""
图表编号：图4-9
图表名称：知识库概念ER图
图表类型：概念ER图
内容描述：
1）实体：知识库、文档；
2）知识库属性：编号、名称、状态、创建时间；
3）文档属性：编号、标题、类型、更新时间；
4）联系：知识库-拥有-文档（一对多）。
绘图要求：数据库表ER图，线是直线，一个表只有一个图，上下椭圆字段包裹实体。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("[知识库]", mermaid)
        self.assertIn("A1((编号))", mermaid)
        self.assertIn("A2((名称))", mermaid)
        self.assertIn("A1 --- E1", mermaid)
        self.assertIn("E1 --- A3", mermaid)
        self.assertNotIn("[文档]", mermaid)
        self.assertNotIn("---|拥有|", mermaid)

    def test_detect_conceptual_er_keywords_as_er_diagram(self):
        generator = self._build_generator()

        detected = generator._detect_chart_type(
            "用户概念ER图",
            "图表类型：概念 ER 图，实体用矩形、属性用椭圆、联系用菱形",
        )

        self.assertEqual("E-R图", detected)

    def test_generate_mermaid_erd_when_config_graph_type_erd(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "erd"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-10",
            chart_name="用户概念ER图",
            description="""
内容描述：
1）实体：用户；
2）用户属性：PK_user_id、用户名、手机号、注册时间、状态。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("erDiagram", mermaid)
        self.assertIn("用户", mermaid)
        self.assertNotIn("flowchart LR", mermaid)

    def test_generate_graphviz_dot_when_config_graph_type_dot(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "dot"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-11",
            chart_name="订单概念ER图",
            description="""
内容描述：
1）实体：订单；
2）订单属性：PK_order_id、订单号、订单状态、创建时间。
""",
        )

        graph_code = generator.generate_mermaid(placeholder)

        self.assertIn("```dot", graph_code)
        self.assertIn("digraph ER", graph_code)
        self.assertIn("订单", graph_code)
        self.assertIn('"订单" [shape=box];', graph_code)
        self.assertIn('rankdir=TB;', graph_code)
        self.assertIn('edge [dir=none];', graph_code)
        self.assertIn('"编号', graph_code)
        self.assertIn('"订单状态', graph_code)
        self.assertIn('{ rank=same;', graph_code)
        self.assertIn('-> "订单";', graph_code)

    def test_generate_multi_entity_chen_diagram_when_scope_is_multi(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "chen", "diagram_scope": "multi"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-12",
            chart_name="用户角色概念ER图",
            description="""
内容描述：
1）实体：用户、角色；
2）用户属性：PK_user_id、用户名、状态；
3）角色属性：PK_role_id、角色名、权限级别；
4）联系：用户-拥有-角色（多对一）。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("flowchart LR", mermaid)
        self.assertIn("[用户]", mermaid)
        self.assertIn("[角色]", mermaid)
        self.assertIn("---|拥有|", mermaid)

    def test_generate_multi_entity_erd_when_scope_is_multi(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "erd", "diagram_scope": "multi"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-13",
            chart_name="用户角色工程ERD",
            description="""
内容描述：
1）实体：用户、角色；
2）用户属性：PK_user_id、用户名、状态；
3）角色属性：PK_role_id、角色名、权限级别；
4）联系：用户-拥有-角色（多对一）。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("erDiagram", mermaid)
        self.assertIn("用户 {", mermaid)
        self.assertIn("角色 {", mermaid)
        self.assertIn("用户", mermaid)
        self.assertIn("角色", mermaid)

    def test_generate_multi_entity_dot_when_scope_is_multi(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "dot", "diagram_scope": "multi"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-17",
            chart_name="订单商品概念ER图",
            description="""
内容描述：
1）实体：订单、商品；
2）订单属性：PK_order_id、订单号、状态；
3）商品属性：PK_product_id、商品名、单价；
4）联系：订单-包含-商品（多对多）。
""",
        )

        graph_code = generator.generate_mermaid(placeholder)

        self.assertIn("```dot", graph_code)
        self.assertIn('"订单" [shape=box];', graph_code)
        self.assertIn('"商品"', graph_code)
        self.assertIn('[shape=diamond];', graph_code)

    def test_chart_name_entity_should_override_description_order_when_it_matches_known_entity(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "chen", "diagram_scope": "single"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-18",
            chart_name="角色概念ER图",
            description="""
内容描述：
1）实体：用户、角色；
2）用户属性：PK_user_id、用户名、状态；
3）角色属性：PK_role_id、角色名、权限级别；
4）联系：用户-拥有-角色（多对一）。
""",
        )

        mermaid = generator.generate_mermaid(placeholder)

        self.assertIn("[角色]", mermaid)
        self.assertNotIn("[用户]", mermaid)

    def test_parse_table_schemas_from_background(self):
        generator = self._build_generator()
        text = """
## 数据库表设计

### 用户表结构
关联表：角色表
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户编号 |
| username | varchar | 50 | 否 | 否 | 用户名 |
| role_id | bigint | 20 | 否 | 否 | 角色外键 |

### 角色表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| role_id | bigint | 20 | 否 | 是 | 角色编号 |
| role_name | varchar | 50 | 否 | 否 | 角色名称 |
"""

        schemas = generator._parse_table_schemas_from_background(text)

        self.assertIn(generator._normalize_table_key("用户"), schemas)
        self.assertIn(generator._normalize_table_key("角色"), schemas)
        self.assertEqual("用户", schemas[generator._normalize_table_key("用户")].display_name)
        self.assertEqual(3, len(schemas[generator._normalize_table_key("用户")].fields))
        self.assertTrue(schemas[generator._normalize_table_key("用户")].fields[0].is_primary)
        self.assertEqual(["角色表"], schemas[generator._normalize_table_key("用户")].related_tables)

    def test_parse_table_schemas_should_capture_business_description(self):
        generator = self._build_generator()
        text = """
## 数据库表设计

### 用户表结构
业务说明：用于记录平台用户的注册、认证与状态信息。
关联表：角色表、订单表
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户编号 |
| username | varchar | 50 | 否 | 否 | 用户名 |
"""

        schemas = generator._parse_table_schemas_from_background(text)
        schema = schemas[generator._normalize_table_key("用户")]

        self.assertEqual("用于记录平台用户的注册、认证与状态信息。", schema.business_description)
        self.assertEqual(["角色表", "订单表"], schema.related_tables)

    def test_generate_er_from_table_schema_and_add_caption(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "thesis-workspace"
            prompt_dir = workspace / "references" / "prompt"
            prompt_dir.mkdir(parents=True)
            (workspace / ".thesis-config.yaml").write_text(
                "er_modeling:\n  graph_type: dot\n  diagram_scope: single\n",
                encoding="utf-8",
            )
            (prompt_dir / "background.md").write_text(
                """
## 数据库表设计

### 用户表结构
关联表：角色表
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户编号 |
| username | varchar | 50 | 否 | 否 | 用户名 |
| status | tinyint | 1 | 否 | 否 | 状态 |
| role_id | bigint | 20 | 否 | 否 | 角色外键 |

### 角色表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| role_id | bigint | 20 | 否 | 是 | 角色编号 |
| role_name | varchar | 50 | 否 | 否 | 角色名称 |
""",
                encoding="utf-8",
            )
            input_file = workspace / "workspace" / "final" / "论文终稿.md"
            input_file.parent.mkdir(parents=True)
            input_file.write_text(
                "<!-- 图表占位符：图4-3 用户概念ER图 -->\n> **[图表占位符]**\n> 展示用户表结构\n<!-- 图表占位符结束 -->",
                encoding="utf-8",
            )

            generator = self._build_generator(input_path=str(input_file))
            placeholder = ChartPlaceholder(
                raw_text="",
                chart_type="E-R图",
                chart_id="图4-3",
                chart_name="用户概念ER图",
                description="展示用户表结构",
            )
            graph_code = generator.generate_mermaid(placeholder)
            generator.charts = [placeholder]
            replaced = generator.replace_placeholders(input_file.read_text(encoding="utf-8"), {"图4-3": graph_code})

        self.assertIn("```dot", graph_code)
        self.assertIn('"用户" [shape=box];', graph_code)
        self.assertIn('用户名', graph_code)
        self.assertIn('状态', graph_code)
        self.assertNotIn('角色名称', graph_code)
        self.assertIn('图4-3说明：', replaced)
        self.assertIn('用户表', replaced)
        self.assertIn('角色', replaced)

    def test_er_caption_should_include_business_role_field_usage_and_relations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "thesis-workspace"
            prompt_dir = workspace / "references" / "prompt"
            prompt_dir.mkdir(parents=True)
            (workspace / ".thesis-config.yaml").write_text(
                "er_modeling:\n  graph_type: dot\n  diagram_scope: single\n",
                encoding="utf-8",
            )
            (prompt_dir / "background.md").write_text(
                """
## 数据库表设计

### 用户表结构
业务说明：用于记录平台用户的注册、认证与状态信息。
关联表：角色表、订单表
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户唯一标识 |
| username | varchar | 50 | 否 | 否 | 用户登录名 |
| status | tinyint | 1 | 否 | 否 | 账号状态 |

### 角色表结构
业务说明：用于定义平台角色及其权限边界。
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| role_id | bigint | 20 | 否 | 是 | 角色唯一标识 |
| role_name | varchar | 50 | 否 | 否 | 角色名称 |
""",
                encoding="utf-8",
            )
            input_file = workspace / "workspace" / "final" / "论文终稿.md"
            input_file.parent.mkdir(parents=True)
            input_file.write_text(
                "<!-- 图表占位符：图4-23 用户概念ER图 -->\n> **[图表占位符]**\n> 展示用户表结构\n<!-- 图表占位符结束 -->",
                encoding="utf-8",
            )

            generator = self._build_generator(input_path=str(input_file))
            placeholder = ChartPlaceholder(
                raw_text="",
                chart_type="E-R图",
                chart_id="图4-23",
                chart_name="用户概念ER图",
                description="展示用户表结构",
            )
            graph_code = generator.generate_mermaid(placeholder)
            generator.charts = [placeholder]
            replaced = generator.replace_placeholders(input_file.read_text(encoding="utf-8"), {"图4-23": graph_code})

        self.assertIn("用于记录平台用户的注册、认证与状态信息", replaced)
        self.assertIn("用户唯一标识", replaced)
        self.assertIn("用户登录名", replaced)
        self.assertTrue("角色表" in replaced or "角色" in replaced)

    def test_chart_name_should_prefer_schema_match_from_background(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "thesis-workspace"
            prompt_dir = workspace / "references" / "prompt"
            prompt_dir.mkdir(parents=True)
            (workspace / ".thesis-config.yaml").write_text(
                "er_modeling:\n  graph_type: dot\n  diagram_scope: single\n",
                encoding="utf-8",
            )
            (prompt_dir / "background.md").write_text(
                """
## 数据库表设计

### 用户表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户编号 |
| username | varchar | 50 | 否 | 否 | 用户名 |

### 角色表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| role_id | bigint | 20 | 否 | 是 | 角色编号 |
| role_name | varchar | 50 | 否 | 否 | 角色名称 |
""",
                encoding="utf-8",
            )
            input_file = workspace / "workspace" / "final" / "论文终稿.md"
            input_file.parent.mkdir(parents=True)
            input_file.write_text("占位符", encoding="utf-8")

            generator = self._build_generator(input_path=str(input_file))
            placeholder = ChartPlaceholder(
                raw_text="",
                chart_type="E-R图",
                chart_id="图4-19",
                chart_name="角色概念ER图",
                description="""
内容描述：
1）实体：用户、角色；
2）用户属性：PK_user_id、用户名、状态；
3）角色属性：PK_role_id、角色名、权限级别；
""",
            )

            graph_code = generator.generate_mermaid(placeholder)

        self.assertIn('"角色" [shape=box];', graph_code)
        self.assertNotIn('"用户" [shape=box];', graph_code)

    def test_dot_fields_should_prefer_business_descriptions_over_generic_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "thesis-workspace"
            prompt_dir = workspace / "references" / "prompt"
            prompt_dir.mkdir(parents=True)
            (workspace / ".thesis-config.yaml").write_text(
                "er_modeling:\n  graph_type: dot\n  diagram_scope: single\n",
                encoding="utf-8",
            )
            (prompt_dir / "background.md").write_text(
                """
## 数据库表设计

### 用户表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | 用户唯一标识 |
| username | varchar | 50 | 否 | 否 | 用户登录名 |
| created_at | datetime | 0 | 否 | 否 | 账号创建时间 |
""",
                encoding="utf-8",
            )
            input_file = workspace / "workspace" / "final" / "论文终稿.md"
            input_file.parent.mkdir(parents=True)
            input_file.write_text("占位符", encoding="utf-8")

            generator = self._build_generator(input_path=str(input_file))
            placeholder = ChartPlaceholder(
                raw_text="",
                chart_type="E-R图",
                chart_id="图4-20",
                chart_name="用户概念ER图",
                description="展示用户表结构",
            )

            graph_code = generator.generate_mermaid(placeholder)

        self.assertIn('用户唯一标识', graph_code)
        self.assertIn('用户登录名', graph_code)
        self.assertIn('账号创建时间', graph_code)
        self.assertNotIn('label="编号"', graph_code)
        self.assertNotIn('label="用户名"', graph_code)
        self.assertNotIn('label="创建时间"', graph_code)

    def test_dot_multi_should_keep_textbook_tb_layout(self):
        generator = self._build_generator(er_modeling_config={"graph_type": "dot", "diagram_scope": "multi"})

        placeholder = ChartPlaceholder(
            raw_text="",
            chart_type="E-R图",
            chart_id="图4-21",
            chart_name="订单商品概念ER图",
            description="""
内容描述：
1）实体：订单、商品；
2）订单属性：PK_order_id、订单号、状态；
3）商品属性：PK_product_id、商品名、单价；
4）联系：订单-包含-商品（多对多）。
""",
        )

        graph_code = generator.generate_mermaid(placeholder)

        self.assertIn("rankdir=TB;", graph_code)
        self.assertIn("splines=line;", graph_code)
        self.assertIn("edge [dir=none];", graph_code)
        self.assertIn('{ rank=same;', graph_code)

    def test_dot_should_warn_when_business_context_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "thesis-workspace"
            prompt_dir = workspace / "references" / "prompt"
            prompt_dir.mkdir(parents=True)
            (workspace / ".thesis-config.yaml").write_text(
                "er_modeling:\n  graph_type: dot\n  diagram_scope: single\n",
                encoding="utf-8",
            )
            (prompt_dir / "background.md").write_text(
                """
## 数据库表设计

### 用户表结构
| 字段名 | 类型 | 长度 | 允许空 | 主键 | 说明 |
|--------|------|------|--------|------|------|
| user_id | bigint | 20 | 否 | 是 | |
| username | varchar | 50 | 否 | 否 | |
""",
                encoding="utf-8",
            )
            input_file = workspace / "workspace" / "final" / "论文终稿.md"
            input_file.parent.mkdir(parents=True)
            input_file.write_text("占位符", encoding="utf-8")

            generator = self._build_generator(input_path=str(input_file))
            placeholder = ChartPlaceholder(
                raw_text="",
                chart_type="E-R图",
                chart_id="图4-22",
                chart_name="用户概念ER图",
                description="展示用户表结构",
            )

            graph_code = generator.generate_mermaid(placeholder)
            context = generator.last_er_context["图4-22"]


    def test_step8_docs_should_describe_dot_as_default_er_mode(self):
        content = Path(
            "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_8_image.md"
        ).read_text(encoding="utf-8")

        self.assertIn("默认", content)
        self.assertIn("graph_type=dot", content)
        self.assertIn("background.md", content)
        self.assertIn("尽量生成并 warning", content)
        self.assertIn("实体居中", content)
        self.assertIn("字段中文", content)
