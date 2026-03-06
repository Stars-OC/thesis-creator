# 论文创作 Agent 系统 — Coding Plan（方案 B：Skill + Python 混合）

> **产品需求文档（PRD）** | 版本 v4 | 2026-03-05

---

## 一、产品概述

### 1.1 产品定位

面向中国本科生的**毕业论文全流程写作辅助系统**。采用 Claude Code Skill 作为主控编排层，Python 脚本作为辅助工具层，实现从选题到交稿的端到端工作流。

### 1.2 目标用户

中国本科生，需要完成毕业论文且希望借助大模型提升写作效率的群体。

### 1.3 核心痛点

| 痛点 | 描述 |
|------|------|
| **写作效率低** | 毕业论文通常 1-3 万字，从零撰写耗时数周 |
| **查重率过高** | AI 生成文本往往有固定模式，查重系统容易匹配 |
| **AIGC 检测风险** | 各高校已引入 AIGC 检测（知网/维普），AI率 > 15-30% 可能被退回 |

### 1.4 产品目标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 论文产出速度 | 3000 字/30 分钟（含人工审核时间） | 以 AI 返回完成到用户确认的端到端时间计量 |
| 查重率 | ≤ 学校要求上限（通常 ≤ 30%） | 最终提交前使用知网/维普/PaperPass 在线查重验证 |
| AIGC 检测率 | ≤ 15%（可配置阈值） | 本地 `aigc_detect.py` 预估（准确率 ~70-80%），正式提交前以知网/维普 AIGC 检测为准 |
| 排版合规率 | 符合用户提供的学校模板格式 | 使用 `format_checker.py` 检查 Markdown 结构，最终通过 pandoc 转 Word 后人工对照模板 |

---

## 二、系统架构

### 2.1 架构选型：方案 B（Skill + Python 混合）

```
┌──────────────────────────────────────────────────────┐
│                   用户 ↔ AI 助手                       │
│              (Claude Code / Gemini 等)                 │
└───────────────────────┬──────────────────────────────┘
                        │ 触发
┌───────────────────────▼──────────────────────────────┐
│                  SKILL.md（主控编排层）                  │
│                                                       │
│  Step 1~7 全流程指令 ──→ prompts/ 详细提示词           │
│                          ↕                            │
│                    references/ 参考资料                │
└───────────────────────┬──────────────────────────────┘
                        │ 调用
┌───────────────────────▼──────────────────────────────┐
│               scripts/（Python 工具层）                │
│                                                       │
│  aigc_detect.py    → 困惑度/突发性本地检测             │
│  synonym_replace.py → jieba 分词 + 同义词替换          │
│  text_analysis.py  → 句长统计、词汇多样性分析           │
│  format_checker.py → 格式规范校验                      │
└──────────────────────────────────────────────────────┘
                        │ 输出
┌───────────────────────▼──────────────────────────────┐
│               workspace/（论文产出工作区）              │
│                                                       │
│  outline.md → drafts/ → reduced/ → final/             │
└──────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 主控编排 | SKILL.md + prompts/ | Claude Code Skill 格式，纯 Markdown 指令 |
| LLM 调用 | AI 助手原生能力 | 无需额外 API 配置，由宿主 AI 直接调用 |
| 文本处理 | Python 3.9+ | `jieba`（分词）+ `synonyms`（同义词） |
| AIGC 检测 | Python（纯统计） | 默认轻量版：突发性 + 词汇多样性 + 过渡词密度 + 句式模式（~50 MB）；可选升级中文 GPT-2 困惑度分析 |
| 文件格式 | Markdown (`.md`) | 全流程使用 Markdown，便于 AI 读写 |
| 格式转换 | pandoc | Markdown → Word（`.docx`）转换，支持应用自定义模板 |

---

## 三、项目目录结构

```
e:\AIAgent\thesis-creator\
│
├── SKILL.md                         # 📋 主 Skill：全流程 7 步编排指令
├── .openskills.json                 # 📋 Skill 元数据
├── CODING_PLAN.md                   # 📋 本文件（PRD）
├── README.md                        # 📋 项目说明
│
├── references/                      # 📁 参考资料（用户手动存放）
│   ├── templates/                   #   论文格式模板
│   │   └── README.md                #   存放说明
│   ├── examples/                    #   优秀范文
│   │   └── README.md                #   存放说明
│   └── guidelines/                  #   学校写作规范
│       └── README.md                #   存放说明
│
├── prompts/                         # 📝 各阶段提示词指南
│   ├── writer_guidelines.md         #   论文编写提示词
│   ├── reducer_guidelines.md        #   降重提示词
│   └── humanizer_guidelines.md      #   AIGC 降低提示词
│
├── scripts/                         # 🐍 Python 辅助脚本
│   ├── requirements.txt             #   依赖声明
│   ├── install.ps1                  #   Windows 一键安装脚本
│   ├── aigc_detect.py               #   AIGC 检测（困惑度+突发性）
│   ├── synonym_replace.py           #   中文同义词替换
│   ├── text_analysis.py             #   文本特征分析
│   ├── format_checker.py            #   格式规范校验
│   └── term_whitelist.txt           #   术语保护白名单（用户可自定义）
│
├── workspace/                       # 📂 工作区（运行时自动创建）
│   ├── outline.md                   #   论文大纲
│   ├── drafts/                      #   各章节初稿
│   ├── reduced/                     #   降重后版本
│   ├── history/                     #   历史版本（各轮改写的备份）
│   └── final/                       #   最终成稿
│
└── docs/
    └── usage_guide.md               # 📖 使用说明
