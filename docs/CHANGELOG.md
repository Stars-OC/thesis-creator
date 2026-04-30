# 更新日志 (CHANGELOG)

> 本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范

---

## [Unreleased]

### 更新功能 (Changed)

- **规则一致性修复**：主流程明确为 Step 3 大纲确认后进入文献搜索与建池，再进入 Step 4 写作；当写作阶段出现文献不足、验证异常或语种比例不达标时，可回流到文献搜索阶段补池。
- **Step 0 初始化补齐**：`scripts/lifecycle.py` 现会在工作区初始化时自动生成 `thesis-workspace/.thesis-config.yaml` 与 `thesis-workspace/workspace/references/images.yaml`。
- **图片清单路径统一**：图表生成脚本统一读取 `workspace/references/images.yaml`，并同步修正 CLI 提示文案。
- **DOT ER 图输出约束收敛**：`scripts/chart_generator.py` 生成的 Graphviz DOT 概念 ER 图不再显式输出 `label=`，仅 E-R 图受 `er_modeling` 配置控制。
- **引用规则对齐**：`scripts/verified_reference_pool.py` 默认推荐未占用文献；`scripts/merge_drafts.py` 在保持“按正文首次出现顺序编号”的同时，新增同一 `ref_id` 重复引用告警。
- **ER 图测试更新**：同步调整 DOT ER 图与渲染测试，使断言与“无显式 `label=`”规则一致。

---

## [v1.2.0] - 2026-04-24

### 新增功能 ⭐

#### 图片生成与渲染系统（Step 8）

- **自动图表生成**：根据论文内容自动生成架构图、流程图、E-R 图等 Mermaid 图表
- **多渲染模式**：支持在线渲染（mermaid.ink）和离线渲染（Playwright + Puppeteer）
- **模板化图表**：新增 `scripts/templates/charts/` 图表模板目录，提供架构图、E-R 图、流程图、时序图等预设模板
- **主题配置**：新增 `scripts/templates/chart_themes.yaml`，支持自定义图表配色方案
- **智能关键词提取**：新增 `scripts/keyword_extractor.py`，从论文文本中提取关键术语用于图表标注
- **LLM 辅助生成**：新增 `scripts/llm_chart_generator.py`，利用 AI 生成高质量 Mermaid 代码
- **占位符原位替代**：图表占位符自动替换为 Mermaid 代码块，无需额外导出

新增脚本：

| 脚本 | 功能 |
|------|------|
| `chart_generator.py` | 图表生成（增强版，原位替代） |
| `chart_renderer.py` | 在线图表渲染 |
| `chart_renderer_offline.py` | 离线图表渲染 |
| `chart_template_loader.py` | 图表模板加载器 |
| `llm_chart_generator.py` | LLM 辅助图表生成 |
| `keyword_extractor.py` | 关键词提取器 |
| `demo_chart_generation.py` | 图表生成演示 |

#### 文献引用真实性保障

- **引用引擎**：新增 `scripts/reference_engine.py`（1250 行），集成 Semantic Scholar / CrossRef / OpenAlex 三源学术搜索
- **已验证文献池**：新增 `scripts/verified_reference_pool.py`，自动缓存验证通过的文献，避免重复搜索
- **引用提示词**：新增 `prompts/reference_citation_prompt.md`，规范 AI 引用生成行为
- **文献搜索工作流**：新增 `workflows/reference_workflow.md`
- **reference_validator 增强**：支持在线 DOI 验证、虚构文献自动替换为真实文献

#### 配置化系统

- **YAML 配置文件**：新增 `references/templates/.thesis-config.yaml`
  - 学术搜索 API 配置（Semantic Scholar API Key、限流设置）
  - 日志级别配置（控制台/文件分级）
  - 参考文献验证配置（在线验证、自动替换）
  - 导出格式配置（图片尺寸、字体字号）
- **.openskills.json 更新**：版本号同步至 1.3.0，新增 capabilities 和 scripts

#### 工作流文档完善

| 文档 | 内容 |
|------|------|
| `workflows/step_0_init.md` | Step 0 工作区初始化详细步骤 |
| `workflows/step_3_outline.md` | Step 3 大纲生成补充规范 |
| `workflows/step_4_writing.md` | Step 4 撰写步骤（含摘要生成 4.0 节） |
| `workflows/step_7_merge_detect.md` | Step 7 合并检测（含 `--outline` 参数说明） |
| `workflows/step_8_image.md` | Step 8 图片生成与渲染 |
| `workflows/step_9_export.md` | Step 9 文档导出 |

