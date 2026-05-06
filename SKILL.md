---
name: thesis-creator
description: 面向中国本科生的毕业论文全流程写作辅助系统。支持从选题到交稿的端到端工作流，包含降重优化、AIGC 降低和本地检测功能。用户说「帮我写论文」或「帮我降重」等时触发。
---

# 论文创作 Agent 系统

面向中国本科生的**毕业论文全流程写作辅助系统**。

---

## 核心原则

> [!IMPORTANT]
> **工作区隔离原则**：AI 始终在用户项目目录下的 `thesis-workspace/` 工作。所有产出文件都在用户工作区内。

---

## 触发条件

| 触发语 | 执行动作 |
|--------|----------|
| 「帮我写论文，主题是…」 | 全流程（Step 0-9） |
| 「帮我降重这段文字：…」 | 仅 Step 5 |
| 「降低这段的 AIGC 率：…」 | 仅 Step 6：必须输出“处理前计划 → 改写文本 → 清单自检”，不得只给改写结果 |
| 「检测这段文字的 AIGC 率」 | AIGC 检测 |
| 「帮我生成论文大纲」 | Step 0-3 |
| 「初始化工作区」 | Step 0（工作区不存在直接初始化） |
| 「继续」 | 仅在当前步骤的强制交互点、前置校验和质量门禁均已满足后继续流程 |
| 「生成摘要」 | Step 4（仅摘要部分） |
| 「生成图片」「生成图表」 | Step 8 |
| 「导出 Word」「导出文档」 | Step 9 |
| 「一键导出」 | Step 8+9 |

---

## 工作流程概览

```mermaid
flowchart LR
    A[Step 0: 初始化] --> B[Step 1-2: 准备]
    B --> C[Step 3: 大纲]
    C --> D[Step 3→4: 文献搜索与建池]
    D --> E[Step 4: 撰写]
    E --> F[Step 5-6: 降重]
    F --> G[Step 7: 合并检测]
    G --> H[Step 8: 图片生成]
    H --> I[Step 9: 导出Word]
```

> **⚠️ 流程顺序**：大纲确认 → 文献搜索与建池 → 正文写作 → 合并 → 图片生成 → 导出 Word
> 状态文件路径：`thesis-workspace/.thesis-status.json`
> 若文件不存在，`status_manager.py` 会自动创建。
>
> **推荐统一入口**：`scripts/lifecycle.py`（整合日志 + 状态管理）

---

## 继续与暂停点规则

> [!IMPORTANT]
> **「继续」不是跳过按钮。** 若当前流程仍存在强制交互点、前置校验或质量门禁未完成，则必须先完成对应动作，再允许进入下一步。

### 不可跳过的暂停点

1. **Step 0 初始化后**：必须先运行 `python scripts/lifecycle.py --workspace thesis-workspace/ --check-workspace`，并检查 `thesis-workspace/references/prompt/background.md` 是否已补全；工作区必须通过脚本初始化并生成 `thesis-workspace/.thesis-config.yaml`、`thesis-workspace/.thesis-status.json`、`thesis-workspace/logs/` 与 `thesis-workspace/workspace/references/images.yaml`；未完成时只能提示用户编辑，禁止直接推进到 Step 1/3。
2. **Step 3 大纲确认后**：必须先询问用户文献数量（20-30 / 30-50 / 15-20），并展示搜索耗时预估后，进入 Step 3→4 之间的“文献搜索与建池”阶段；该阶段不是独立 Step，但后续在 Step 4/6/7 中如发现文献不足、语种比例失衡或文献失效，必须允许回流补池后再继续写作或检测。
3. **Step 4 每章写作时**：必须先完成 Stage 1 要点规划，待用户确认后才能进入 Stage 2 扩写；如果当前仍停留在 Stage 1，用户回复「继续」只能视为确认本章要点，不能跳过更早的未完成门禁。
4. **Step 7 合并检测后**：若同一 `ref_id` 在终稿中重复出现，必须硬阻断并回退修正，禁止带重复引用进入 AIGC 检测；若 AIGC 检测未通过，必须回退到 Step 5/6 继续改写与审校，禁止进入 Step 8 图片生成或 Step 9 导出。
5. **Step 8 图片生成前**：必须按“抽取图片需求 → 准备源码文件 → 大模型填写 `.dot/.mmd/.puml` → 渲染 PNG → 回填 `[image_N]` → 完整性验证”执行；使用 `scripts/charts/manifest_builder.py`、`source_writer.py`、`render.py`、`markdown_updater.py`、`validate.py`，最终已渲染 AI 图片不得残留 `[image_N]`。

---

## 详细步骤（按需加载）

