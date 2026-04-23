# 参考文献引用生成 Prompt

> **核心目标**：消除 AI 幻觉，确保所有引用来自已验证的真实文献池

---

## ⚠️ 引用生成铁律（ABSOLUTE RULES）

> **以下规则为硬性约束，违反即为严重错误！**

### 规则 1：禁止编造任何文献

**所有引用必须来自 `workspace/verified_references.yaml` 文献池**。

```
❌ 错误做法：
[1] 张三, 李四. 大数据技术研究[J]. 管理科学学报, 2023, 26(3): 45-52.
（如果这条文献不在 verified_references.yaml 中，禁止使用）

✅ 正确做法：
从文献池中选取已验证的文献：
- 加载 verified_references.yaml
- 检索匹配关键词
- 选取相关度最高的文献
- 格式化为 GB/T 7714
```

### 规则 2：文献池不足时的处理

如果文献池中没有合适的文献：

```
❌ 错误做法：自行编造一个"看起来合理"的文献

✅ 正确做法：
在段落末尾标注：
「⚠️ [需搜索补充] 关于XX主题的文献不足，建议搜索补充」

然后触发文献搜索：
python scripts/reference_engine.py --query "XX主题关键词" --limit 10
```

### 规则 3：每条引用必须包含 DOI 链接

所有文献引用必须包含可点击的 DOI 链接：

```
✅ 正确格式：
[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//NAACL 2020. 2020. [DOI](https://doi.org/10.18653/v1/2020.naacl-main.13)

❌ 错误格式（缺少DOI链接）：
[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//NAACL 2020. 2020.
```

### 规则 4：中文文献无 DOI 时的处理

中文文献如无 DOI，必须标注「需用户确认」：

```
[1] 张三, 李四. 某中文期刊论文[J]. 中文期刊, 2022, 15(3): 45-52. ⚠️ 需用户确认

（后续需用户手动核实或从CNKI补充DOI）
```

---

## 引用匹配流程

### Step 1：分析段落核心主题

```
输入段落 → 提取关键词 → 确定引用需求

示例：
输入：「RAG技术通过检索外部知识库增强语言模型的生成能力...」
提取关键词：["RAG", "知识库", "检索增强", "语言模型"]
```

### Step 2：检索文献池

```
调用文献池管理器：
python scripts/verified_reference_pool.py --recommend --keywords "RAG 知识库 检索" --limit 5

返回结果：
- ref_001: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- ref_002: "Neural Retrieval for Question Answering"
- ref_003: "Dense Passage Retrieval for Open-Domain Question Answering"
```

### Step 3：选择最相关文献

```
选择标准：
1. 关键词匹配度高
2. 引用次数多（权威性）
3. 年份较新（时效性）
4. 已验证DOI（可靠性）
```

### Step 4：插入引用标注

```
在段落合适位置插入引用标注 [序号]：

示例：
「RAG技术通过检索外部知识库增强语言模型的生成能力[1]，该技术由Lewis等人于2020年提出[2]，已成为知识密集型任务的主流方案...」
```

### Step 5：生成参考文献列表

```
在段落末尾附上完整引用信息：

### 参考文献
[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//NAACL 2020. 2020. [DOI](https://doi.org/10.18653/v1/2020.naacl-main.13)
[2] ...
```

---

## 输出格式规范

### 引用后完整段落

```
（段落正文，含 [1][2] 等引用标注）

例如：
RAG技术通过检索外部知识库增强语言模型的生成能力[1]。该技术的核心思想是将检索与生成相结合，在回答问题前先从大规模文档库中检索相关片段，然后将检索结果作为上下文提供给语言模型[2]。实验表明，RAG在知识密集型任务上显著优于纯生成模型，尤其在需要精确事实的任务中表现突出[3]。
```

### 参考文献列表

```
### 参考文献

[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//NAACL. 2020. [DOI](https://doi.org/10.18653/v1/2020.naacl-main.13)

[2] Karpukhin V, Oguz B, Min S, et al. Dense Passage Retrieval for Open-Domain Question Answering[C]//EMNLP. 2020. [DOI](https://doi.org/10.18653/v1/2020.emnlp-main.346)

[3] Guu K, Lee K, Tung Z, et al. Retrieval Augmented Language Model Pre-Training[C]//ICML. 2020. [DOI](https://doi.org/10.48550/arXiv.2002.08909)
```

---

## 引用频率要求

| 段落类型 | 引用要求 | 说明 |
|----------|----------|------|
| 理论阐述 | 每段 1-2 条 | 需引用原始论文或权威综述 |
| 方法描述 | 每段 2-3 条 | 需引用相关方法论文 |
| 数据分析 | 每段 1-2 条 | 可引用数据来源或分析方法 |
| 结论总结 | 每段 1 条 | 可引用支撑研究或对比研究 |

**最低要求**：每千字至少 2 个文献引用

---

## 常见问题处理

### Q1：文献池中没有相关文献怎么办？

```
答：
1. 在段落末尾标注「⚠️ [需搜索补充]」
2. 触发搜索命令：
   python scripts/reference_engine.py --query "<段落关键词>" --limit 10
3. 将搜索结果添加到文献池
4. 重新生成引用
```

### Q2：同一文献被多次引用怎么办？

```
答：
同一文献最多引用 3 次（避免过度引用）。如需多次引用同一文献：
- 在不同段落中使用不同引用角度
- 或标注「详见上文引用[1]」
```

### Q3：中文文献如何处理？

```
答：
中文文献处理规则：
1. 优先使用已有 DOI 的中文文献
2. 无 DOI 的中文文献标注「⚠️ 需用户确认」
3. 建议用户从 CNKI 补充 DOI 或手动核实
```

### Q4：如何验证引用是否正确？

```
答：
每章完成后运行快速验证：
python scripts/reference_validator.py <章节文件> --validate-online

检查：
- DOI 链接是否可点击
- 文献是否在文献池中
- 格式是否符合 GB/T 7714
```

---

## 文献池管理命令速查

```bash
# 初始化文献池
python scripts/verified_reference_pool.py --init --chapter "第四章"

# 批量添加文献
python scripts/verified_reference_pool.py --add --file search_results.yaml --chapter "第四章"

# 推荐文献
python scripts/verified_reference_pool.py --recommend --keywords "RAG 知识库" --limit 5

# 导出参考文献
python scripts/verified_reference_pool.py --export --format gbt7714 --chapter "第四章"

# 显示统计
python scripts/verified_reference_pool.py --stats
```

---

## 禁止行为清单

| 序号 | 禁止行为 | 说明 |
|------|----------|------|
| 1 | 编造论文标题 | ❌ 绝对禁止虚构标题 |
| 2 | 编造作者姓名 | ❌ 禁止使用「张三」「李四」等占位符 |
| 3 | 编造期刊名称 | ❌ 禁止虚构期刊或会议名 |
| 4 | 编造 DOI | ❌ 禁止生成虚假 DOI 号 |
| 5 | 使用未验证文献 | ❌ 必须来自 verified_references.yaml |
| 6 | 缺少 DOI 链接 | ❌ 每条引用必须有可点击 DOI |
| 7 | 过度引用同一文献 | ❌ 同一文献最多引用 3 次 |

---

> **最后提醒**：引用真实性是学术论文的生命线。宁可标注「需搜索补充」，也绝不编造文献！