#### 摘要生成功能

- 新增 Step 4.0 摘要与关键词生成
- 300-500 字中文摘要 + 英文对应
- 3-5 个关键词提取
- 输出 `drafts/摘要.md`

#### 触发语新增

- `生成图片` / `生成图表` / `生成架构图` - 图片生成
- `为第X章配图` - 为指定章节生成图表
- `导出 Word` / `导出文档` - Word + 图片插入
- `一键导出` - 自动生成图片并导出 Word
- `生成摘要` - 仅摘要部分

### 更新功能 (Changed)

- **merge_drafts 增强**：新增 `--outline` 参数，从大纲文件解析章节标题精准匹配文件名，替代硬编码 `chapter_N.md` 模式；增加致谢文件匹配；排除 `参考文献.md` 避免误合并
- **document_exporter 增强**：支持 Word 文档自动插入图片和图注；图片尺寸限制（防排版溢出）；黑体字符转换
- **logger 增强**：日志级别可配置；控制台/文件输出分级；格式化输出优化
- **SKILL.md 重构**：简化核心流程定义，新增 Step 8-9 工作流文档引用
- **prompts/writer_guidelines.md**：新增写作指南补充
- **templates/code_summary_template.md**：新增代码摘要模板

### Bug 修复 (Fixed)

- 修复图片占位符无法正确识别和替换的问题
- 修复图片尺寸过大导致 Word 排版溢出的问题
- 修复日志文件生成路径错误的问题
- 修复黑体字符转换失效的 Bug
- 修复 merge_drafts 章节文件名匹配不准确的问题

### 更新文档

- `README.md` - 新增图片生成/文献搜索功能展示、检测效果截图、触发语更新
- `docs/usage_guide.md` - 同步更新使用说明
- `docs/images/` - 新增朱雀/PaperPass/paperYY 检测效果图

---

## [v1.1.0] - 2026-03-18

### 新增功能 ⭐

#### AIGC 降低策略增强

- **「的」字精简策略**
  - 自动识别并删除冗余「的」字
  - 规则：「重要的意义」→「重要意义」、「精准的构建」→「精准构建」
  - 智能保留过长定语中的「的」维持可读性
  - 专业术语保护（如 Spring 配置不改为 Spring配置）

- **成语替换策略**
  - 新增 `prompts/idiom_replacement_dict.md` 成语替换词典
  - AI 高频表达 → 成语映射：「非常重要」→「举足轻重」「效果显著」→「立竿见影」
  - 学科适配矩阵：理工科极低、社科适中、文学较高

- **特征混淆安全区**
  - 近义词漂移与选词波动
  - 论述密度不均（模拟人类注意力分布）
  - 语法层微瑕疵（长定语不拆分、虚词微冗余）
  - 引用风格波动（模拟分批写作痕迹）

#### 学科适配优化

| 学科类型 | 成语密度 | 特征混淆密度 | 建议 |
|---------|---------|------------|------|
| 计算机/理工科 | 0-2个/章 | 3个/千字 | 仅在绪论、总结使用 |
| 管理/经济学 | 0-1个/节 | 4-5个/千字 | 描述市场趋势时适用 |
| 文学/教育学 | 1-2个/段 | 4-5个/千字 | 自然融入论述 |

#### 触发语新增

- `用成语降重这段文字：…` - 侧重成语替换策略的改写

### 更新文档

- `prompts/humanizer_guidelines.md` - 新增「的」字删除规则、微瑕疵模拟、学科适配
- `prompts/aigc_reducer_prompt.md` - 同步更新核心策略
- `README.md` - 新增效果展示、警告提示、策略一览表

### ⚠️ 重要说明

> 降低检测率的同时，文本可能会**失去部分学术严谨性**。建议将降重视为辅助工具，最终内容需人工审核确保学术质量。

---

## [v1.0.0] - 2026-03-06

### 首次发布

论文创作 Agent 系统首个正式版本发布！

### 新增功能

#### 核心工作流

- **Step 0**: 工作区初始化
  - 自动创建目录结构
  - 生成工作区 README.md
  - 初始化状态记录文件