```

---

## 四、功能详细规格

### 4.1 参考资料管理（`references/`）

#### 功能描述
提供一个结构化目录供用户存放论文相关参考资料，Skill 在编写前自动读取。

#### 子目录详述

| 子目录 | 用途 | 输入格式 | AI 处理方式 |
|--------|------|----------|-------------|
| `templates/` | 论文格式模板 | `.docx` `.pdf` `.jpg` `.png` | 提取格式规范（标题层级、字体、行距等） |
| `examples/` | 优秀范文 | `.docx` `.pdf` | 分析写作风格、论证结构、引用方式 |
| `guidelines/` | 学校规范 | `.docx` `.pdf` `.jpg` `.png` | 提取查重率/AIGC率上限、格式硬性要求 |

#### 行为规则
- 若 `references/` 为空 → 提醒用户先放入资料，可继续但给出 warning
- 若包含 PDF/Word → AI 尝试读取文本内容
- 若包含图片 → AI 尝试视觉识别关键信息
- 读取完成后 → 生成一份「参考资料摘要」给用户确认

---

### 4.2 论文编写 Agent（Step 3 + Step 4）

#### 功能描述
根据主题和大纲，分章节生成符合学术规范的论文内容。

#### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | string | ✅ | 论文主题 |
| `major` | string | ✅ | 专业方向 |
| `word_count` | int | ❌ | 目标总字数（默认 10000） |
| `outline` | file | ❌ | 用户自定义大纲文件路径 |

#### 输出
- `workspace/outline.md` — 完整论文大纲
- `workspace/drafts/chapter_XX_章节名.md` — 各章节初稿

#### 编写规则（详细版）
1. **大纲结构**：标题 → 摘要（中英文）→ 关键词 → 引言 → 文献综述 → 正文章节（2-4章）→ 结论 → 参考文献 → 致谢
2. **段落要求**：每段 150-300 字，包含论点+论据+小结
3. **引用规范**：每千字至少 2 个文献引用，格式 GB/T 7714
4. **语体要求**：学术正式语体，但避免以下 AI 特征词汇：
   - 禁用：「此外」「值得注意的是」「不可否认」「综上所述」
   - 推荐：「研究表明」「据统计分析」「笔者认为」「从实证角度来看」
5. **结构多样性**：避免每段都是「总分」结构，穿插归纳法/演绎法/对比法

---

### 4.3 论文降重 Agent（Step 5）

#### 功能描述
对初稿进行语义不变的深度改写，降低文本相似度。

#### 降重策略矩阵

| 策略 | 操作 | 示例 | 预估降重效果 |
|------|------|------|-------------|
| 句式重构 | 主被动转换 | 「本文采用了…」→「…被本研究所采用」 | 高 |
| 句式重构 | 长句拆短句 | 拆分复合句为 2-3 个短句 | 中 |
| 句式重构 | 短句合长句 | 合并相邻短句为带从句的长句 | 中 |
| 同义替换 | 词汇级替换 | 「显著」→「明显」→「突出」 | 中 |
| 同义替换 | 短语级替换 | 「起到了重要作用」→「发挥了关键效能」 | 中 |
| 段落重组 | 逻辑顺序调整 | 将「原因→结果」改为「结果→原因」 | 高 |
| 数据增强 | 具象化 | 「显著提升」→「提升了 23.7%」 | 低 |
| 引用编织 | 添加引用 | 在论点处补充「根据张三（2023）的研究…」 | 中 |

#### Python 辅助（`synonym_replace.py`）

```
输入：一段中文文本
处理：jieba 分词 → 识别可替换词 → synonyms 库查询 → 生成候选替换方案
输出：替换后文本 + 替换日志（记录每处替换）
```

**术语保护机制**：内置术语白名单，专业术语不替换：
- 用户可自定义白名单文件 `scripts/term_whitelist.txt`
- 每行一个术语，如：`深度学习`、`卷积神经网络`、`供应链管理`

---

### 4.4 AIGC 降低 Agent（Step 6）

#### 功能描述
模拟人类写作特征，降低 AIGC 检测系统的识别概率。

#### AIGC 特征消除策略

| AI 特征 | 消除方法 | 优先级 |
|---------|----------|--------|
| **过渡词模板化** | 消除「首先/其次/最后/此外/综上」，改为自然过渡 | P0 |
| **句长均匀** | AI 通常每句 20-30 字很均匀，改为 10-50 字随机波动 | P0 |
| **段落结构整齐** | AI 偏好总分总，改为多种结构交替 | P0 |
| **缺乏主观性** | 添加「笔者」「据观察」「值得思考的是」 | P1 |
| **逻辑过于完美** | 适度添加转折、让步、质疑等 | P1 |
| **用词偏好** | AI 高频使用「旨在」「致力于」「具有重要意义」，替换为低频表达 | P1 |
| **每段首句同质** | 避免每段都以「XX是…」开头 | P2 |
| **标点规律** | AI 很少用分号、破折号，适度添加 | P2 |

#### 自检循环

```
降重后文稿 → AIGC 检测 → 检测率 ≤ 阈值? → 是 → 通过
                                          → 否 → 标记高风险段 → 再次改写（最多 3 轮）
