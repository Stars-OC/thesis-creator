# Step 8: 图片生成与渲染

> **状态管理(强制执行)**：
> 1. 启动前：`python scripts/status_manager.py thesis-workspace/ --ensure`
> 2. 启动时：`python scripts/status_manager.py thesis-workspace/ --check-step 8`
> 3. 前置条件通过后：`--update-step 8 --action start`
> 4. 完成后：`--update-step 8 --action complete`
>
> **统一入口(推荐)**：`python scripts/lifecycle.py --workspace thesis-workspace/ --step 8 --event start|complete`

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
- Step 8 先运行 `manifest_builder.py`，把正文需求块转写到 `workspace/references/images.yaml`。
- 大模型只能基于 `images.yaml` 的 `purpose`、`fact_source`、`description`、`prompt_hint` 生成源码文件。
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
    source: ai
    diagram_type: architecture
    engine: mermaid
    purpose: 展示系统整体分层与核心组件关系
    fact_source: thesis-workspace/references/prompt/background.md
    placement: 图前说明架构目标，图后分析分层职责
    status: pending
    description: 展示系统整体分层、组件关系与数据流向
    prompt_hint: 根据论文背景生成具体架构，不要使用默认模板
    source_file: workspace/final/images/sources/image_1.mmd
    output_file: workspace/final/images/image_1.png
    render_status: pending
```

### engine 推断规则

| source / diagram_type | 默认 engine | 源码后缀 |
|---|---|---|
| `source=user` | `user` | 无源码 |
| `diagram_type=er/erd/dot` | `graphviz` | `.dot` |
| `diagram_type=flowchart/activity/usecase/sequence/class/plantuml` | `plantuml` | `.puml` |
| `diagram_type=architecture/module` | `mermaid` | `.mmd` |
| 其他 AI 图 | `mermaid` | `.mmd` |

---

## 系统设计章节双图策略(硬约束)

### ER 图生成口径(硬约束)

- 默认引擎：`engine=graphviz`，源码格式：`.dot`
- 唯一事实源：`thesis-workspace/references/prompt/background.md`
- 唯一配置源：`thesis-workspace/.thesis-config.yaml -> er_modeling`
- 教科书 DOT 要求：实体居中、字段环绕、字段中文
- 当 background.md 的表标题同时包含中文逻辑名与英文物理表名时，ER 图实体节点优先使用英文物理表名；字段说明仍保持中文语义。
- 关联表无论写成 `角色表`、`角色表（sys_role）` 还是 `角色表(sys_role)`，都应优先归一到英文物理表名后再参与 ER 图生成。
- DOT 输出约束：不要显式生成 `label=` 属性，直接使用节点文本。
- 信息不足时：尽量生成并 warning，不因字段说明缺失直接阻断。
- 只有 ER 图受 `er_modeling` 配置影响；架构图、流程图、模块图、时序图不跟随该配置。

| 图表 | 来源 | 推荐 engine | 占位符标记 |
|------|------|-------------|------------|
| 系统整体架构图 | AI 生成 | `mermaid` | `[image_N]` |
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
- 适合论文插图展示

只输出PlantUML代码。
```

- 架构图、模块图等 Mermaid 非流程型结构图不附加这段 PlantUML 提示词。
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
# Step 1: 从正文占位符和 image-requirement 块生成 images.yaml
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
| `kroki` | 在线 API 渲染 Mermaid/PlantUML | 需要网络 |
| `auto` | Mermaid/PlantUML 自动选择可用方式；DOT 仍走 Graphviz | 已安装的优先 |

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

- `graphviz`：默认模式，读取 `background.md` 作为唯一事实源，输出教科书风格 Graphviz DOT；强调实体居中、字段环绕、字段中文，信息不足时尽量生成并 warning。
- `mermaid`：用于普通架构图、流程图、模块图等。
- `plantuml`：用于用例图、时序图、类图和活动图，更符合 UML 表达规范。