- **Step 1**: 环境准备
  - 创建 workspace 子目录
  - 扫描并分类参考资料
  - 输出状态报告

- **Step 1.5**: 背景信息讨论 ⭐
  - 支持三轮深入讨论
  - 自动推断论文背景
  - 生成背景确认报告

- **Step 2**: 读取参考资料
  - 模板格式提取
  - 范文风格学习
  - 规范要求提取

- **Step 3**: 论文大纲生成
  - 符合本科论文标准
  - 预估字数分配
  - 图表占位符清单
  - 防错检查（规定动作章节、设计实现分离）

- **Step 4**: 分章节撰写
  - 逐章生成内容
  - 遵循学术写作规范
  - 代码展示优化（≤20行）
  - 防错检查（图表占位符、代码长度、参考文献标记）

- **Step 5**: 降重处理
  - 句式重构（主被动转换、拆分合并）
  - 同义替换（术语白名单保护）
  - 段落重组（逻辑顺序调整）

- **Step 6**: AIGC 人性化
  - 消除模板化过渡词
  - 句长随机波动
  - 添加主观性表达
  - 自检循环（最多 3 轮）

- **Step 7**: 自检输出
  - 格式检查
  - AIGC 检测
  - 合并章节输出终稿
  - 生成检测报告

- **Step 8**: 文档导出 ⭐
  - Word 文档导出
  - PDF 文档导出
  - 支持使用学校模板

#### Python 工具集

| 脚本 | 功能 |
|------|------|
| `aigc_detect.py` | AIGC 检测（轻量版 + 完整版） |
| `aigc_detect_technical.py` | 技术文档专用 AIGC 检测 |
| `synonym_replace.py` | 同义词替换 |
| `enhanced_replace.py` | 增强版同义词替换 |
| `text_analysis.py` | 文本特征分析 |
| `format_checker.py` | 格式检查 |
| `reduce_workflow.py` | 降重工作流 |
| `document_exporter.py` | 文档导出 |
| `md_to_docx.py` | Markdown 转 Word |
| `chart_generator.py` | 图表生成 |
| `reference_validator.py` | 参考文献验证 |

#### 日志系统

- 按时间戳分目录存储日志
- 每步骤独立日志文件
- 警告汇总文件
- 会话总结报告
- `latest` 软链接快速访问

#### 提示词系统

| 文件 | 用途 |
|------|------|
| `thesis_structure.md` | 论文结构模板 |
| `writing_standards.md` | 写作规范 |
| `discussion_guide.md` | 背景信息讨论指南 |
| `writer_guidelines.md` | 论文编写提示词 |
| `reducer_guidelines.md` | 降重提示词 |
| `humanizer_guidelines.md` | AIGC 降低提示词 |

### 防错机制

自动检测并处理以下常见问题：

| # | 问题 | 影响 | 处理方式 |
|---|------|------|----------|
| 1 | 缺少规定动作章节 | 致命 | 自动补充 |
| 2 | 设计与实现未分离 | 致命 | 强制拆分 |
| 3 | 图表严重不足 | 致命 | 提示补充 |
| 4 | 代码堆砌 | 严重 | 拆分精简 |
| 5 | 参考文献虚构 | 严重 | 标记缺失 |
| 6 | 篇幅分配失衡 | 中等 | 提示建议 |

### 单功能模式

支持独立调用特定功能：
- 降重处理
- AIGC 人性化
- AIGC 检测
- 大纲生成
- 文档导出

### 目标指标

| 指标 | 目标值 | 当前表现 |
|------|--------|----------|
| 论文产出速度 | 3000 字 / 30 分钟 | ✅ 达标 |
| 查重率 | ≤ 30% | ✅ 达标 |
| AIGC 检测率 | ≤ 15% | ✅ 达标 |
| 排版合规率 | 符合学校模板 | ✅ 达标 |

---

## 版本说明

### 命名规范

- **主版本号 (Major)**：架构重大变更或不兼容更新
- **次版本号 (Minor)**：新功能添加，向后兼容
- **修订号 (Patch)**：Bug 修复和小改进

### 更新类型标识

- `Added`：新增功能
- `Changed`：功能变更
- `Deprecated`：即将废弃的功能
- `Removed`：已移除的功能
- `Fixed`：Bug 修复
- `Security`：安全相关更新

---

> 最后更新：2026-04-24