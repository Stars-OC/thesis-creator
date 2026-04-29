# Step 8: 图片生成与渲染

> **状态管理(强制执行)**：
> 1. 启动前：`python scripts/status_manager.py thesis-workspace/ --ensure`
> 2. 启动时：`python scripts/status_manager.py thesis-workspace/ --check-step 8`
> 3. 前置条件通过后：`--update-step 8 --action start`
> 4. 完成后：`--update-step 8 --action complete`
>
> **统一入口(推荐)**：`python scripts/lifecycle.py --workspace thesis-workspace/ --step 8 --event start|complete`

> **整合流程：图片生成 → 渲染 → 插入到 Word**

---

## 完整工作流

```mermaid
flowchart TD
    A[扫描正文中的 image 占位符] --> B[读取 references/images.yaml]
    B --> C[校验占位符与清单一致性]
    C --> D[按 source 类型生成或校验图片]
    D --> E[渲染 PNG 或检查用户图片]
    E --> F[将 [image_N] 替换为 Markdown 图片引用]
    F --> G[输出更新后的终稿]
    G --> H[✅ 图片生成完成]
    H --> I[进入 Step 9 导出]
```

---

## 系统设计章节双图策略(硬约束)

### ER 图生成口径(硬约束)

- 默认模式：`graph_type=dot`
- 唯一事实源：`thesis-workspace/references/prompt/background.md`
- 教科书 DOT 要求：实体居中、字段环绕、字段中文
- 信息不足时：尽量生成并 warning，不因字段说明缺失直接阻断

| 图表 | 来源 | 占位符标记 |
|------|------|------------|
| 系统整体架构图 | **AI(大模型)生成** | 标准图表占位符 |
| 系统功能模块图 | **用户手动提供** | `<!-- 用户提供图片：图4-2 系统功能模块图 -->` |
| 各模块业务流程图 | **AI(大模型)生成** | 标准图表占位符 |
| 实体 E-R 图(按配置决定单图单表或多表同图) | **AI(大模型)生成** | 标准图表占位符 |

> 生成前请先检查并修改 `thesis-workspace/.thesis-config.yaml`，尤其是 `er_modeling.graph_type`、`er_modeling.diagram_scope`、`diagram_generation.flowchart_direction`、`format.table_font`。
> `chart_generator.py` 会识别 `用户提供图片` 占位符并在报告中列出待手填图片清单。

## 系统实现章节(第5章)图片策略(硬约束)

| 图表 | 来源 | 占位符标记 |
|------|------|-----------|
| 各功能界面截图 | **用户手动提供** | `<!-- 用户提供图片：图5-X XX功能界面截图 -->` |
| 系统运行效果图 | **用户手动提供** | `<!-- 用户提供图片：图5-X XX运行效果图 -->` |

> **写作组合(硬约束)**：文字描述 + 用户提供系统截图 + 核心代码实现
> 第5章的图片全部由用户提供系统实际运行截图，AI 不自动生成。

---

## 图片生成完整性验证(硬约束)

### 验证命令
python scripts/chart_generator.py workspace/final/论文终稿.md --output workspace/final/images/ --report

### 验证检查项
| 检查项 | 要求 | 不达标处理 |
|--------|------|-----------|
| 占位符全部替换 | 论文中不得残留 `<!-- 图表占位符` 标记 | 重新执行图片生成 |
| 图片文件存在 | images/ 下每个引用的图片文件必须存在 | 补充生成 |
| 图片非空 | 每个 PNG 文件 > 1KB | 重新渲染 |
| 图片引用一致 | MD 中的图片路径与 images/ 下文件名一一对应 | 修正路径 |

---