```

---

### 4.5 AIGC 本地检测（`aigc_detect.py`）

#### 功能描述
基于文本统计特征的本地 AIGC 检测工具，提供快速预估。采用**双模式设计**：

| 模式 | 依赖大小 | 检测维度 | 预估准确率 | 适用场景 |
|------|---------|---------|-----------|----------|
| **方案 A（默认）** | ~50 MB | 4 个纯统计维度 | ~55-65% | 快速预估，轻量部署 |
| **方案 B（可选升级）** | ~2.5 GB | 4 统计 + 困惑度 | ~70-80% | 更高精度需求 |

#### 方案 A：轻量版检测维度（默认）

| 维度 | 方法 | 权重 |
|------|------|------|
| **突发性（Burstiness）** | 分析句长方差，AI 文本句长方差小（均匀） | 35% |
| **词汇多样性** | TTR（Type-Token Ratio），AI 文本词汇重复率偏高 | 25% |
| **过渡词密度** | 统计 AI 高频过渡词的出现密度 | 20% |
| **句式模式** | 检测「总分总」等 AI 偏好结构出现频率 | 20% |

#### 方案 B：完整版检测维度（可选升级）

在方案 A 的基础上增加**困惑度（Perplexity）**维度，使用中文 GPT-2 模型（`uer/gpt2-chinese-cluecorpussmall`）计算。

| 维度 | 方法 | 权重 |
|------|------|------|
| **困惑度（Perplexity）** | 使用中文 GPT-2 模型计算文本困惑度，AI 文本困惑度通常较低 | 40% |
| **突发性（Burstiness）** | 分析句长方差 | 25% |
| **词汇多样性** | TTR | 15% |
| **过渡词密度** | 统计 AI 高频过渡词密度 | 10% |
| **句式模式** | 检测 AI 偏好结构频率 | 10% |

> [!TIP]
> 方案 B 需额外安装 `transformers` + `torch`（~2.5 GB）。首次运行时自动下载中文 GPT-2 模型（~500 MB）。
> 升级方式：`pip install transformers torch`，脚本会自动检测并启用困惑度维度。

#### 输出格式

```json
{
  "mode": "lite",
  "overall_score": 26.0,
  "burstiness": { "score": 18.0, "detail": "句长方差 12.3，低于人类典型值 35+" },
  "vocabulary": { "score": 22.0, "detail": "TTR = 0.41，略低于人类典型值 0.55+" },
  "transition": { "score": 30.0, "detail": "高频过渡词密度 4.2%，高于人类典型值 2%" },
  "structure":  { "score": 20.0, "detail": "总分总结构占比 60%" },
  "high_risk_paragraphs": [2, 5, 8],
  "suggestion": "建议重点改写第 2、5、8 段"
}
```

#### CLI 接口

```powershell
# 检测单个文件
python scripts/aigc_detect.py --input workspace/drafts/chapter_01.md

