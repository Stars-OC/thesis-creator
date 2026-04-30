# thesis-creator 规则统一与接口约束修复 Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 统一 thesis-creator 中关于初始化、文献池、图片清单、摘要字数、ER 图配置和引用唯一性规则的定义，并对现有脚本做最小确定性修复。

**Architecture:** 先修入口文档与 workflow，让 SKILL、workflow、prompt 三层口径一致；再对真实存在的脚本做小范围接口收敛，优先修配置路径、图片清单路径、引用唯一使用与引用顺序约束，不做大规模重构。

**Tech Stack:** Markdown、Python、PyYAML、Graphviz DOT、Mermaid

---

## 设计摘要

### 范围
- 修改 Skill 入口文档、workflow 文档、prompt 文档
- 修改真实存在的脚本：`scripts/chart_generator.py`、`scripts/verified_reference_pool.py`、`scripts/merge_drafts.py`
- 如有必要，补充 `docs/CHANGELOG.md`

### 目标规则
1. Step 0 必须通过脚本初始化工作区
2. `.thesis-config.yaml` 必须初始化，且后续流程必须参考其配置
3. `images.yaml` 唯一路径统一为 `workspace/references/images.yaml`
4. 文献搜索阶段位于 Step 3 与 Step 4 之间，且可在后续阶段回流补池
5. 单篇文献整篇论文只能引用一次
6. 合并时参考文献编号按正文首次出现顺序生成
7. 中文摘要统一为 550 字左右，避免与“页面 2/3”口径冲突
8. 只有 ER 图受 `.thesis-config.yaml.er_modeling` 控制
9. DOT 生成避免显式 `label=` 约束
10. 数据库设计写法固定为“先业务用途文字说明，再给 ER 图”

### 设计决策
- 不新增独立 Step，文献搜索作为 Step 3→4 之间内嵌阶段处理
- 不大改脚本架构，只修真实已存在实现的输入输出契约
- 文档中所有路径、命令与字段名必须相互一致
