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
    C --> D[Step 4: 撰写]
    D --> E[Step 5-6: 降重]
    E --> F[Step 7: 合并检测]
    F --> G[Step 8: 图片生成]
    G --> H[Step 9: 导出Word]
```

> **⚠️ 流程顺序**：合并 → 图片生成 → 导出 Word
> 状态文件路径：`thesis-workspace/.thesis-status.json`
> 若文件不存在，`status_manager.py` 会自动创建。
>
> **推荐统一入口**：`scripts/lifecycle.py`（整合日志 + 状态管理）

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

> **核心改进**：文献池独立存放在 `workspace/references/verified_references.yaml`

### 流程

1. **Step 3 大纲确认后询问文献数量**（默认 20-30 篇）
2. **多源搜索**：Semantic Scholar + CrossRef + OpenAlex
3. **DOI 验证**：判断 4xx 错误状态码
4. **合并去重**：多源结果合并，按相关度选出最相关 x 篇（`scripts/reference_merger.py`）
5. **写作时从文献池选取引用**

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
| AI模板词超标 | 中等 | 自动替换 |
| **章节内自建参考文献列表** | 中等 | 删除，合并阶段统一生成 |
| **background.md 为空或未完善** | **致命** | **提示用户编辑 `thesis-workspace/references/prompt/background.md`，禁止控制台交互式输入** |

---

## Prompt 文件（写作时加载）

| 文件 | 说明 | 加载时机 |
|------|------|----------|
| `prompts/writer_guidelines.md` | 写作规范 | Step 4 |
| `prompts/aigc_reducer_prompt.md` | AIGC降重 | Step 4 |
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
| `scripts/aigc_detect.py` | AIGC检测 |
| `scripts/lifecycle.py` | 生命周期管理（日志+状态统一入口） |

---

## 致谢

致谢生成位于 `Step 4`（与摘要同阶段），输出文件为 `workspace/drafts/致谢.md`，由 `merge_drafts.py` 在合并阶段自动纳入终稿。

> 注意：致谢不计入七章正文结构，但属于论文交付的必备内容之一。