| 步骤 | 说明 | 详细文档 |
|------|------|----------|
| Step 0 | 工作区初始化 | `workflows/step_0_init.md` |
| Step 3 | 生成论文大纲 | `workflows/step_3_outline.md` |
| Step 4 | 分章节撰写 | `workflows/step_4_writing.md` |
| Step 6 | 审校润色 | `workflows/step_6_review_polish.md` |
| Step 7 | 合并与检测 | `workflows/step_7_merge_detect.md` |
| Step 8 | 图片生成与渲染（ER图默认读取 `background.md`，优先输出教科书风格 DOT，信息不足时尽量生成并 warning） | `workflows/step_8_image.md` |
| Step 9 | 文档导出 | `workflows/step_9_export.md` |
| 参考文献 | 文献池管理 | `workflows/reference_workflow.md` |

---

## 参考文献（独立存放）

> **核心改进**：文献池独立存放在 `workspace/references/verified_references.yaml`
> **文献校验状态**：`verified_doi / verified_metadata_only / broken_doi_metadata_ok / missing_doi_unverified / invalid_reference`
> **规则说明**：无 DOI 不等于假文献；允许通过元数据验证的真实文献继续进入文献池。

### 图片需求清单

- 正文图片占位符统一使用 `[image_1]`、`[image_2]` 等格式
- 图片需求清单统一记录到 `workspace/references/images.yaml`
- `workspace/references/images.yaml` 必须采用结构化字段，至少包含 `id`、`title`、`chapter`、`section`、`source`、`diagram_type`、`engine`、`purpose`、`fact_source`、`placement`、`status`、`description`、`source_file`、`output_file`、`render_status`；可选 `prompt_hint` 用于指导大模型生成源码
- Step 4 只负责记录 `[image_N]` 与 `image-requirement` 图片需求块，Step 8 再生成 `images.yaml`、准备源码文件、由大模型填写 `.dot/.mmd/.puml`、渲染 PNG 并回填 Markdown 图片引用
- 架构图、模块图、流程图、ER 图等 AI 图片必须先有 manifest 记录；用户提供图片必须在清单中标明 `source=user` 和待补状态
- 图表引擎按图类型明确映射，不自由摇摆：**流程图/活动图/用例图/时序图/类图 → PlantUML (`.puml`)；ER 图 → Graphviz DOT (`.dot`)；架构图/模块图 → Mermaid (`.mmd`)；用户截图 → `user`**
- **仅当流程图使用 PlantUML 生成时**，必须附加固定提示词模板，并将其中主题替换为当前图表标题或用途描述：

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
- 不再默认使用 Mermaid 流程图；普通流程图同样优先走 PlantUML。
- **生成测试图或单独响应“生成流程图”类指令时，默认行为是将源码写入 `thesis-workspace/workspace/final/images/sources/` 对应 `.puml/.dot/.mmd` 文件，而不是在控制台直接输出完整图表源码；仅在用户明确要求“只输出代码”时，才直接返回源码文本。**

### 流程

1. **Step 3 大纲确认后询问文献数量**（默认 20-30 篇）
2. **多源搜索**：Semantic Scholar + CrossRef + OpenAlex
3. **DOI 验证**：判断 4xx 错误状态码
4. **合并去重**：多源结果合并，按相关度选出最相关 x 篇（`scripts/reference_merger.py`）
5. **写作时从文献池选取未占用引用**
6. **文献搜索与建池阶段可回流复用**：在 Step 4/6/7 任一阶段，如果当前章节缺少可用未占用文献、文献验证失败、语种比例不达标或引用密度不足，必须回到该阶段补充搜索，并增量更新 `workspace/references/verified_references.yaml`
7. **单篇文献整篇仅允许引用一次**：一旦某个 `ref_id` 被正文使用一次，就必须标记为已占用，后续章节不得重复使用；Step 7 发现重复 `ref_id` 必须硬阻断
8. **中文文献质量不足时提示人工补充**：若自动源无法满足中文文献占比 >65%，必须提示用户从 CNKI、万方、学校图书馆等外部高质量来源人工补充真实中文文献，禁止伪造
9. **文献 YAML 输出必须安全可解析**：标题含英文冒号、中文冒号、括号等特殊字符时，仍必须能被 `yaml.safe_load()` 读取

详见 `workflows/reference_workflow.md`

---

## 用户工作区目录结构

```
thesis-workspace/
├── README.md                  # 工作区使用说明
├── .thesis-config.yaml        # 配置文件
├── references/                # 参考资料（用户放入）
│   ├── templates/             # 学校模板
│   ├── examples/              # 范文
│   ├── guidelines/            # 规范
│   └── prompt/background.md   # 论文背景（必填）
├── workspace/                 # 论文产出
│   ├── outline.md             # 大纲
│   ├── references/                # 参考文献池（独立）⭐
│   │   ├── verified_references.yaml  # 已验证文献池
│   ├── cited_references.json  # 引用记录（每章引用的ref_id）⭐
│   ├── drafts/                # 初稿（仅含临时引用编号，无参考文献列表）⭐
│   │   ├── 参考文献.md         # 合并阶段生成的参考文献（独立MD文件，GB/T 7714格式）⭐
│   ├── final/                 # 终稿
│   │   ├── 论文终稿.md         # 终稿（引用编号已重排）
│   │   ├── 论文终稿.docx
│   │   └── images/            # 图片
│   └── reports/               # 报告
├── logs/                      # 日志
└── .thesis-status.json        # 状态
```

