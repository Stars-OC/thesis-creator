# Step 8: 图片生成与渲染

> **状态管理(强制执行)**：
> 1. 启动前：`python scripts/core/status_manager.py thesis-workspace/ --ensure`
> 2. 启动时：`python scripts/core/status_manager.py thesis-workspace/ --check-step 8`
> 3. 前置条件通过后：`--update-step 8 --action start`
> 4. 完成后：`--update-step 8 --action complete`
>
> **统一入口(推荐)**：`python scripts/core/lifecycle.py --workspace thesis-workspace/ --step 8 --event start|complete`

> **整合流程：从正文抽取图片需求 → 生成/更新 `images.yaml` → 大模型填写 `.dot/.mmd/.puml` 源码 → 渲染 PNG → 回填 Markdown → 验证完整性 → 进入 Step 9 导出**

---

## 完整工作流

```mermaid
flowchart TD
    A[扫描正文中的 image 占位符和 image-requirement 块] --> B[生成 workspace/references/images.yaml]
    B --> C[创建 workspace/final/images/sources 源码文件]
    C --> D[大模型按 images.yaml 填写 dot/mmd/puml]
    D --> E[校验源码文件已填充]
    E --> F[按 engine 渲染 PNG]
    F --> G[将 [image_N] 替换为 Markdown 图片引用]
    G --> H[验证源码、PNG、占位符和用户待补图片]
    H --> I[✅ 图片生成完成]
    I --> J[进入 Step 9 导出]
```

---

## Step 4 到 Step 8 的衔接规则(硬约束)

- Step 4 正文只放 `[image_N]` 和 `image-requirement` 注释块，不在正文中写图表源码。
- Step 8 先运行 `manifest_builder.py`，把正文需求块转写到 `workspace/references/images.yaml`，并同步从正文中删除 `image-requirement` 参数块。
- 大模型只能基于 `images.yaml` 的 `purpose`、`fact_source`、`description`、`prompt_hint` 生成源码文件；正文中不得继续携带图片参数描述。
- 图表源码统一放在 `workspace/final/images/sources/`，后缀按引擎区分：
  - Mermaid：`.mmd`
  - Graphviz DOT：`.dot`
  - PlantUML：`.puml`
- 渲染后的 PNG 统一放在 `workspace/final/images/`。
- 最终正文不得残留已渲染 AI 图片的 `[image_N]`；用户待补截图可保留并在报告中列为 `user_required`。

---

## images.yaml 字段规范

每条图片记录至少包含：

```yaml
images:
  - id: image_1
    title: 图4-1 系统整体架构图
    chapter: 第4章
    section: "4.1"
    source: user
    diagram_type: architecture
    engine: user
    purpose: 展示系统整体分层与核心组件关系
    fact_source: 用户自行生成；如需 AI 生成请使用 GPT image
    placement: 图前说明架构目标，图后分析分层职责
    status: pending_user
    description: 系统架构图由用户自行生成后补入
    prompt_hint: 架构图不进入自动源码生成和渲染链路
    output_file: workspace/final/images/image_1.png
    render_status: pending_user
```

### engine 推断规则

| source / diagram_type | 默认 engine | 源码后缀 |
|---|---|---|
| `source=user` | `user` | 无源码 |
| `diagram_type=er/entity_er/overall_er/dot` | `graphviz` | `.dot` |
| `diagram_type=erd` 且 `.thesis-config.yaml` 中 `er_modeling.graph_type=erd` | `mermaid` | `.mmd` |
| `diagram_type=flowchart/flow/workflow/流程图/activity/usecase/sequence/class/plantuml` | `plantuml` | `.puml` |
| `diagram_type=architecture` | `user` | 无源码 |
| `diagram_type=module` | `mermaid` | `.mmd` |
| 其他 AI 图 | `mermaid` | `.mmd` |

---

## 系统设计章节双图策略(硬约束)

### ER 图生成口径(硬约束)

- ER 图类型由 `thesis-workspace/.thesis-config.yaml` 的 `er_modeling.graph_type` 决定；仅 ER 图读取该配置。
- 默认 `graph_type=dot`，输出 Graphviz DOT `.dot`，并采用教科书 Chen 风格：实体用矩形、属性用椭圆、联系用菱形，实体通过联系节点连接实体。
- `diagram_type=overall_er` 表示总体 ER 图，必须在数据库设计流程中第一个展示，并使用 DOT 实体-联系-实体结构。
- 总体 ER 图只展示实体、联系与 `1:1` / `1:N` 基数，不展示字段节点；关系菱形节点必须结合外键字段或实体语义命名，如“拥有”“包含”，不得统一写成“关联”。
- `diagram_type=entity_er` 表示单实体字段图；当 `graph_type=dot` 且 `dot_mode=textbook-single-entity-ring` 时，输出 Graphviz 单实体字段环绕图：实体居中、字段椭圆环绕、使用 `graph ER` 与 `layout=neato`，仅中心实体固定 `pos="0,0!"`，字段节点不写 `pos`，通过边 `len` 控制距离，不生成关系菱形；字段超过8个时边长只适度增加，在避免重叠的同时保持紧凑感。
- `dot_mode` 优先级：`images.yaml` 单图 `dot_mode` > `.thesis-config.yaml` 全局 `er_modeling.dot_mode` > 现有默认 DOT 逻辑。
- `graph_type=erd` 时输出 Mermaid `erDiagram` `.mmd`；`graph_type=chen` 当前按 DOT Chen 风格处理。
- 事实源：优先读取 `thesis-workspace/references/prompt/background.md`。
- DOT 输出约束：不要显式生成 `label=` 属性，直接使用节点文本。
- 图名、表名、字段节点和联系节点会使用 DOT 安全引用，以支持图号、空格、括号等常见论文写法。
- `source_writer.py` 会优先从 `background.md` 生成真实 ER 源码，不再为 ER 图生成占位源码；中文字段名只读取表结构中的 `显示名`/`中文名`/`字段中文名` 等大模型语义列，不从 `说明` 列脚本化截断或翻译。
- 信息不足时：尽量生成最小 DOT 并 warning，不因字段说明缺失直接阻断。

