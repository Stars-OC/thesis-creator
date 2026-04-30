# thesis-creator 规则统一与接口约束修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 thesis-creator 中初始化、文献池、图片生成与摘要规则不一致的问题，并对关键脚本做最小确定性修复。

**Architecture:** 先统一 `SKILL.md`、workflow、prompt 的规则定义，再修 `chart_generator.py`、`verified_reference_pool.py`、`merge_drafts.py` 的路径与行为约束。所有修改遵循最小改动原则，不重构整个系统。

**Tech Stack:** Markdown、Python、PyYAML、Mermaid、Graphviz DOT

---

### Task 1: 统一 Skill 入口规则

**Files:**
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\SKILL.md`

**Step 1: 修改初始化、文献池、图片与摘要规则**
- 明确 Step 0 需脚本初始化
- 统一 `workspace/references/images.yaml`
- 补充文献搜索阶段位于 Step 3→4 之间且可回流
- 加入单篇文献仅能引用一次
- 统一摘要 550 字左右

**Step 2: 自查路径与术语一致性**
- 检查 `.thesis-config.yaml`
- 检查 `verified_references.yaml`
- 检查 `images.yaml`

### Task 2: 统一 workflow 文档

**Files:**
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\workflows\step_0_init.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\workflows\step_4_writing.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\workflows\reference_workflow.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\workflows\step_7_merge_detect.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\workflows\step_8_image.md`

**Step 1: 统一文档路径与阶段定位**
**Step 2: 增加文献回流补池规则**
**Step 3: 增加数据库设计写法与 DOT 约束**

### Task 3: 统一 prompt 规则

**Files:**
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\prompts\writer_guidelines.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\prompts\thesis_structure.md`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\prompts\image_generation.md`

**Step 1: 修正摘要 550 字规则**
**Step 2: 明确数据库设计“先文后图”**
**Step 3: 明确 ER 图仅受 `er_modeling` 控制、图片清单路径统一**

### Task 4: 修复脚本接口约束

**Files:**
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\scripts\chart_generator.py`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\scripts\verified_reference_pool.py`
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\scripts\merge_drafts.py`

**Step 1: 修复 `chart_generator.py` 的 images.yaml 查找路径**
- 仅识别 `workspace/references/images.yaml` 及 `thesis-workspace/workspace/references/images.yaml`

**Step 2: 强化 `verified_reference_pool.py` 的单次引用语义**
- 推荐默认排除已占用文献
- CLI 增加显式排除已占用参数

**Step 3: 强化 `merge_drafts.py` 的唯一引用校验**
- 检测同一 `ref_id` 重复出现并写入 warning/error
- 保持最终编号按首次出现顺序生成

### Task 5: 回归检查与更新变更记录

**Files:**
- Modify: `E:\AIAgent\thesis-creator\.claude\skills\thesis-creator\docs\CHANGELOG.md`

**Step 1: 补充本次规则修复说明**
**Step 2: 通读所有已改路径与命令示例，确保无旧路径残留**
