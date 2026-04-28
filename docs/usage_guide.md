# 论文创作 Agent 系统 - 使用指南

> 面向中国本科生的毕业论文全流程写作辅助系统
> **最后更新：2026-04-11**

---

## 一、系统概述

### 1.1 功能特点

| 功能 | 说明 |
|------|------|
| 全流程覆盖 | 从选题到交稿的端到端工作流 |
| 降重优化 | 句式重构、同义替换、段落重组 |
| AIGC 降低 | 模拟人类写作特征，降低检测风险 |
| 本地检测 | 轻量级 AIGC 检测工具，快速预估 |
| 格式检查 | 自动检查论文结构规范性 |
| 智能讨论 | 三轮深入讨论充分理解论文需求 |
| **图片生成** ⭐ NEW | 自动生成架构图、流程图、E-R图等 |
| **图片插入** ⭐ NEW | Word 文档自动插入图片和图注 |
| 文档导出 | 支持 Word/PDF 格式一键导出（含图片）|

### 1.2 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 |
| Python | 3.9+ |
| Claude Code | 已安装并可运行 |

---

## 二、安装配置

### 2.1 快速安装（Windows）

```powershell
# 进入项目目录
cd thesis-creator

# 运行安装脚本
.\scripts\install.ps1
```

### 2.2 手动安装

```powershell
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r scripts\requirements.txt

# 4. 验证安装
python scripts\aigc_detect.py --help
```

### 2.3 可选：安装完整版 AIGC 检测

如需更高精度的 AIGC 检测（包含 GPT-2 困惑度），需额外安装：

```powershell
# 安装 PyTorch CPU 版
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 安装 Transformers
pip install transformers>=4.30.0
```

> ⚠️ 完整版额外占用约 2.5 GB 磁盘空间。

---

## 三、快速开始

### 3.1 准备参考资料

将以下文件放入 `references/` 目录：

```
references/
├── templates/     # 论文格式模板（.docx/.pdf）
├── examples/      # 优秀范文（.docx/.pdf）
├── guidelines/    # 学校规范（.docx/.pdf）
├── prompt/        # 背景信息
│   └── background.md  # 必填：论文背景信息
└── reference/
    ├── code/      # 参考代码（.py/.R/.sql）
    └── doc/       # 参考文献（.pdf/.docx）
```

### 3.2 触发 Skill

在 Claude Code 中说：

```
帮我写论文，主题是《大数据在精准营销中的应用研究》
```

系统将自动执行完整工作流：

```
Step 0: 初始化工作区
    ↓
Step 1: 环境准备 → Step 1.5: 背景信息讨论
    ↓
Step 2: 读取参考资料 → Step 3: 生成论文大纲
    ↓
Step 4: 分章节撰写 → Step 5: 降重处理
    ↓
Step 6: AIGC 人性化 → Step 7: 自检输出
    ↓
Step 8: 文档导出（Word/PDF）
```

### 3.3 单功能模式

| 触发语 | 执行动作 |
|--------|----------|
| 「帮我降重这段文字：…」 | 仅执行降重 |
| 「降低这段的 AIGC 率：…」 | 仅执行人性化改写 |
| 「检测这段文字的 AIGC 率」 | 仅调用检测工具 |
| 「帮我生成论文大纲」 | Step 0-3 |
| 「分析这段文字的特征」 | 仅调用文本分析 |
| 「检查论文格式」 | 仅调用格式检查 |
| 「生成图片」/「生成图表」/「生成架构图」 | 图片生成 ⭐ NEW |
| 「为第X章配图」 | 为指定章节生成图表 ⭐ NEW |
| 「导出 Word」/「导出 PDF」 | 文档格式转换 |
| 「一键导出」 | 图片生成 + 文档导出 ⭐ NEW |

---

## 四、工作流程详解

### 4.1 Step 0：初始化工作区

**触发条件**：
- 首次执行「帮我写论文」
- 或直接说「初始化工作区」

**执行内容**：
1. 检查工作区是否存在
2. 创建完整目录结构
3. 生成工作区 README.md
4. 创建日志目录
5. 初始化 `.thesis-status.json` 状态文件

**输出示例**：

```
✅ 工作区初始化完成！

📂 工作区位置：thesis-workspace/
📝 日志目录：thesis-workspace/logs/latest/

📋 请按以下步骤准备参考资料：

1. 打开 thesis-workspace/README.md 阅读详细说明
2. 将学校模板放入 references/templates/
3. 将优秀范文放入 references/examples/
4. 将写作规范放入 references/guidelines/
5. 填写 references/prompt/background.md（必填）
6. 将参考文献放入 references/reference/doc/
7. 将参考代码放入 references/reference/code/

⏸️ 准备完成后，请回复「继续」开始论文创作。
```

