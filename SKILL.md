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
| 「降低这段的 AIGC 率：…」 | 仅 Step 6 |
| 「检测这段文字的 AIGC 率」 | AIGC 检测 |
| 「帮我生成论文大纲」 | Step 0-3 |
| 「初始化工作区」 | Step 0 |
| 「继续」 | 继续流程 |
| 「生成图片」「生成图表」 | Step 8 |
| 「导出 Word」「导出文档」 | Step 9 |
| 「一键导出」 | Step 8+9 |

---

## 工作流程概览

```mermaid
flowchart LR
    A[Step 0: 初始化] --> B[Step 1-2: 准备]
    B --> C[Step 3: 大纲]
    C --> D[Step 4: 撰写]
    D --> E[Step 5-6: 降重]
    E --> F[Step 7: 合并检测]
    F --> G[Step 8: 图片生成]
    G --> H[Step 9: 导出Word]
```

> **⚠️ 流程顺序**：合并 → 图片生成 → 导出 Word

---

## 详细步骤（按需加载）

| 步骤 | 说明 | 详细文档 |
|------|------|----------|
| Step 0 | 工作区初始化 | `workflows/step_0_init.md` |
| Step 3 | 生成论文大纲 | `workflows/step_3_outline.md` |
| Step 4 | 分章节撰写 | `workflows/step_4_writing.md` |
| Step 7 | 合并与检测 | `workflows/step_7_merge_detect.md` |
| Step 8 | 图片生成与渲染 | `workflows/step_8_image.md` |
| Step 9 | 文档导出 | `workflows/step_9_export.md` |
| 参考文献 | 文献池管理 | `workflows/reference_workflow.md` |

---

## 参考文献（独立存放）

> **核心改进**：文献池独立存放在 `workspace/verified_references.yaml`

### 流程

1. **Step 3 大纲确认后询问文献数量**（默认 20-30 篇）
2. **多源搜索**：Semantic Scholar + CrossRef + OpenAlex
3. **DOI 验证**：判断 4xx 错误状态码
4. **写作时从文献池选取引用**

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
│   ├── verified_references.yaml  # 文献池（独立）⭐
│   ├── cited_references.json  # 引用记录（每章引用的ref_id）⭐
│   ├── drafts/                # 初稿（仅含临时引用编号，无参考文献列表）⭐
│   ├── final/                 # 终稿
│   │   ├── 论文终稿.md         # 终稿（引用编号已重排）
│   │   ├── 参考文献.md         # 参考文献（独立MD文件，GB/T 7714格式）⭐
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
| **使用 LLM 上下文合并文档** | **致命** | **必须使用 merge_drafts.py 脚本** |
| 图表不足 | 严重 | 提示补充 |
| 参考文献虚构 | 严重 | DOI验证+重生成 |
| 参考文献数量超标 | 严重 | 按相关度截取 |
| AI模板词超标 | 中等 | 自动替换 |
| **章节内自建参考文献列表** | 中等 | 删除，合并阶段统一生成 |

---

## Prompt 文件（写作时加载）

| 文件 | 说明 | 加载时机 |
|------|------|----------|
| `prompts/writer_guidelines.md` | 写作规范 | Step 4 |
| `prompts/aigc_reducer_prompt.md` | AIGC降重 | Step 4 |
| `prompts/reference_citation_prompt.md` | 引用铁律 | Step 4 |
| `workspace/verified_references.yaml` | 文献池 | **必须加载** |

---

## Script 文件

| 文件 | 说明 |
|------|------|
| `scripts/reference_engine.py` | 多源搜索 + DOI验证 |
| `scripts/document_exporter.py` | Word导出 + 图片插入 |
| `scripts/merge_drafts.py` | 章节合并 |
| `scripts/aigc_detect.py` | AIGC检测 |

---

> **详细步骤请查看 `workflows/` 目录下的对应文档**