# 检测一段文本
python scripts/aigc_detect.py --text "待检测的文本内容..."

# 检测整个目录
python scripts/aigc_detect.py --dir workspace/reduced/

# 指定输出格式
python scripts/aigc_detect.py --input paper.md --format json
python scripts/aigc_detect.py --input paper.md --format table

# 启用方案 B（需已安装 transformers + torch）
python scripts/aigc_detect.py --input paper.md --mode full
```

> ⚠️ 本地检测为近似估计（方案 A 准确率 ~55-65%，方案 B ~70-80%）。正式提交前建议到知网/维普做正式检测。

---

### 4.6 文本分析工具（`text_analysis.py`）

#### 功能描述
分析文本的统计特征，帮助用户了解文本「像 AI」的程度。

#### 分析指标

| 指标 | 说明 | 人类典型值 | AI 典型值 |
|------|------|-----------|----------|
| 平均句长 | 每句平均字数 | 15-35字（波动大） | 20-30字（稳定） |
| 句长标准差 | 句长波动程度 | > 10 | < 7 |
| 词汇丰富度（TTR） | 不重复词/总词数 | > 0.50 | < 0.45 |
| 过渡词密度 | 过渡词占总词数比例 | < 2% | > 3% |
| 段落首词多样度 | 段首第一个词的去重率 | > 70% | < 50% |

#### CLI 接口

```powershell
python scripts/text_analysis.py --input paper.md
python scripts/text_analysis.py --compare before.md after.md
```

---

### 4.7 同义词替换工具（`synonym_replace.py`）

#### 功能描述
基于 jieba 分词和 synonyms 库，自动替换文本中的非术语词汇。

#### 处理流程

```
原始文本
  ↓ jieba 分词
词语列表 [w1, w2, w3, ...]
  ↓ 过滤（排除术语白名单、停用词、单字词）
可替换词列表 [w2, w5, w8, ...]
  ↓ synonyms 查询同义词
替换候选 {w2: [s1,s2], w5: [s3], w8: [s4,s5]}
  ↓ 按替换比例随机选取（默认 30%）
替换后文本
```

#### CLI 接口

```powershell
# 基本替换
python scripts/synonym_replace.py --input paper.md --output paper_replaced.md

# 自定义替换比例
python scripts/synonym_replace.py --input paper.md --ratio 0.4

# 指定术语白名单
python scripts/synonym_replace.py --input paper.md --whitelist scripts/term_whitelist.txt
```

---

### 4.8 格式检查工具（`format_checker.py`）

#### 功能描述
检查论文 Markdown 文件的结构规范性。在 Step 7（自检与输出）中被调用。

#### 检查项

| 检查项 | 规则 |
|--------|------|
| 标题层级 | 必须从 `#` 开始，层级不跳级 |
| 摘要 | 必须包含中英文摘要和关键词 |
| 参考文献 | 必须存在「参考文献」章节且非空 |
| 引用格式 | 检查 `[数字]` 引用标记是否在参考文献中有对应 |
| 字数统计 | 报告各章节字数和总字数 |
| 章节完整性 | 检查必要章节（引言/文献综述/结论）是否存在 |