| 图表 | 来源 | 推荐 engine | 占位符标记 |
|------|------|-------------|------------|
| 总体 ER 图 | AI 生成 | `graphviz` | `[image_N]`，数据库设计流程第一个展示 |
| 单实体字段 ER 图（`entity_er`） | AI 生成 | `graphviz` | `[image_N]`，可启用 `textbook-single-entity-ring` |
| 系统整体架构图 | 用户自行生成；如需 AI 生成请使用 GPT image 生图后补入 | `user` | `[image_N]` |
| 系统功能模块图 | 用户手动提供 | `user` | `[image_N]` |
| 各模块业务流程图 | AI 生成 | `plantuml` | `[image_N]` |
| 实体 E-R 图 | AI 生成 | `graphviz` | `[image_N]` |
| 用例图/时序图/类图/活动图 | AI 生成 | `plantuml` | `[image_N]` |

### PlantUML 流程图固定提示词(硬约束)

- 仅当 `engine=plantuml` 且当前图片属于流程图/活动图表达时使用。
- 主题优先取 `images.yaml` 中的 `title`；若标题过长，可改用 `purpose` 的简化表述。
- 生成 `.puml` 源码前，必须附加以下固定提示词模板：

```text
请生成一个用于毕业论文的PlantUML流程图，主题为“{{图表主题}}”。要求：

- 使用activity diagram
- 所有节点使用中文
- 起止节点使用“开始”“结束”
- 逻辑严谨，体现完整业务流或上下文流转机制
- 包含必要循环（如存在用户持续操作、重试或追问）
- 避免语法歧义（防止被解析为class diagram）
- 图结构简洁，不超过3层嵌套
- 判断分支连线必须明确标注 Y/N
- 全图只保留一个最终结束节点，所有分支和普通路径最终汇入该结束节点
- 适合论文插图展示

只输出PlantUML代码。
```

### PlantUML 用例图固定提示词(硬约束)

- 用例图布局由 `thesis-workspace/.thesis-config.yaml` 的 `usecase_modeling.layout` 控制。
- `usecase_modeling.layout=overall`：生成一张总体用例图。
- `usecase_modeling.layout=per_actor`：一个角色一张图；`manifest_builder.py` 会把单个 `[image_N]` 展开为多条 manifest，并在回填时按同一个占位符插入多张图片。
- 当 `diagram_type=usecase` 时，生成 `.puml` 源码前必须附加以下固定提示词：

```text
请基于以下业务描述，生成一个符合软件工程论文规范的 PlantUML 用例图（Use Case Diagram）。

要求：

1. 使用标准 UML 用例图规范
2. 风格偏学术化、简洁、黑白
3. 不使用彩色、渐变、阴影
4. actor 使用中文
5. 系统边界使用 rectangle 包裹
6. 用例名称简洁，避免长句
7. 控制整体节点数量，保持论文可读性
8. 避免复杂交叉线
9. 使用 left to right direction 布局
10. 输出完整可运行的 PlantUML 代码
11. 使用如下 skinparam 风格：

skinparam shadowing false
skinparam packageStyle rectangle
skinparam usecase {
    BackgroundColor white
    BorderColor black
}
skinparam defaultFontName Microsoft YaHei

12. 若功能较多，仅保留核心业务用例
13. include / extend 仅在确实存在复用关系时使用
14. 图的整体风格应接近高校计算机专业毕业论文中的 UML 用例图
```

- 架构图不走 Mermaid 自动生成；必须由用户自行生成，若需要 AI 生成则使用 GPT image 生图后作为 `source=user` 图片补入。
- 模块图等 Mermaid 非流程型结构图不附加这段 PlantUML 提示词。
- 普通业务流程图、活动流程图统一优先使用 PlantUML，而不是 Mermaid。
- 若图题为“历史会话管理流程”等多轮交互主题，应在流程中显式体现上下文读取、历史检索、上下文合并、回答生成与持续追问循环。
- **当用户要求“生成流程图”“测试流程图”或单独生成某张图时，默认先将源码写入 `thesis-workspace/workspace/final/images/sources/` 下对应 `.puml/.dot/.mmd` 文件，再按需渲染；除非用户明确要求“只输出代码”，否则不要把完整图表源码直接打印到控制台。**