### 4.2 Step 1：环境准备

- 创建 `workspace/` 子目录
- 检查 `references/` 目录，扫描用户文件
- 自动排除 `README.md`、模板占位文件等非用户文件
- 输出状态报告

### 4.3 Step 1.5：背景信息讨论 ⭐

> [!IMPORTANT]
> 此步骤是确保论文质量的关键环节，不可跳过。

**流程**：
1. 检查 `background.md` 是否存在
2. 进行三轮讨论：
   - **第一轮**：研究主题与背景
   - **第二轮**：研究方法与技术路线
   - **第三轮**：论文结构与章节安排
3. 生成背景确认报告 `workspace/background_confirmation.md`
4. 用户确认后进入下一步

**支持模式**：
- 用户填写模式：用户预先填写 background.md
- AI 推断模式：AI 根据主题自动推断
- 混合模式：用户填写 + AI 补充

### 4.4 Step 2：读取参考资料

- 读取模板 → 提取格式规范（字体、行距、页边距等）
- 读取范文 → 学习写作风格与章节比例
- 读取规范 → 提取硬性要求（字数、查重率、AIGC 率上限）
- 读取参考代码 → 了解技术实现细节
- 生成「参考资料摘要」

### 4.5 Step 3：生成论文大纲

**执行内容**：
1. 根据主题生成符合规范的大纲
2. 为每个章节预估字数
3. 生成图表占位符清单
4. 保存到 `workspace/outline.md`

**防错检查**：

| 检查项 | 要求 | 不达标处理 |
|--------|------|-----------|
| 规定动作章节 | 必须包含：绪论、国内外研究现状、可行性分析、结论 | 自动补充缺失章节 |
| 设计实现分离 | 第4章设计、第5章实现，不可合并 | 强制拆分 |
| 篇幅比例 | 正文各章字数合理分配 | 提示建议比例 |

**用户交互**：用户可修改大纲，确认后进入下一步

### 4.6 Step 4：分章节撰写

**规则**：
- 每段 150-300 字，包含论点+论据+小结
- 每千字至少 2 个文献引用（GB/T 7714-2015）
- 代码片段不超过 20 行，需有设计说明和效果分析
- 使用图表占位符标记图表位置

**防错检查**（每章完成后自动执行）：

| 检查项 | 要求 | 不达标处理 |
|--------|------|-----------|
| 图表占位符 | 每章至少 2 个 | 提示补充 |
| 代码长度 | ≤20 行 | 拆分或精简 |
| 参考文献标记 | 引用需标注来源 | 标记缺失位置 |
| 段落结构 | 论点+论据+小结 | 提示优化 |

**输出**：每章保存到 `workspace/drafts/`

### 4.7 Step 5：降重处理

**降重策略**：
1. **句式重构**：主被动转换、拆分合并
2. **同义替换**：词汇、短语替换（术语白名单保护）
3. **段落重组**：逻辑顺序调整
4. **引用编织**：增加引用密度

**输出**：`workspace/reduced/`

### 4.8 Step 6：AIGC 人性化

**消除 AI 特征**：

| 优先级 | 问题 | 处理方式 |
|--------|------|----------|
| P0 | 模板化过渡词 | 替换为自然表达 |
| P0 | 句长均匀 | 增加波动（10-50字） |
| P0 | 结构整齐 | 打破规律性 |
| P1 | 缺乏主观性 | 添加主观表达 |
| P1 | 逻辑过于完美 | 适当增加转折 |
| P2 | 段首同质 | 变换开头方式 |
| P2 | 标点规律 | 增加标点多样性 |

**自检循环**：检测 → AIGC率≤阈值? → 通过/改写（最多3轮）

### 4.9 Step 7：自检输出

**检查项**：

| 检查项 | 方式 | 输出 |
|--------|------|------|
| 规定动作检查 | 确保章节完整 | 检查报告 |
| 格式检查 | 调用 format_checker.py | 格式报告 |
| 图表完整性 | 检查占位符数量和状态 | 图表清单 |
| AIGC 检测 | 调用 aigc_detect.py | 检测报告 |
| 写作质量 | 调用 text_analysis.py | 质量报告 |

**输出文件**：
- `workspace/final/论文终稿.md`
- `workspace/final/quality_report.md`

---

### 4.8 Step 8：图片生成与渲染 🖼️ ⭐ NEW