#### CLI 接口

```powershell
# 检查单个文件
python scripts/format_checker.py --input workspace/final/论文终稿.md

# 检查多个章节
python scripts/format_checker.py --dir workspace/drafts/
```

---

## 五、全流程交互设计

### 5.1 全流程模式

```
用户："帮我写论文，主题是《大数据在精准营销中的应用研究》"
  │
  ├─ Step 1：创建 workspace/，检查 references/
  │   └─ AI 回复："工作区已创建。检测到 references/ 中有 2 个模板和 1 份范文。"
  │
  ├─ Step 2：读取参考资料
  │   └─ AI 回复："已读取格式模板，论文要求：一级标题宋体小二号加粗..."
  │
  ├─ Step 3：生成大纲
  │   └─ AI 回复："大纲已生成，请审核...[展示大纲]...确认后我开始撰写。"
  │   └─ 用户："第三章再加一节关于隐私保护的内容"
  │   └─ AI 修改大纲并保存
  │
  ├─ Step 4：分章节撰写
  │   └─ AI 逐章写作，每章完成后通知
  │
  ├─ Step 5：降重处理
  │   └─ AI 对每章执行降重，可调用 Python 脚本辅助
  │
  ├─ Step 6：AIGC 人性化
  │   └─ AI 对降重稿执行人性化改写
  │
  └─ Step 7：自检输出
      ├─ 调用 aigc_detect.py 检测
      ├─ 若通过 → 合并输出终稿
      └─ 若未通过 → 标记并回到 Step 6
      └─ 若 3 轮后仍未通过 → 输出当前最佳版本 + 高风险段标记，建议用户手动调整
```

### 5.2 单功能模式

| 触发语 | 执行动作 |
|--------|----------|
| 「帮我降重这段文字：…」 | 仅 Step 5 |
| 「降低这段的 AIGC 率：…」 | 仅 Step 6 |
| 「检测这段文字的 AIGC 率」 | 仅调用 `aigc_detect.py` |
| 「帮我生成论文大纲」 | Step 1-3 |
| 「分析这段文字的特征」 | 仅调用 `text_analysis.py` |
| 「检查论文格式」 | 仅调用 `format_checker.py` |

---

## 六、Python 脚本依赖（`scripts/requirements.txt`）

### 默认依赖（方案 A，轻量版）

```
jieba>=0.42.1               # 中文分词
synonyms>=3.18.0             # 中文同义词
rich>=13.0.0                 # 命令行美化输出
click>=8.1.0                 # CLI 参数解析
```

> 总大小约 **50 MB**，安装时间 < 1 分钟。

### 可选升级依赖（方案 B，完整版）

在默认依赖基础上，额外安装以下包以启用困惑度检测：

```
transformers>=4.30.0         # 中文 GPT-2 困惑度计算
torch>=2.0.0                 # PyTorch（CPU 版即可）
```

> [!WARNING]
> `transformers` + `torch` 额外占用约 **2.5 GB** 磁盘空间。仅在需要更高检测精度时安装。

#### Windows 安装说明

```powershell
# 1. 推荐使用虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. 安装默认依赖（方案 A）
pip install -r scripts/requirements.txt

# 3.（可选）升级到方案 B：安装 PyTorch CPU 版 + transformers
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers>=4.30.0
```

> [!TIP]
> 安装方案 B 后，`aigc_detect.py` 会自动检测 `transformers` 是否可用，若可用则自动启用困惑度维度。
> 中文 GPT-2 模型首次运行时自动下载（~500 MB），如无法访问 HuggingFace，可手动下载模型到本地。

---

## 七、实施计划