## 系统实现章节(第5章)图片策略(硬约束)

| 图表 | 来源 | engine | 占位符标记 |
|------|------|--------|-----------|
| 各功能界面截图 | 用户手动提供 | `user` | `[image_N]` |
| 系统运行效果图 | 用户手动提供 | `user` | `[image_N]` |
| 接口调用时序图 | AI 生成 | `plantuml` | `[image_N]` |

> **写作组合(硬约束)**：文字描述 + 用户提供系统截图 + 核心代码实现。第5章功能界面截图由用户提供系统实际运行截图，AI 不自动伪造截图。

---

## 执行命令

```bash
# Step 1: 从正文占位符和 image-requirement 块生成 images.yaml，并同步清除正文参数块
python scripts/charts/manifest_builder.py --input workspace/final/论文终稿.md --output workspace/references/images.yaml

# Step 2: 根据 images.yaml 创建 .dot/.mmd/.puml 源码文件占位
python scripts/charts/source_writer.py --manifest workspace/references/images.yaml --sources-dir workspace/final/images/sources

# Step 3: 大模型逐条读取 images.yaml，并填写 workspace/final/images/sources/ 下的源码文件
# - Mermaid: image_N.mmd
# - Graphviz DOT: image_N.dot
# - PlantUML: image_N.puml

# Step 4: 校验源码文件已经由大模型填充，不再是占位内容
python scripts/charts/source_writer.py --manifest workspace/references/images.yaml --validate

# Step 5: 按 engine 渲染 PNG
python scripts/charts/render.py --manifest workspace/references/images.yaml --method auto --report

# Step 6: 回填 Markdown 图片引用
python scripts/charts/markdown_updater.py --input workspace/final/论文终稿.md --manifest workspace/references/images.yaml --in-place

# Step 7: 完整性验证
python scripts/charts/validate.py --input workspace/final/论文终稿.md --manifest workspace/references/images.yaml --images-dir workspace/final/images
```

---

## 渲染方法选项

| 方法 | 说明 | 依赖 |
|------|------|------|
| `graphviz` | DOT 本地渲染 | `pip install graphviz` + 本机安装 Graphviz `dot` |
| `mmdc` | Mermaid CLI 本地渲染 | `npm install -g @mermaid-js/mermaid-cli` |
| `playwright` | Mermaid 浏览器渲染 | `pip install playwright && playwright install` |
| `plantuml` | PlantUML 本地渲染 | 安装 PlantUML 命令行与 Java 环境 |
| `kroki` | PlantUML 先尝试 Kroki，失败后再尝试 PlantUML 官方服务器；Mermaid 仍走 Kroki | 需要网络 |
| `official_server` | 仅 PlantUML 官方服务器渲染 | 需要网络 |
| `auto` | PlantUML 按“本地 PlantUML → Kroki → PlantUML 官方服务器”自动选择；Mermaid 自动选择本地或 Kroki；DOT 仍走 Graphviz | 已安装的优先 |

---

## 图片生成完整性验证(硬约束)

| 检查项 | 要求 | 不达标处理 |
|--------|------|-----------|
| 清单完整 | 正文每个 `[image_N]` 都有 images.yaml 记录 | 补充 `image-requirement` 后重新生成清单 |
| 源码存在 | AI 图片必须有 `.dot/.mmd/.puml` 源码文件 | 补充大模型源码 |
| 源码非占位 | 源码文件不得仍是 `CHART_SOURCE_PLACEHOLDER` | 用正式图表源码替换 |
| 图片文件存在 | 已渲染 AI 图片必须有 PNG | 重新渲染 |
| 图片非空 | 每个 PNG 文件 > 1KB | 重新渲染 |
| 占位符回填 | 已渲染 AI 图片不得残留 `[image_N]` | 执行 `markdown_updater.py` |
| 用户图片 | `source=user` 可保留为待补，但必须列入报告 | 提示用户补充真实截图 |

---

## 输出文件

- `workspace/references/images.yaml` - 图片需求清单
- `workspace/final/images/sources/image_N.mmd` - Mermaid 源码
- `workspace/final/images/sources/image_N.dot` - Graphviz DOT 源码
- `workspace/final/images/sources/image_N.puml` - PlantUML 源码
- `workspace/final/images/image_N.png` - 渲染后的图片
- `workspace/final/images/render_report.md` - 图表渲染报告

---

## Step 8 中 ER 图的推荐口径

- `graphviz`：ER 图默认模式，读取 `background.md` 并启发式生成基础 Graphviz DOT；图名、表名、字段节点使用 DOT 安全引用，信息不足时尽量生成并 warning。
- `mermaid`：用于模块图等非流程型结构图；系统架构图固定按 `source=user` 处理，不进入 Mermaid 自动生成链路。
- `plantuml`：用于流程图、用例图、时序图、类图和活动图，更符合 UML 表达规范。
