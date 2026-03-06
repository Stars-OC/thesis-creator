# CODING_PLAN 补充改进建议

> 基于 `claude-scientific-skills` 项目分析 | 2026-03-05
> 本文件为 `CODING_PLAN.md` 的补充，列出可整合的改进项

---

## 改进 1：`writer_guidelines.md` — 整合两阶段写作法 ⭐P0

> 参考来源：`scientific-writing` SKILL.md（Stage 1 → Stage 2 写作流程）

### 背景
`scientific-writing` 的核心方法是「先提纲 → 再成文」，要求 AI **绝不直接输出段落**，而是先列要点、再扩展为段落。此策略可有效：
- 降低 AI 模板化输出倾向
- 增加文本结构多样性
- 便于用户在要点阶段介入调整

### 具体改进内容

在 `prompts/writer_guidelines.md` 中新增以下写作策略：

```markdown
## 两阶段写作法（核心策略）

### Stage 1：段落级要点规划
对每一章节，先生成结构化要点列表：
- 每段的核心论点（1 句话）
- 计划引用的文献（作者+年份）
- 支撑论据（数据/案例/理论）
- 段落间的逻辑衔接关系

**示例输出：**
```
第三章 大数据在精准营销中的应用
├─ § 3.1 用户画像构建
│  ├─ 要点：大数据技术使用户画像从静态标签转向动态行为建模
│  ├─ 引用：张三（2023）用户行为分析框架、李四（2022）画像精度研究
│  ├─ 论据：某电商平台画像准确率提升 27%（具体数据）
│  └─ 衔接：→ 引出 § 3.2 精准推荐
│
├─ § 3.2 精准推荐算法
│  ├─ 要点：协同过滤与深度学习结合提升推荐精度
│  ├─ 引用：王五（2024）混合推荐模型
│  ├─ 论据：A/B 测试点击率提升 15.3%
│  └─ 衔接：→ 过渡至效果评估
```

### Stage 2：要点扩展为段落
将上述要点转为连贯的学术段落，遵循以下规则：
1. **变换句式结构**：禁止连续 3 段使用相同的「总分」结构
2. **句长波动**：目标句长标准差 > 10，模拟人类写作节奏
3. **自然引用**：将引用融入句子中，而非堆砌在段末
4. **段首多样性**：相邻段落首词不得相同
```

### 与 AIGC 降低的协同效果

两阶段写作法天然产生更「人类化」的文本：
- Stage 1 的规划过程引入了结构随机性
- Stage 2 的逐点展开避免了 AI 一次性生成的模板化
- 与现有 Step 6（AIGC 人性化）形成**前后夹击**策略

---

## 改进 2：`format_checker.py` — 增强引用检查 ⭐P0

> 参考来源：`citation-management` 的 `validate_citations.py` 和 `literature-review` 的 `verify_citations.py`

### 背景
当前 `format_checker.py` 仅检查「参考文献章节是否存在且非空」和「`[数字]` 引用标记是否在参考文献中有对应」。可参照 `claude-scientific-skills` 的引用验证逻辑进行增强。

### 新增检查项

```python
# === 引用完整性检查 ===

def check_citation_integrity(text: str, references: list[str]) -> dict:
    """
    检查引文完整性（参考 validate_citations.py）

    检查项：
    1. 正文中 [1][2]... 引用编号是否在参考文献中有对应
    2. 参考文献中的条目是否都有被正文引用（孤立引用检测）
    3. 引用编号是否连续（如有 [1][3] 但缺 [2]）
    4. 每千字引用密度是否达标（≥ 2 个/千字）
    5. 引用分布是否均匀（避免集中在某一章节）
    """
    pass

# === GB/T 7714 格式初步校验 ===

def check_reference_format(ref_line: str) -> dict:
    """
    初步检查参考文献条目是否符合 GB/T 7714 格式

    检查项：
    1. 作者名格式（姓在前，名缩写）
    2. 期刊名是否斜体标注（Markdown 中为 *期刊名*）
    3. 年份、卷号、页码格式
    4. DOI 或 URL 是否存在
    """
    pass
```

### CLI 新增参数

```powershell
# 仅检查引用
python scripts/format_checker.py --input paper.md --check-citations

# 检查引用 + 输出引用分布报告
python scripts/format_checker.py --input paper.md --check-citations --report json

# 输出格式
{
  "total_citations": 28,
  "total_references": 30,
  "orphan_references": [22, 29],
  "missing_references": [],
  "citation_density": 2.3,
  "distribution": {
    "chapter_1": 8,
    "chapter_2": 12,
    "chapter_3": 6,
    "chapter_4": 2
  },
  "format_issues": [
    {"ref_no": 5, "issue": "缺少 DOI 或 URL"},
    {"ref_no": 12, "issue": "年份格式不规范"}
  ]
}
```

---

## 改进 3：Step 7 自检输出 — 增加质量评估报告 ⭐P0

