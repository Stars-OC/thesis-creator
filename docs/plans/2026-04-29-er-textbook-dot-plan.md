# ER 图教科书风格改造 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 thesis-creator 的 E-R 图默认输出改为基于 `background.md` 的教科书风格 DOT 图，并补齐业务说明、配置模板、文档与测试。

**Architecture:** 继续沿用现有 `scripts/chart_generator.py` 的 E-R 图生成主链路，不新增独立子模块。通过增强 `background.md` 解析、实体命中、字段中文化、DOT 布局与图下注释生成来完成改造，并同步更新配置模板、Step 8 文档、技能元数据与测试。

**Tech Stack:** Python 3、unittest、PyYAML、Graphviz DOT、Markdown 文档

---

### Task 1: 调整 ER 默认配置与技能元数据

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/references/templates/.thesis-config.yaml:36-53`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md:44-48`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/.openskills.json:1-66`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/docs/CHANGELOG.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`

**Step 1: Write the failing test**

在 `scripts/test_chart_generator_er_diagram.py` 新增测试，断言默认配置应为 `graph_type=dot`，并保留 `diagram_scope=single`。

```python
def test_default_er_modeling_config_should_use_dot_graph_type(self):
    config, _ = _load_er_modeling_config()
    assert config["graph_type"] == "dot"
    assert config["diagram_scope"] == "single"
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_default_er_modeling_config_should_use_dot_graph_type`
Expected: FAIL，因为默认值当前仍是 `chen`。

**Step 3: Write minimal implementation**

修改以下内容：

- `references/templates/.thesis-config.yaml`
  - 将 `er_modeling.graph_type` 默认值从 `chen` 改为 `dot`
  - 注释明确：默认输出教科书 DOT，可切换为 `erd` / `chen`
- `scripts/chart_generator.py`
  - `_load_er_modeling_config()` 的默认 `graph_type` 从 `chen` 改为 `dot`
- `SKILL.md`
  - 将 Step 8 的 ER 图口径改为“默认教科书 DOT，可在 `.thesis-config.yaml` 中切换”
- `.openskills.json`
  - 更新能力描述，使其体现“教科书风格 ER 图 / 配置化切换 / background.md 驱动”
- `docs/CHANGELOG.md`
  - 记录本次默认 ER 风格调整

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_default_er_modeling_config_should_use_dot_graph_type`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/references/templates/.thesis-config.yaml \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/.openskills.json \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/docs/CHANGELOG.md \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py

git commit -m "feat: default ER diagrams to textbook dot style"
```

### Task 2: 增强 background.md 表结构与业务语义解析

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py:67-293`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py:260-348`

**Step 1: Write the failing test**

新增测试，验证 `background.md` 中的表级业务说明、关联表和字段说明可以被解析到 `TableSchema`。

```python
def test_parse_table_schemas_should_capture_business_description(self):
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
    assert schema.business_description == "用于记录平台用户的注册、认证与状态信息。"
    assert schema.related_tables == ["角色表", "订单表"]
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_parse_table_schemas_should_capture_business_description`
Expected: FAIL，因为 `TableSchema` 当前没有 `business_description`。

**Step 3: Write minimal implementation**

在 `scripts/chart_generator.py` 中：

- 扩展 `TableSchema`：新增 `business_description: str = ""`
- 在 `_parse_table_schemas_from_background()` 中解析：
  - `业务说明：...`
  - `用途：...`
  - `说明：...`（表级说明，仅限非表格行）
- 保留字段级 `description`
- 保持兼容现有 `关联表：...` 解析逻辑

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_parse_table_schemas_should_capture_business_description`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py

git commit -m "feat: parse ER business context from background"
```

### Task 3: 优先按图名命中实体并统一字段中文化

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py:580-666,832-946`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`

**Step 1: Write the failing test**

新增两类测试：

1. 图名命中实体时，应优先使用 `background.md` 中的目标实体，而不是 description 的实体顺序。
2. 字段应优先输出中文，不裸露 `user_id`、`role_id`、`username` 这类技术名。

```python
def test_chart_name_should_prefer_schema_match_from_background(self):
    placeholder = ChartPlaceholder(... chart_name="角色概念ER图", description="1）实体：用户、角色；...")
    graph_code = generator.generate_mermaid(placeholder)
    assert 'label="角色"' in graph_code
    assert 'label="用户"' not in graph_code


def test_dot_fields_should_prefer_chinese_display_names(self):
    graph_code = generator.generate_mermaid(placeholder)
    assert 'label="用户编号"' in graph_code or 'label="编号"' in graph_code
    assert 'label="用户名"' in graph_code
    assert 'user_id' not in graph_code
    assert 'username' not in graph_code
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram -v`
Expected: 部分 FAIL，当前字段中文化与图名命中逻辑不够稳定。

**Step 3: Write minimal implementation**

在 `scripts/chart_generator.py` 中：

- 新增/增强辅助函数：
  - `_match_schema_from_chart_name()`：优先从 `chart_name` 命中实体
  - `_resolve_field_display_name()`：优先使用字段说明；英文技术名清洗后再兜底
  - `_is_mostly_chinese()`：辅助判断显示文本是否仍偏英文
- `_schema_to_attribute_names()` 改为优先输出中文语义名：
  - 主键优先 `字段说明`，无说明再退化为 `编号`
  - 外键优先 `字段说明`
  - 普通字段优先 `字段说明`，其次中文字段名，最后清洗英文名
- `_generate_er_diagram()` 中优先按图名命中 `background.md` 实体

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram -v`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py

git commit -m "feat: prefer background schema names for ER fields"
```

### Task 4: 强化 DOT 教科书布局与 warning 策略

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py:1029-1133`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_renderer_dot.py`

