# thesis-creator ER 图可选模式设计

## 背景

现有 thesis-creator 已支持 ER 图默认使用 Graphviz DOT，并以教科书 Chen 风格为主，但当前规则主要面向“总体 ER 图”，即多实体、联系菱形、基数展示、不展示字段。

新增需求是支持一个**可选的单实体字段级 ER 图模式**，用于生成教科书风格的单表结构图。该模式要求：

- 使用 `graph ER`
- 使用 `layout=neato`
- 使用 `pos` 精确坐标
- 禁止 `rank`
- 单实体居中
- 属性椭圆环绕分布
- 不使用 `label=`
- 单图输出

该模式不替换现有默认 ER 逻辑，而是作为可选模式新增。

## 设计目标

1. 保留现有 `overall_er` 总体 ER 图链路不变。
2. 新增一个专用于单实体字段环绕布局的 DOT 模式。
3. 支持全局配置和单图覆盖两种触发方式。
4. 先以文档 + prompt 模板 + `source_writer.py` 轻量联动实现，不扩大到 `manifest_builder.py`。
5. 新模式失效时安全回退到现有默认 DOT 逻辑。

## 模式定义

新增 DOT 子模式：

- `er_modeling.graph_type=dot`
- `er_modeling.dot_mode=textbook-single-entity-ring`

其中：

- `graph_type` 继续决定 ER 图采用 DOT 还是 Mermaid。
- `dot_mode` 只在 `graph_type=dot` 时生效。
- `textbook-single-entity-ring` 仅用于单实体 ER 图。

## 触发入口与优先级

支持两层触发：

1. 全局默认：`.thesis-config.yaml`
2. 单图覆盖：`images.yaml` 某条记录

优先级：

`images.yaml 单图配置 > .thesis-config.yaml 全局配置 > 现有默认规则`

推荐配置示例：

```yaml
er_modeling:
  graph_type: dot
  dot_mode: textbook-single-entity-ring
```

单图覆盖示例：

```yaml
images:
  - id: image_3
    diagram_type: entity_er
    engine: graphviz
    dot_mode: textbook-single-entity-ring
```

## ER 模式职责边界

为避免混淆，将 ER 图拆分为 3 类：

| 类型 | 用途 | 展示内容 | 关系菱形 | 字段属性 | 引擎 |
|---|---|---|---|---|---|
| `overall_er` | 数据库总体结构图 | 多实体、联系、`1:1 / 1:N` 基数 | 有 | 无 | Graphviz DOT |
| `entity_er` | 单实体结构图 | 1 个实体 + 字段属性 | 无 | 有 | Graphviz DOT |
| `erd` | Mermaid ERD 表达 | Mermaid 标准语法 | 按语法 | 按语法 | Mermaid |

其中 `textbook-single-entity-ring` 只作用在 `entity_er` 上，不作用于 `overall_er`。

## 文件改动设计

### 需要修改的文件

1. `SKILL.md`
   - 补充 `dot_mode=textbook-single-entity-ring` 说明
   - 明确其仅用于 `entity_er`

2. `workflows/step_8_image.md`
   - 新增该模式的触发条件
   - 新增输出限制
   - 新增优先级说明
   - 明确与 `overall_er` 的边界

3. `prompts/er_textbook_single_entity_dot.md`
   - 新增独立 prompt 模板文件
   - 内容采用固定 DOT 约束模板，支持实体名/字段名注入

4. `scripts/charts/source_writer.py`
   - 识别 `.thesis-config.yaml` 与 `images.yaml` 中的 `dot_mode`
   - 在 `graph_type=dot` 且 `diagram_type=entity_er` 时，命中该模式则使用专用 prompt
   - 未命中时回退到现有默认 DOT 逻辑

5. `.openskills.json`
   - 如有必要更新版本或能力描述

## 为什么先不改 manifest_builder.py

第一阶段只改 `source_writer.py`，原因如下：

- 改动面更小，风险更低
- 先保证模式可被稳定触发
- 避免把正文需求抽取与 DOT 模式识别绑得过早过深

后续若需要从正文 `image-requirement` 自动抽取 `dot_mode`，再单独扩展 `manifest_builder.py`。

## Prompt 模板设计

建议新增独立模板文件：

- `prompts/er_textbook_single_entity_dot.md`

模板职责：

- 固化 `graph ER`、`layout=neato`、`overlap=false`、`splines=true`
- 要求使用 `pos` 精确布局
- 要求实体居中、属性环绕、视觉对称
- 要求属性直接连实体
- 禁止属性互连、禁止关系菱形、禁止 `label=`、禁止 `rank`
- 只输出 DOT 代码

该模板作为 `source_writer.py` 命中模式后的专用提示词来源。

## 验证设计

### 验证层级

1. 文档层
   - 检查 `SKILL.md`、`step_8_image.md`、prompt 文件内容一致

2. 配置层
   - 使用最小 `.thesis-config.yaml` + 最小 `images.yaml` 验证模式解析

3. 脚本层
   - 运行 `source_writer.py` 的最小样例
   - 确认命中 `textbook-single-entity-ring` 时切换到专用 prompt

### 关键测试场景

1. 全局配置触发
   - 全局 `graph_type=dot`
   - 全局 `dot_mode=textbook-single-entity-ring`
   - 单图不写 `dot_mode`

2. 单图覆盖触发
   - 全局使用普通 dot
   - 某张 `entity_er` 单图写 `dot_mode=textbook-single-entity-ring`

3. 总体 ER 不误触发
   - `diagram_type=overall_er`
   - 即使全局存在 `dot_mode=textbook-single-entity-ring`
   - 仍必须走总体 ER 逻辑

## 回退策略

| 情况 | 回退行为 |
|---|---|
| `diagram_type=entity_er` 但字段不全 | 尽量生成最小单实体环绕图，并 warning |
| `diagram_type=overall_er` | 忽略 `textbook-single-entity-ring` |
| `graph_type != dot` | 不启用该模式 |
| `dot_mode` 未识别 | 回退到现有默认 DOT ER 逻辑 |

## 推荐实施顺序

1. 更新 `SKILL.md`
2. 更新 `workflows/step_8_image.md`
3. 新增 `prompts/er_textbook_single_entity_dot.md`
4. 修改 `scripts/charts/source_writer.py`
5. 进行最小验证
6. 视需要再决定是否补 `manifest_builder.py`

## 结论

推荐方案为：

- 新增可选模式 `textbook-single-entity-ring`
- 仅作用于 `entity_er`
- 支持全局配置 + 单图覆盖
- 优先级为单图覆盖全局
- 通过文档、独立 prompt 模板与 `source_writer.py` 轻量联动落地
- 第一阶段不修改 `manifest_builder.py`
- 验证重点是“总体 ER 不误触发”