> 参考来源：`peer-review` SKILL.md（7 阶段评审流程 + 结构化反馈）

### 背景
当前 Step 7 仅做 AIGC 检测和格式检查。可参照 `peer-review` 的评审清单，增加论文整体质量评估。

### 新增自检清单

在 SKILL.md Step 7 中新增质量评估环节，输出以下结构化报告：

```markdown
## 论文质量自检报告

### 一、结构完整性
- [x] 标题页完整（题目、作者、专业、指导老师）
- [x] 中英文摘要及关键词
- [x] 目录结构正确
- [ ] ⚠️ 缺少「致谢」章节
- [x] 参考文献列表非空

### 二、引用规范
- 引用总数：28 个
- 引用密度：2.3 个/千字 ✅（≥ 2）
- 孤立引用：[22] [29] ⚠️
- GB/T 7714 格式问题：2 处

### 三、写作质量
- 平均句长：22.4 字 ✅
- 句长标准差：11.2 ✅（> 10）
- 词汇丰富度（TTR）：0.52 ✅（> 0.50）
- 段首多样度：72% ✅（> 70%）
- 过渡词密度：1.8% ✅（< 2%）

### 四、AIGC 检测
- 整体预估：18% ⚠️（阈值 15%）
- 高风险段落：第 2、5、8 段
- 建议：重点改写标记段落

### 五、逻辑连贯性（AI 评估）
- 各章节主题衔接：良好
- 论点与论据匹配：良好
- 结论与前文照应：⚠️ 第 4 章结论部分引入了未在正文讨论的观点
```

### 实现方式
- `format_checker.py` 负责结构和引用检查（自动化）
- `text_analysis.py` 负责写作质量指标（自动化）
- `aigc_detect.py` 负责 AIGC 检测（自动化）
- AI 助手负责逻辑连贯性评估（非脚本，由 SKILL.md 指令引导）

### 输出位置
```
workspace/final/
├── 论文终稿.md
└── quality_report.md    ← 新增：质量自检报告
```

---

## 改进 4：Step 2 参考资料读取 — 结构化文献摘要 ⭐P1

> 参考来源：`literature-review` SKILL.md（Phase 4 数据提取 + Phase 5 主题综合）

### 背景
当前 Step 2 读取参考资料后仅「生成一份参考资料摘要给用户确认」。可参照 `literature-review` 的主题式综合方法，输出更有价值的结构化摘要。

### 改进后的摘要格式

```markdown
## 参考资料分析摘要

### 一、格式模板分析（来自 references/templates/）
- **论文结构要求**：标题 → 摘要 → 目录 → 正文（5章）→ 参考文献 → 致谢
- **字体规范**：正文宋体小四，标题黑体，英文 Times New Roman
- **行距**：正文 1.5 倍行距
- **页边距**：上 2.5cm，下 2.5cm，左 3cm，右 2cm
- **页码**：阿拉伯数字，居中

### 二、优秀范文分析（来自 references/examples/）
- **范文 1**：《xxx》
  - 写作风格：学术正式，多用数据论证
  - 章节分布：引言 10%、文献综述 20%、方法 15%、分析 35%、结论 10%、其它 10%
  - 引用密度：3.1 个/千字
  - 值得借鉴：数据可视化方式、论证逻辑链

### 三、学校规范摘要（来自 references/guidelines/）
- 查重率上限：≤ 30%
- AIGC 率上限：≤ 15%
- 必要章节：摘要（中英文）、关键词、目录、参考文献、致谢
- 参考文献格式：GB/T 7714
- 字数要求：8000-15000 字

### 四、综合建议
- 目标字数分配方案：[基于范文比例自动计算]
- 引用计划：至少 XX 篇参考文献（基于字数和密度要求）
- 重点注意事项：[基于规范提取的硬性要求]
```

---

## 改进 5：CLI 参数规范统一 ⭐P1

> 参考来源：`claude-scientific-skills` 全局脚本设计模式

### 背景
当前 4 个 Python 脚本的 CLI 参数设计已基本合理，但可做进一步统一。

### 统一规范

| 参数 | 用途 | 所有脚本统一使用 |
|------|------|-----------------|
| `--input` / `-i` | 输入文件路径 | ✅ |
| `--output` / `-o` | 输出文件路径 | ✅ |
| `--dir` / `-d` | 输入目录路径 | ✅ |
| `--format` / `-f` | 输出格式（json / table / markdown） | ✅ |
| `--verbose` / `-v` | 详细输出模式 | ✅ 新增 |
| `--quiet` / `-q` | 静默模式（仅输出结果） | ✅ 新增 |
| `--report` | 输出检查/分析报告 | ✅ 新增 |

### 统一输出格式

所有脚本的 JSON 输出统一包含元信息头：

```json
{
  "tool": "aigc_detect",
  "version": "1.0.0",
  "timestamp": "2026-03-05T16:00:00+08:00",
  "input": "workspace/drafts/chapter_01.md",
  "results": { ... }
}
```