> **一键生成论文图表并插入到 Word 文档**

**触发条件**：
- 用户说「生成图片」「生成图表」「生成架构图」
- 用户说「为第X章配图」
- AIGC 检测通过后自动提示
- 导出文档前自动执行

**支持的图片类型**：

| 图片类型 | Mermaid 语法 | 适用章节 |
|----------|-------------|----------|
| 系统架构图 | `graph TB` | 第4章 系统设计 |
| 流程图 | `flowchart TD` | 第4-5章 功能设计/实现 |
| 概念 ER 图 | `flowchart LR` | 第4章 数据库设计 |
| 用例图 | `graph LR` | 第4章 需求分析 |
| 时序图 | `sequenceDiagram` | 第5章 接口调用 |
| 类图 | `classDiagram` | 第5章 类设计 |

**使用方法**：

```powershell
# 方式1: 分步执行（可调试）
# Step 1: 从占位符生成 Mermaid 代码（原位替换，不生成副本）
python scripts/chart_generator.py workspace/final/论文终稿.md -o workspace/final/images/ --replace

# Step 2: 渲染 Mermaid 为 PNG 并更新 Markdown（原位覆盖）
python scripts/chart_renderer.py --input workspace/final/论文终稿.md --output workspace/final/images/ --method auto --update

# 方式2: 一键生成（推荐）
# AI 自动执行：扫描 → 生成 → 渲染 → 更新引用
```

**渲染方法选项**：

| 方法 | 说明 | 依赖 |
|------|------|------|
| `mmdc` | Mermaid CLI（本地） | `npm install -g @mermaid-js/mermaid-cli` |
| `playwright` | 浏览器渲染（本地） | `pip install playwright && playwright install` |
| `kroki` | 在线 API | 需要网络 |
| `auto` | 自动选择 | 按优先级尝试 |

**输出文件**：
- `workspace/final/images/图X-X.png` - 渲染后的图片
- `workspace/final/images/image_manifest.md` - 图片清单
- `workspace/final/images/chart_report.md` - 图表生成报告

---

### 4.9 Step 9：文档导出与图片插入 📄 ⭐ NEW

> **Word 文档自动插入图片和图注**

**触发方式**：
- AIGC 检测通过后自动提示
- 用户说「导出 Word」「导出文档」「生成Word」
- 用户说「一键导出」（图片+文档）

**图片插入特性**：

| 特性 | 说明 | 格式标准 |
|------|------|----------|
| 自动居中 | 图片居中显示 | 符合论文规范 |
| 尺寸控制 | 默认宽度 12cm | 适合 A4 纸张 |
| 图注格式 | 五号宋体、居中 | 符合学术论文规范 |
| 路径解析 | 支持相对路径 | 自动转换为绝对路径 |
| 失败处理 | 图片不存在时记录警告 | 不中断导出流程 |

**使用方法**：

```powershell
# 导出 Word 文档（含图片）
python scripts/document_exporter.py --input workspace/final/论文终稿.md --format docx

# 导出 PDF 文档
python scripts/document_exporter.py --input workspace/final/论文终稿.md --format pdf

# 同时导出两种格式
python scripts/document_exporter.py --input workspace/final/论文终稿.md --format both
```

**导出成功示例**：

```
[信息] 正在读取: workspace/final/论文终稿.md
[成功] Word 文档已保存: workspace/final/论文终稿.docx
[信息] 成功插入 12 张图片
==================================================
[文档导出报告]
输入文件: workspace/final/论文终稿.md
输出目录: workspace/final/
导出时间: 20260411_194041
--------------------------------------------------
DOCX: [成功]
  路径: workspace/final/论文终稿.docx
  图片: 12 张已插入
==================================================
```

**文档格式规范**：
- 页边距：上下 2.54cm，左右 3.17cm
- 正文字体：宋体 12pt
- 标题字体：黑体，一级标题 14pt，二级标题 12pt
- 行距：1.5 倍行距
- 首行缩进：0.74cm（两个字符）

**PDF 转换依赖**（选择其一）：
- `pip install docx2pdf`（推荐，简单易用）
- LibreOffice（跨平台）
- Microsoft Word（仅 Windows）

---

## 五、Python 工具使用

### 5.1 AIGC 检测（`aigc_detect.py`）