> ⭐ 标记为本次更新新增或变更的文件

---

## 防错机制

| 问题 | 影响 | 处理 |
|------|------|------|
| 缺少规定动作章节 | 致命 | 自动补充 |
| 设计实现未分离 | 致命 | 强制拆分 |
| **章节顺序错误** | **致命** | **强制调整为：系统分析→系统设计→系统实现→系统测试→总结与展望** |
| **使用 LLM 上下文合并文档** | **致命** | **必须使用 merge_drafts.py 脚本** |
| 图表不足 | 严重 | 提示补充 |
| **数据库表数量不足** | **严重** | **检查 background.md 表定义，确保 ≥11 张表** |
| **未执行状态管理脚本** | **致命** | **每个 Step 必须通过 lifecycle.py 或 status_manager.py 记录状态，禁止大模型自行维护状态** |
| **日志未通过脚本记录** | **严重** | **所有流程日志必须通过 logger.py 输出，禁止大模型自行生成日志内容** |
| **文献链接 404** | **严重** | **合并前执行 reference_validator.py --check-404，404文献必须替换** |
| **图片文件缺失** | **严重** | **Step 8 完成后检查 images/ 目录，所有占位符必须有对应 PNG 文件** |
| 参考文献虚构 | 严重 | DOI验证+重生成 |
| 参考文献数量超标 | 严重 | 按相关度截取 |
| **参考文献缺少中英文** | **严重** | **中文和英文文献都必须包含，缺少则触发补充搜索** |
| **参考文献 YAML 解析失败** | **严重** | **reference_merger.py 必须使用安全 YAML 输出，特殊字符标题保存后仍可 `yaml.safe_load()`** |
| **中文文献比例不足** | **严重** | **自动源不足时提示从 CNKI、万方、学校图书馆人工补充真实中文文献，禁止伪造** |
| **引用复用同一 ref_id** | **严重** | **同一篇文献整篇仅允许引用一次，发现重复占用必须硬阻断并回流补池改写引用** |
| AI模板词超标 | 中等 | 按 Step 6 的 AIGC 标准流程处理：先做处理前计划，再按“场景化重写 → 结构重组 → 细节注入 → 语言去模板化”改写，最后输出清单自检；禁止只做同义替换或只给改写结果 |
| **AIGC 降低缺少自检清单** | **严重** | **必须补齐处理前计划、改写文本、自检表；自检项出现“未通过”时继续局部修正，不得交付为最终版** |
| **章节内自建参考文献列表** | 中等 | 删除，合并阶段统一生成 |
| **background.md 为空或未完善** | **致命** | **提示用户编辑 `thesis-workspace/references/prompt/background.md`，禁止控制台交互式输入** |
| **ER 图事实源不一致** | **严重** | **Step 8 的 ER 图默认读取 `background.md`，仅 ER 图受 `thesis-workspace/.thesis-config.yaml` 的 `er_modeling` 配置影响，优先输出教科书风格 DOT，且 DOT 输出不要显式使用 `label=`** |

---

## Prompt 文件（写作时加载）

| 文件 | 说明 | 加载时机 |
|------|------|----------|
| `prompts/writer_guidelines.md` | 写作规范 | Step 4 |
| `prompts/aigc_reducer_prompt.md` | AIGC 表达质量优化与深度人工化流程 | Step 6 |
| `prompts/humanizer_guidelines.md` | 人工化改写细则与风险边界 | Step 6 |
| `prompts/reference_citation_prompt.md` | 引用铁律 | Step 4 |
| `workspace/references/verified_references.yaml` | 文献池 | **必须加载** |

---

## Script 文件

| 文件 | 说明 |
|------|------|
| `scripts/reference_engine.py` | 多源搜索 + DOI验证 |
| `scripts/reference_merger.py` | 文献合并去重 + 选出最相关 x 篇 |
| `scripts/document_exporter.py` | Word导出 + 图片插入 |
| `scripts/merge_drafts.py` | 章节合并 |
| `scripts/aigc/detect.py` | AIGC检测 |
| `scripts/aigc/technical_detect.py` | 技术论文 AIGC 检测 |
| `scripts/charts/manifest_builder.py` | 从正文 `[image_N]` 与 `image-requirement` 生成或更新 `images.yaml` |
| `scripts/charts/source_writer.py` | 根据 `images.yaml` 准备并校验 `.mmd/.dot/.puml` 源码文件 |
| `scripts/charts/render.py` | 按 Mermaid、Graphviz、PlantUML 渲染 PNG |
| `scripts/charts/markdown_updater.py` | 将已渲染图片回填为 Markdown 图片引用 |
| `scripts/charts/validate.py` | 校验源码、PNG、占位符和用户待补截图状态 |

---

## 致谢

致谢生成位于 `Step 4`（与摘要同阶段），输出文件为 `workspace/drafts/致谢.md`，由 `merge_drafts.py` 在合并阶段自动纳入终稿。

> 注意：致谢不计入七章正文结构，但属于论文交付的必备内容之一。