**Step 1: Write the failing test**

新增测试验证：

- 单实体 DOT 图保持“实体居中、字段上下环绕、关系直线”
- `single` 模式下即使 description 有多实体，也只绘制主实体
- 字段信息不足时仍能生成，但需要记录 warning

```python
def test_single_scope_dot_should_only_render_primary_entity(self):
    graph_code = generator.generate_mermaid(placeholder)
    assert 'entity [label="用户", shape=box];' in graph_code
    assert 'label="角色"' not in graph_code


def test_dot_should_keep_center_entity_and_wrapped_attributes(self):
    assert '{ rank=same; entity; }' in graph_code
    assert 'top_attr_1 -> entity;' in graph_code
    assert 'entity -> bottom_attr_1;' in graph_code
    assert 'splines=line;' in graph_code
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram scripts.test_chart_renderer_dot -v`
Expected: FAIL，当前 warning 策略未被测试覆盖，部分布局行为需要显式稳定。

**Step 3: Write minimal implementation**

在 `scripts/chart_generator.py` 中：

- `_build_graphviz_dot()` / `_build_graphviz_dot_multi()` 中统一：
  - `rankdir=TB`
  - `splines=line`
  - `edge [dir=none]`
  - 实体固定居中 rank
  - 上/下字段组使用 `rank=same`
- `strict_single_table=true` 时，`single` 模式只画主实体，关系通过图下注释体现
- 新增 warning 记录逻辑：
  - 字段说明缺失
  - 字段名仍为英文
  - 业务说明缺失
  - 主实体无法精确命中时的兜底生成
- 保持“尽量生成并 warning”，仅在 `background.md` 缺失或完全无表结构时阻断

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram scripts.test_chart_renderer_dot -v`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_renderer_dot.py

git commit -m "feat: enforce textbook dot ER layout"
```

### Task 5: 将图下注释升级为业务语义说明

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py:600-606,1208-1224`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py:289-346`

**Step 1: Write the failing test**

新增测试验证图下注释应同时包含：
- 实体业务职责
- 关键字段用途
- 与关联实体的业务关系

```python
def test_er_caption_should_include_business_role_field_usage_and_relations(self):
    replaced = generator.replace_placeholders(content, {"图4-3": graph_code})
    assert "用于记录" in replaced
    assert "支撑" in replaced
    assert "关联" in replaced or "存在关系" in replaced
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_er_caption_should_include_business_role_field_usage_and_relations`
Expected: FAIL，当前 `_build_er_caption()` 还是偏通用说明。

**Step 3: Write minimal implementation**

在 `scripts/chart_generator.py` 中：

- 重写 `_build_er_caption()`：
  - 句 1：实体职责（优先取 `business_description`）
  - 句 2：关键字段业务用途（优先取字段说明）
  - 句 3：与 `related_schemas` 的业务关系
- `replace_placeholders()` 保持原位替换逻辑，但 E-R 图说明改为调用新业务说明

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_er_caption_should_include_business_role_field_usage_and_relations`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py

git commit -m "feat: generate business-aware ER captions"
```

### Task 6: 更新 Step 8 文档并补齐验收说明

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_8_image.md:38-179`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md:57-67`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`

**Step 1: Write the failing test**

新增文档一致性测试或最小字符串断言测试，确保文档口径与实现一致：
- 默认 `dot`
- `background.md` 是唯一事实源
- 信息不足时尽量生成并 warning

```python
def test_step8_docs_should_describe_dot_as_default_er_mode(self):
    content = Path(".../workflows/step_8_image.md").read_text(encoding="utf-8")
    assert "默认" in content
    assert "dot" in content
    assert "background.md" in content
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_step8_docs_should_describe_dot_as_default_er_mode`
Expected: FAIL，如果文档仍保留旧口径。

**Step 3: Write minimal implementation**

修改 `workflows/step_8_image.md` 与 `SKILL.md`：

- 明确 `background.md` 是 ER 图唯一事实源
- 明确默认 `graph_type=dot`
- 明确“缺失时尽量生成并 warning”
- 明确教科书 DOT 风格要求：实体居中、字段环绕、字段中文
- 补充验收与烟测说明

**Step 4: Run test to verify it passes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram.ChartGeneratorERDiagramTestCase.test_step8_docs_should_describe_dot_as_default_er_mode`
Expected: PASS

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_8_image.md \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py

git commit -m "docs: align ER workflow with textbook dot defaults"
```

### Task 7: 运行完整回归并人工检查关键输出

**Files:**
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_renderer_dot.py`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_layout_config.py`

**Step 1: Run targeted test suite**

Run: `python -m unittest scripts.test_chart_generator_er_diagram scripts.test_chart_renderer_dot scripts.test_chart_layout_config -v`
Expected: PASS

**Step 2: Run smoke test for chart rendering if Graphviz is available**

Run: `python scripts/chart_renderer.py --input workspace/final/ER图_dot测试_由易到难.md --output workspace/final/images/ --method auto --update --report`
Expected: 生成 DOT PNG 与渲染报告；若本机缺少 Graphviz，记录为环境限制。

**Step 3: Manually inspect representative output**

人工检查至少 1 张 DOT ER 图，确认：
- 实体居中
- 字段上下环绕
- 字段标签为中文
- 图下注释包含业务描述

**Step 4: Verify docs and metadata changes**

Run: `python -m unittest scripts.test_chart_generator_er_diagram -v`
Expected: PASS；确认文档一致性测试通过。

**Step 5: Commit**

```bash
git add \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_renderer_dot.py \
  E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_layout_config.py

git commit -m "test: verify textbook dot ER workflow end to end"
```