```powershell
# 检测单个文件
python scripts/aigc_detect.py --input workspace/drafts/chapter_01.md

# 检测一段文本
python scripts/aigc_detect.py --text "待检测的文本内容..."

# 检测整个目录
python scripts/aigc_detect.py --dir workspace/reduced/

# 指定输出格式
python scripts/aigc_detect.py --input paper.md --format json

# 使用完整版（需已安装 transformers + torch）
python scripts/aigc_detect.py --input paper.md --mode full
```

**输出示例**：

```
╭───────────────────────────────────────────────────────────╮
│ AIGC 检测报告                                              │
│ 模式：轻量版（4 维度）                                      │
│ 字数：3520                                                 │
╰───────────────────────────────────────────────────────────╯

整体 AIGC 检测率：26.0% ⚡ 中等风险

┌───────────────┬────────┬─────────────────────────────────────┐
│ 维度          │ 分数   │ 说明                                 │
├───────────────┼────────┼─────────────────────────────────────┤
│ 突发性        │ 18.0   │ 句长方差 12.3，接近人类/AI 边界       │
│ 词汇多样性    │ 22.0   │ TTR = 0.41，略低于人类典型值          │
│ 过渡词密度    │ 30.0   │ 过渡词密度 4.2%，高于正常             │
│ 句式模式      │ 20.0   │ 总分总结构占比 60%                    │
└───────────────┴────────┴─────────────────────────────────────┘

高风险段落：第 2、5、8 段

建议：AIGC 检测率中等（26.0%），建议适当改写高风险段落
```

### 5.2 同义词替换（`synonym_replace.py`）

```powershell
# 基本替换
python scripts/synonym_replace.py --input paper.md --output paper_replaced.md

# 自定义替换比例
python scripts/synonym_replace.py --input paper.md --ratio 0.4

# 指定术语白名单
python scripts/synonym_replace.py --input paper.md --whitelist scripts/term_whitelist.txt
```

### 5.3 文本分析（`text_analysis.py`）

```powershell
# 分析单个文件
python scripts/text_analysis.py --input paper.md

# 对比两个文件（改写前后对比）
python scripts/text_analysis.py --input before.md --compare after.md
```

### 5.4 格式检查（`format_checker.py`）

```powershell
# 检查单个文件
python scripts/format_checker.py --input workspace/final/论文终稿.md

# 检查整个目录
python scripts/format_checker.py --dir workspace/drafts/
```

### 5.6 图表生成（`chart_generator.py`）⭐ NEW

```powershell
# 从 Markdown 文件中的占位符生成 Mermaid 代码（原位替换）
python scripts/chart_generator.py workspace/final/论文终稿.md -o workspace/final/images/ --replace

# 指定输出目录
python scripts/chart_generator.py workspace/final/论文终稿.md --output workspace/final/images/ --replace

# 详细模式
python scripts/chart_generator.py workspace/final/论文终稿.md --output workspace/final/images/ --replace --report
```

**支持的图表类型**：

| 图表类型 | Mermaid 语法 | 适用场景 |
|----------|-------------|----------|
| 系统架构图 | `graph TB` | 系统整体架构 |
| 流程图 | `flowchart TD` | 业务流程、操作流程 |
| 概念 ER 图 | `flowchart LR` | 数据库设计（实体/属性/联系） |
| 用例图 | `graph LR` | 功能需求分析 |
| 时序图 | `sequenceDiagram` | 接口调用流程 |
| 类图 | `classDiagram` | 类结构设计 |

### 5.7 图表渲染（`chart_renderer.py`）⭐ NEW

```powershell
# 渲染 Markdown 中引用的 Mermaid 图片（并更新 Markdown 原文）
python scripts/chart_renderer.py --input workspace/final/论文终稿.md --output workspace/final/images/ --method auto --update

# 指定渲染方法
python scripts/chart_renderer.py --input paper.md --output workspace/final/images/ --method mmdc --update

# 渲染方法选项
# mmdc: Mermaid CLI（需安装 @mermaid-js/mermaid-cli）
# playwright: 浏览器渲染（需安装 playwright）
# kroki: 在线 API（需网络）
# auto: 自动选择（推荐）
```

**渲染依赖安装**：

```powershell
# Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Playwright
pip install playwright && playwright install

# Kroki 无需安装，直接使用在线 API
```

### 5.8 文档导出（`document_exporter.py`）

```powershell
# 导出 Word
python scripts/document_exporter.py --input paper.md --format docx

# 导出 PDF
python scripts/document_exporter.py --input paper.md --format pdf

# 同时导出两种格式
python scripts/document_exporter.py --input paper.md --format both
```

> ⭐ 图片插入功能已集成：导出 Word 时自动解析 Markdown 图片引用并插入到文档中。

---