| 图片类型 | 代码/语法 | 适用章节 | 示例 |
|----------|-----------|----------|------|
| 系统架构图 | `graph LR` | 第4章 系统设计 | 横向分层架构、模块关系 |
| 功能模块图 | `graph TB` | 第4章 系统设计 | 系统→模块→功能树状结构 |
| 流程图 | `flowchart LR` | 第4-5章 功能设计/实现 | 登录流程、业务流程 |
| **概念 ER 图** | **`.thesis-config.yaml -> er_modeling.graph_type=dot` → ` ```dot `** | **第4章 数据库设计** | **实体居中、字段上下分布、Graphviz 渲染，且脚本自动补图下 80-120 字说明** |
| **工程 ERD** | **`.thesis-config.yaml -> er_modeling.graph_type=erd` → `erDiagram`** | **第4章 数据库设计** | **按 `diagram_scope` 输出单表或多表 ERD** |
| 用例图 | `graph LR` | 第4章 需求分析 | 用户用例 |
| 时序图 | `sequenceDiagram` | 第5章 接口调用 | API交互时序 |
| 类图 | `classDiagram` | 第5章 类设计 | 类结构关系 |

---

## 图表尺寸约束(硬约束)

| 约束项 | 要求 |
|--------|------|
| 流程图节点数 | 每张图 ≤ 10 个节点(超出自动拆分为多张子图) |
| E-R 图实体数 | 每张图 ≤ 6 个实体 |
| 模块图层级 | 最多 2 层(系统→子模块→功能) |
| 渲染高度 | Mermaid 渲染高度上限 800px |
| 导出高度 | Word 插图高度不超过 12cm |
| 图文比例 | 每页至少 40% 文字内容 |

---

## 执行命令

```bash
# 方式1: 分步执行
# 生成前请先检查并修改 thesis-workspace/.thesis-config.yaml
# - ER 图按 er_modeling.graph_type + er_modeling.diagram_scope 控制
# - 架构图优先按 diagram_generation.architecture_mode 走模型生成
# - 流程图方向按 diagram_generation.flowchart_direction 控制
# - 三线表字体按 format.table_font 控制

# Step 1: 从占位符生成图代码(原位替代，不产生副本)
python scripts/chart_generator.py workspace/final/论文终稿.md --output workspace/final/images/ --replace

# 若有章节上下文，可传入 --context 提升流程图步骤匹配准确度
python scripts/chart_generator.py workspace/final/论文终稿.md --output workspace/final/images/ --replace --context workspace/drafts/chapter_4.md

# Step 2: 渲染代码块为 PNG，并更新 Markdown
# - Mermaid / ERD: 走 mmdc / playwright / kroki
# - DOT: 走 Python graphviz + 本地 dot
python scripts/chart_renderer.py --input workspace/final/论文终稿.md --output workspace/final/images/ --method auto --update

# 方式2: 一键完成(推荐)
# AI 自动执行完整流程
```

---

## 渲染方法选项

| 方法 | 说明 | 优先级 | 依赖 |
|------|------|--------|------|
| `graphviz` | DOT 本地渲染 | DOT 固定路径 | `pip install graphviz` + 本机安装 Graphviz `dot` |
| `mmdc` | Mermaid CLI(本地) | 1 | `npm install -g @mermaid-js/mermaid-cli` |
| `playwright` | 浏览器渲染(本地) | 2 | `pip install playwright && playwright install` |
| `kroki` | 在线 API | 3 | 需要网络 |
| `auto` | Mermaid 自动选择(按优先级尝试)；DOT 仍走 Graphviz | - | 已安装的优先 |

---

## 调试与验收（最小烟测）

```bash
# 原则：不基于论文终稿做测试，而是使用独立最小测试文件
# 每种模式各 3 张图，便于快速回归验证

# 1) ERD 模式最小烟测（3 张图）
python scripts/chart_renderer.py --input workspace/final/ER图_erd烟测.md --output workspace/final/images/ --method auto --update --report

# 2) DOT 模式最小烟测（3 张图）
python scripts/chart_renderer.py --input workspace/final/ER图_dot测试_由易到难.md --output workspace/final/images/ --method auto --update --report

# 3) 验收点
# - 两个最小测试文件中的代码块都被替换为图片引用
# - images/ 下存在 6 张对应 PNG
# - 每张 PNG 文件 > 1KB
# - DOT 模式保持实体居中、字段上下分布
```

## 最小烟测文件

- `workspace/final/ER图_erd烟测.md`：ERD 模式最小测试，固定 3 张图
- `workspace/final/ER图_dot测试_由易到难.md`：DOT 模式最小测试，固定 3 张图

---

## 输出文件

- `workspace/final/images/图X-X.png` - 渲染后的图片
- `workspace/final/images/chart_report.md` - 占位符分析报告(可选，`chart_generator.py --report`)
- `workspace/final/images/render_report.md` - 图表渲染报告(可选，`chart_renderer.py --report`)

---

## Step 8 中 ER 图的推荐口径

- `dot`：默认模式，读取 `background.md` 作为唯一事实源，输出教科书风格 Graphviz DOT；强调实体居中、字段环绕、字段中文，信息不足时尽量生成并 warning。
- `erd`：用于工程 ERD，输出 Mermaid `erDiagram`，强调字段列表与工程表达，可按 `diagram_scope` 生成单表或多表视图。
- `chen`：保留为 Mermaid `flowchart LR` 的传统概念 ER 图兜底模式。