---

## 改进 6：文献搜索辅助工具（可选） ⭐P2

> 参考来源：`citation-management` 的 `search_google_scholar.py` + `search_pubmed.py`

### 设计思路

新增 `scripts/search_literature.py`，面向中文学术数据库：

```powershell
# 搜索中文文献（基于 CNKI/万方开放接口或网页抓取）
python scripts/search_literature.py --query "大数据 精准营销" --limit 20

# 搜索 Google Scholar 中文文献
python scripts/search_literature.py --query "大数据 精准营销" --source scholar --lang zh

# 输出 GB/T 7714 格式的参考文献
python scripts/search_literature.py --query "..." --format gbt7714
```

> [!WARNING]
> 中文学术数据库（知网、万方）API 多为付费或受限，此功能为**可选增强**。
> 初版建议仅支持 Google Scholar 中文搜索 + DOI 提取。

---

## 改进 7：论文流程可视化 ⭐P2

> 参考来源：`markdown-mermaid-writing` SKILL.md

### 设计思路

在 SKILL.md 和 `writer_guidelines.md` 中使用 Mermaid 生成论文技术路线图，作为论文中的图表素材：

```markdown
### 技术路线图生成示例

当论文需要技术路线图时，AI 可自动生成 Mermaid 图：

​```mermaid
graph TD
    A[研究问题提出] --> B[文献调研]
    B --> C[理论框架构建]
    C --> D[数据收集]
    D --> E[数据分析]
    E --> F[结果讨论]
    F --> G[结论与建议]

    style A fill:#4ECDC4,stroke:#333
    style G fill:#FF6B6B,stroke:#333
​```
```

AI 可根据论文主题自动生成适配的技术路线图，减少用户手动绘图工作。

---

## 实施优先级与关联

| 改进项 | 优先级 | 实施阶段 | 关联模块 | 状态 |
|--------|--------|----------|----------|------|
| 1. 两阶段写作法 | P0 | Phase 3（提示词） | `prompts/writer_guidelines.md` | ✅ 已完成 |
| 2. 引用检查增强 | P0 | Phase 4a（Python 脚本） | `scripts/format_checker.py` | ✅ 已完成 |
| 3. 质量评估报告 | P0 | Phase 4a + Phase 6（集成） | `scripts/*` + SKILL.md Step 7 | ✅ 已完成 |
| 4. 结构化文献摘要 | P1 | Phase 3（提示词） | SKILL.md Step 2 | ✅ 已完成 |
| 5. CLI 参数统一 | P1 | Phase 4a/4b（Python 脚本） | `scripts/*.py` | ✅ 已完成 |
| 6. 文献搜索辅助 | P2 | 额外 Phase | `scripts/search_literature.py`（新） | ⬜ 待实施 |
| 7. Mermaid 流程图 | P2 | Phase 3（提示词） | `prompts/writer_guidelines.md` | ⬜ 待实施 |

---

## 实施记录（2026-03-05）

### 已完成的改进

#### 改进 1：两阶段写作法 ✅
- 在 `prompts/writer_guidelines.md` 中新增「两阶段写作法（核心策略）」章节
- 包含 Stage 1（段落级要点规划）和 Stage 2（要点扩展为段落）
- 提供了详细的示例输出和与 AIGC 降低的协同效果说明

#### 改进 2：引用检查增强 ✅
- 在 `scripts/format_checker.py` 中新增 `check_citation_integrity()` 方法
- 实现引用完整性检查、孤立引用检测、引用密度计算、引用分布分析
- 新增 `check_reference_format()` 方法进行 GB/T 7714 格式初步校验
- 新增 `--check-citations` CLI 参数

#### 改进 3：质量评估报告 ✅
- 在 SKILL.md Step 7 中新增详细的质量评估报告格式
- 包含结构完整性、引用规范、写作质量、AIGC 检测、逻辑连贯性五大维度
- 输出 `workspace/final/quality_report.md` 文件

#### 改进 4：结构化文献摘要 ✅
- 在 SKILL.md Step 2 中新增结构化的「参考资料分析摘要」格式
- 包含格式模板分析、范文分析、学校规范摘要、综合建议四个部分

#### 改进 5：CLI 参数统一 ✅
- 统一所有 Python 脚本的 CLI 参数设计
- 新增 `--verbose/-v`、`--quiet/-q`、`--report/-r` 参数
- 统一 JSON 输出格式（包含 tool、version、timestamp、input、results 元信息）
- 已更新：`aigc_detect.py`、`format_checker.py`、`synonym_replace.py`、`text_analysis.py`

### 待实施的改进（P2）

#### 改进 6：文献搜索辅助工具
- 需新增 `scripts/search_literature.py`
- 面向中文学术数据库的文献搜索

#### 改进 7：论文流程可视化
- 在 `prompts/writer_guidelines.md` 中新增 Mermaid 流程图生成能力