| 阶段 | 内容 | 产出文件 | 预估 | 状态 |
|------|------|----------|------|------|
| **Phase 1** | 目录结构 + references/ README + README.md | 目录和 README | — | ✅ 已完成 |
| **Phase 2** | SKILL.md + .openskills.json | `SKILL.md`、`.openskills.json` | — | ✅ 已完成 |
| **Phase 3** | 三份提示词指南 | `prompts/*.md`（3 个文件） | ~45 min | ✅ 已完成 |
| **Phase 4a** | 轻量 Python 脚本 | `synonym_replace.py`、`text_analysis.py`、`format_checker.py` | ~60 min | ✅ 已完成 |
| **Phase 4b** | AIGC 检测脚本（默认轻量版 + 可选 GPT-2） | `aigc_detect.py`（双模式） | ~90 min | ✅ 已完成 |
| **Phase 5** | 使用文档 + 安装脚本 | `docs/usage_guide.md`、`scripts/install.ps1` | ~20 min | ✅ 已完成 |
| **Phase 6** | 集成验证 + SKILL.md 同步更新 | 测试报告 | ~45 min | 🔄 进行中 |

---

## 八、验证方案

### 8.1 结构验证
- [x] 所有文件按目录结构创建完毕
- [x] SKILL.md 可被 AI 助手正确触发和读取
- [ ] Python 脚本 `pip install -r requirements.txt` 无报错

### 8.2 功能验证
- [ ] `aigc_detect.py` 对已知 AI 文本检测分数 > 50%
- [ ] `aigc_detect.py` 对已知人类文本检测分数 < 30%
- [ ] `synonym_replace.py` 替换后文本语义通顺
- [ ] `text_analysis.py` 输出各项指标正确
- [ ] `format_checker.py` 能检出缺少章节等问题

### 8.3 端到端验证
- [ ] 全流程生成 3000 字短论文，人工检查质量
- [ ] 降重前后用在线查重工具对比重复率
- [ ] 最终产出到 AIGC 检测平台验证 ≤ 15%

---

## 九、错误处理与边界情况

| 场景 | 处理策略 |
|------|----------|
| GPT-2 模型下载失败（方案 B） | 自动回退到方案 A（轻量版 4 维度检测），提示用户困惑度维度不可用 |
| PDF/Word 文件无法解析（加密/扫描版） | 提示用户手动提取关键信息到 `.txt`，或提供截图由 AI 视觉识别 |
| 论文字数过长导致处理缓慢 | 按章节分块处理，每块 ≤ 3000 字，避免一次性加载 |
| 3 轮 AIGC 改写后仍未达标 | 输出当前最佳版本 + 高风险段落标记，建议用户手动修改这些段落 |
| `synonyms` 库无合适同义词 | 保留原词不替换，在替换日志中标记「无可用同义词」 |
| `workspace/` 已存在旧数据 | 提示用户选择：覆盖 / 备份后覆盖 / 新建带时间戳的子目录 |
| Python 环境未配置 | 提供 `scripts/install.ps1` 一键安装脚本，或输出手动安装指引 |

---

## 十、版本控制策略

为防止多轮改写导致数据丢失，采用以下策略：

1. **自动备份**：每次进入 Step 5（降重）和 Step 6（AIGC 人性化）前，将当前文件复制到 `workspace/history/`
2. **命名规则**：`workspace/history/chapter_XX_v{轮次}_{时间戳}.md`
   - 示例：`chapter_01_v1_20260305_1430.md`
3. **保留策略**：默认保留最近 5 个版本，旧版本可手动清理
4. **回滚方式**：用户可指定从 `workspace/history/` 中恢复某个版本到 `workspace/reduced/`

---

## 十一、Markdown → Word 格式转换

最终论文需要以 `.docx` 格式提交，提供以下转换方案：

```powershell
# 基本转换
pandoc workspace/final/论文终稿.md -o workspace/final/论文终稿.docx

# 使用自定义 Word 模板（推荐）
pandoc workspace/final/论文终稿.md --reference-doc=references/templates/模板.docx -o workspace/final/论文终稿.docx
```

> [!NOTE]
> pandoc 安装：`winget install pandoc` 或从 [pandoc.org](https://pandoc.org/installing.html) 下载安装。
> 若学校模板格式复杂（如封面页、页眉页脚），建议导出后在 Word 中手动微调。

---