## 六、日志系统

### 6.1 日志目录结构

```
logs/
├── 20260411_150000/           # 按时间戳分目录
│   ├── step_0_init.log        # 初始化日志
│   ├── step_1_env.log         # 环境准备
│   ├── step_1.5_discussion.log # 背景讨论
│   ├── step_2_references.log  # 参考资料分析
│   ├── step_3_outline.log     # 大纲生成
│   ├── step_4_chapter_1.log   # 各章节撰写
│   ├── step_4_chapter_2.log
│   ├── ...
│   ├── step_5_reduce.log      # 降重处理
│   ├── step_6_humanize.log    # AIGC 人性化
│   ├── step_7_aigc.log        # AIGC 检测详情
│   ├── step_7_final.log       # 最终检查
│   ├── step_8_chart.log       # 图片生成与渲染 ⭐ NEW
│   ├── step_9_export.log      # 文档导出（含图片插入） ⭐ NEW
│   ├── warnings.log           # ⚠️ 警告汇总
│   └── session_summary.md     # 会话总结报告
└── latest -> 20260411_150000/ # 最新日志快捷访问
```

### 6.2 日志格式

```
[时间戳] [步骤] [级别] 消息内容
[2026-03-06 15:00:00] [Step 3] [INFO] 开始生成论文大纲
[2026-03-06 15:00:05] [Step 3] [WARN] 检测到缺少"可行性分析"章节，已自动补充
[2026-03-06 15:00:10] [Step 3] [INFO] 大纲生成完成，共 5 章
```

### 6.3 查看日志

```powershell
# 查看最新日志目录
ls logs/latest/

# 查看特定步骤日志
cat logs/latest/step_3_outline.log

# 查看警告汇总
cat logs/latest/warnings.log

# 查看会话总结
cat logs/latest/session_summary.md
```

---

## 七、防错机制

系统自动检测并处理以下常见问题：

| # | 问题 | 影响 | 处理方式 |
|---|------|------|----------|
| 1 | 缺少规定动作章节 | 致命 | 自动补充缺失章节 |
| 2 | 设计与实现未分离 | 致命 | 强制拆分 |
| 3 | 图表严重不足 | 致命 | 提示补充 |
| 4 | 代码堆砌（>20行） | 严重 | 拆分精简 |
| 5 | 参考文献虚构 | 严重 | 标记缺失位置 |
| 6 | 篇幅分配失衡 | 中等 | 提示建议比例 |

---

## 八、常见问题

### Q1：AIGC 检测率一直降不下来怎么办？

1. 确保执行了 Step 6（AIGC 人性化）
2. 手动修改高风险段落
3. 添加更多主观性表达（如「笔者认为」「从实证角度来看」）
4. 增加句长波动，避免每句话长度相近

### Q2：参考文献格式不规范？

1. 使用 GB/T 7714-2015 格式
2. 确保每条文献有 [J]/[D]/[M] 标识
3. 检查引用标记是否与文献列表对应

### Q3：Python 脚本报错？

1. 确认 Python 版本 ≥ 3.9 (`python --version`)
2. 确认已激活虚拟环境 (`.\.venv\Scripts\Activate.ps1`)
3. 确认已安装所有依赖 (`pip install -r scripts\requirements.txt`)
4. 检查文件路径是否使用了正确的分隔符

### Q4：GPT-2 模型下载失败？

1. 检查网络连接
2. 配置 HuggingFace 镜像：`$env:HF_ENDPOINT = "https://hf-mirror.com"`
3. 或使用轻量版（`--mode lite`），无需下载模型

### Q5：如何恢复之前的进度？

直接回复「继续」，系统会自动读取 `.thesis-status.json` 恢复进度。

### Q6：如何重新开始？

删除 `.thesis-status.json` 文件，重新触发 thesis-creator。

---

## 九、注意事项

1. **本地检测为近似估计**
   - 轻量版准确率约 55-65%
   - 完整版准确率约 70-80%
   - 正式提交前建议使用知网/维普进行官方检测

2. **版本控制**
   - 每次改写前自动备份到 `workspace/history/`
   - 默认保留最近 5 个版本

3. **术语保护**
   - 专业术语不会被降重工具打乱
   - 可自定义白名单 `scripts/term_whitelist.txt`

---

## 十、技术支持

如遇问题，请提供以下信息：

1. 操作系统版本
2. Python 版本（`python --version`）
3. 错误信息截图
4. 复现步骤
5. 相关日志文件（`logs/latest/` 目录下）

---

> 最后更新：2026-04-11