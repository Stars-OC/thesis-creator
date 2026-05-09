# scripts 索引与引用脚本模块化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `scripts/` 改造成模型友好的模块索引结构，并把引用相关脚本完全迁移到 `scripts/references/`。

**Architecture:** `scripts/aigc/`、`scripts/charts/`、`scripts/references/` 都以 `INDEX.md` 作为模块入口；`scripts/INDEX.md` 作为总入口。引用脚本不保留根目录兼容包装，所有命令、导入、测试与文档统一切换到 `scripts/references/`。

**Tech Stack:** Python 3、标准库 `pathlib/argparse/dataclasses`、PyYAML、requests、Markdown 文档索引。

---

## 前置约束

- 当前主工作目录不是 Git 仓库，因此本计划不包含实际 commit 步骤；如后续在 Git 仓库中执行且用户明确要求提交，再按变更分批提交。
- 不新增不必要抽象，只做路径迁移、导入修复、索引文档补齐。
- 若测试发现旧路径依赖，优先更新调用方，不创建根目录兼容包装。

---

### Task 1: 将 AIGC YAML 索引替换为 Markdown 索引

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/aigc/INDEX.md`
- Remove: `.claude/skills/thesis-creator/scripts/aigc/_index.yaml`
- Read for reference: `.claude/skills/thesis-creator/scripts/charts/INDEX.md`

**Step 1: 写入 `INDEX.md`**

创建内容结构：

```markdown
# AIGC 脚本索引

本目录负责论文 AIGC 检测与技术论文表达检测，供 Step 6/Step 7 质量门禁调用。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `detect.py` | 通用 AIGC 检测，支持文本、文件和目录检测 |
| `technical_detect.py` | 面向技术论文的 AIGC 检测，结合技术术语白名单降低误判 |

## 资源文件

| 文件 | 用途 |
|---|---|
| `term_whitelist.txt` | 技术术语保护白名单 |

## 推荐命令

```bash
python scripts/aigc/detect.py --input workspace/final/论文终稿.md --format json
python scripts/aigc/technical_detect.py --input workspace/final/论文终稿.md --format json
```

## 推荐顺序

1. `detect.py`
2. `technical_detect.py`
3. 根据检测结果进入 Step 6 改写与自检
```

**Step 2: 删除 YAML 索引**

删除 `.claude/skills/thesis-creator/scripts/aigc/_index.yaml`。

**Step 3: 验证**

检查目录中只保留 `INDEX.md` 作为索引入口。

---

### Task 2: 创建 references 模块目录并迁移脚本

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/references/__init__.py`
- Move: `.claude/skills/thesis-creator/scripts/references/reference_engine.py` → `.claude/skills/thesis-creator/scripts/references/reference_engine.py`
- Move: `.claude/skills/thesis-creator/scripts/references/reference_merger.py` → `.claude/skills/thesis-creator/scripts/references/reference_merger.py`
- Move: `.claude/skills/thesis-creator/scripts/references/reference_validator.py` → `.claude/skills/thesis-creator/scripts/references/reference_validator.py`
- Move: `.claude/skills/thesis-creator/scripts/references/reference_searcher.py` → `.claude/skills/thesis-creator/scripts/references/reference_searcher.py`
- Move: `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py` → `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py`

**Step 1: 创建模块目录**

创建 `scripts/references/` 和空的 `__init__.py`。

**Step 2: 迁移文件**

移动上述 5 个引用脚本，不在根目录保留包装入口。

**Step 3: 验证**

确认以下旧文件不存在：

```text
scripts/references/reference_engine.py
scripts/references/reference_merger.py
scripts/references/reference_validator.py
scripts/references/reference_searcher.py
scripts/references/verified_reference_pool.py
```

并确认新目录存在对应文件。

---

### Task 3: 修复 references 模块内部导入

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_searcher.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_validator.py`
- Check: `.claude/skills/thesis-creator/scripts/references/reference_engine.py`
- Check: `.claude/skills/thesis-creator/scripts/references/reference_merger.py`
- Check: `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py`

**Step 1: 修复 `reference_searcher.py` 导入**

将：

```python
from reference_engine import (
    CrossRefSearcher, OpenAlexSearcher,
    VerifiedReference, MultiSourceSearcher
)
```

改为兼容包导入与直接脚本执行：

```python
try:
    from .reference_engine import (
        CrossRefSearcher, OpenAlexSearcher,
        VerifiedReference, MultiSourceSearcher,
    )
except ImportError:
    from reference_engine import (
        CrossRefSearcher, OpenAlexSearcher,
        VerifiedReference, MultiSourceSearcher,
    )
```

**Step 2: 修复 `reference_validator.py` 导入**

将：

```python
from reference_searcher import SemanticScholarSearcher, verify_doi
```

改为：

```python
try:
    from .reference_searcher import SemanticScholarSearcher, verify_doi
except ImportError:
    from reference_searcher import SemanticScholarSearcher, verify_doi
```

将：

```python
from reference_engine import CrossRefSearcher
```

改为：

```python
try:
    from .reference_engine import CrossRefSearcher
except ImportError:
    from reference_engine import CrossRefSearcher
```

**Step 3: 验证导入**

运行：

```bash
python -m py_compile .claude/skills/thesis-creator/scripts/references/reference_engine.py .claude/skills/thesis-creator/scripts/references/reference_searcher.py .claude/skills/thesis-creator/scripts/references/reference_validator.py .claude/skills/thesis-creator/scripts/references/reference_merger.py .claude/skills/thesis-creator/scripts/references/verified_reference_pool.py
```

Expected: 无输出且退出码为 0。

---

### Task 4: 新增 references 模块索引

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/references/INDEX.md`

**Step 1: 写入模块说明**

索引内容：

```markdown
# 参考文献脚本索引

本目录负责论文参考文献链路：多源搜索、DOI/元数据验证、合并去重、文献池维护、GB/T 7714 格式检查与输出。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `reference_engine.py` | 多源学术搜索引擎，整合 Semantic Scholar、CrossRef、OpenAlex，并处理 DOI 验证 |
| `reference_searcher.py` | 旧搜索接口与多源搜索适配层，支持关键词、DOI 与语言过滤 |
| `reference_merger.py` | 合并多个 YAML 文献文件，按 DOI 和标题相似度去重，并输出 `verified_references.yaml` |
| `reference_validator.py` | 校验参考文献格式、可疑占位符、DOI 可达性和在线元数据 |
| `verified_reference_pool.py` | 管理 `workspace/references/verified_references.yaml`，推荐、占用和导出文献 |

## 推荐顺序

1. `reference_engine.py` 或 `reference_searcher.py` 搜索候选文献
2. `reference_merger.py` 合并去重并生成文献池
3. `reference_validator.py` 检查格式和链接风险
4. `verified_reference_pool.py` 在写作阶段推荐和占用文献

## 推荐命令

```bash
python scripts/references/reference_engine.py --query "RAG 知识库" --source all --language zh --limit 15
python scripts/references/reference_merger.py -i workspace/references/ --top 25 -o workspace/references/verified_references.yaml
python scripts/references/reference_validator.py workspace/final/论文终稿.md --output workspace/reports/
python scripts/references/verified_reference_pool.py --recommend --keywords "RAG 知识库 检索"
```

## 关键约束

- 文献池路径统一为 `workspace/references/verified_references.yaml`
- 同一 `ref_id` 整篇论文仅允许引用一次
- 无 DOI 不等于假文献，但必须记录验证状态
- 中文文献不足时提示人工补充真实来源，禁止伪造
```

**Step 2: 验证**

确认 `references/INDEX.md` 与 `charts/INDEX.md` 风格一致，且路径均指向新目录。

---

### Task 5: 新增 scripts 总索引

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/INDEX.md`

**Step 1: 写入总入口索引**

内容结构：

```markdown
# scripts 脚本总索引

本目录存放 thesis-creator Skill 的执行脚本。模型优先从本文件进入，再按任务读取对应模块的 `INDEX.md`。

## 模块目录

| 模块 | 索引 | 职责 |
|---|---|---|
| AIGC | `aigc/INDEX.md` | AIGC 检测与技术论文表达检测 |
| 图表 | `charts/INDEX.md` | 图片需求抽取、源码准备、渲染、回填与验证 |
| 参考文献 | `references/INDEX.md` | 文献搜索、验证、合并、文献池管理 |

## 根目录脚本

| 脚本 | 职责 |
|---|---|
| `lifecycle.py` | 工作区生命周期检查与状态入口 |
| `status_manager.py` | `.thesis-status.json` 状态管理 |
| `logger.py` | 流程日志记录 |
| `merge_drafts.py` | 合并章节草稿、致谢与参考文献 |
| `document_exporter.py` | 导出 Word/PDF 并处理图片插入 |
| `format_checker.py` | 格式检查 |
| `document_reader.py` | 文档读取辅助 |
| `keyword_extractor.py` | 关键词抽取 |
| `chart_generator.py` | 旧图表生成入口，优先使用 `charts/` 模块链路 |
| `chart_renderer.py` | 旧图表渲染入口，优先使用 `charts/render.py` |

## 推荐读取顺序

1. 先读本文件判断任务类型
2. 再读对应模块的 `INDEX.md`
3. 最后只读取需要执行或修改的具体脚本
```

**Step 2: 验证**

确认 `scripts/INDEX.md` 没有列出已迁移到 `references/` 的根目录旧路径。

---

### Task 6: 更新测试文件路径与导入

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/test_reference_merger.py`
- Modify: `.claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py`
- Modify: `.claude/skills/thesis-creator/scripts/test_reference_validator.py`

**Step 1: 查找旧导入**

搜索：

```text
reference_engine
reference_merger
reference_validator
reference_searcher
verified_reference_pool
```

**Step 2: 更新测试导入**

示例替换：

```python
from reference_merger import load_yaml_file
```

改为：

```python
from references.reference_merger import load_yaml_file
```

如果测试通过修改 `sys.path` 指向 `scripts/`，保留 `scripts/` 路径，让 `references` 作为包导入。

**Step 3: 运行引用测试**

```bash
python .claude/skills/thesis-creator/scripts/test_reference_merger.py
python .claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py
python .claude/skills/thesis-creator/scripts/test_reference_validator.py
```

Expected: 三个测试脚本均通过。

---

### Task 7: 更新 Skill 文档与 workflow 命令路径

**Files:**
- Modify: `.claude/skills/thesis-creator/SKILL.md`
- Modify: `.claude/skills/thesis-creator/README.md`
- Modify as needed: `.claude/skills/thesis-creator/workflows/reference_workflow.md`
- Modify as needed: `.claude/skills/thesis-creator/workflows/step_4_writing.md`
- Modify as needed: `.claude/skills/thesis-creator/workflows/step_7_merge_detect.md`

**Step 1: 搜索旧路径**

搜索以下模式：

```text
scripts/references/reference_engine.py
scripts/references/reference_merger.py
scripts/references/reference_validator.py
scripts/references/reference_searcher.py
scripts/references/verified_reference_pool.py
reference_engine.py
reference_merger.py
reference_validator.py
reference_searcher.py
verified_reference_pool.py
```

**Step 2: 更新命令路径**

命令路径统一改为：

```text
scripts/references/reference_engine.py
scripts/references/reference_merger.py
scripts/references/reference_validator.py
scripts/references/reference_searcher.py
scripts/references/verified_reference_pool.py
```

**Step 3: 更新脚本表格**

`SKILL.md` 的 Script 文件表需要显示：

```markdown
| `scripts/references/reference_engine.py` | 多源搜索 + DOI验证 |
| `scripts/references/reference_merger.py` | 文献合并去重 + 选出最相关 x 篇 |
| `scripts/references/reference_validator.py` | 参考文献格式与 DOI/元数据验证 |
| `scripts/references/verified_reference_pool.py` | 已验证文献池管理 |
```

**Step 4: 验证**

再次搜索旧命令路径，Expected: 不再出现 `scripts/reference_*.py` 或 `scripts/references/verified_reference_pool.py`。

---

### Task 8: 更新设计/上下文记录中的旧引用路径

**Files:**
- Modify as needed: `.claude/skills/thesis-creator/docs/plans/*.md`
- Modify as needed: `.vibe-context/project/modules/reference_pipeline.yaml`
- Modify as needed: `.vibe-context/plans/active_plan.md`

**Step 1: 搜索旧路径**

在 `.claude/skills/thesis-creator/docs/` 和 `.vibe-context/` 中搜索：

```text
scripts/reference_
scripts/references/verified_reference_pool.py
```

**Step 2: 更新路径**

所有路径统一指向 `scripts/references/`。

**Step 3: 保留历史语义**

如果是历史计划文档中的“当时方案”，只更新会误导模型执行的命令路径；不要改写历史结论本身。

---

### Task 9: 全量残留搜索与最小验证

**Files:**
- No direct edits unless search finds missed references.

**Step 1: 搜索旧根目录引用脚本路径**

搜索：

```text
scripts/references/reference_engine.py
scripts/references/reference_merger.py
scripts/references/reference_validator.py
scripts/references/reference_searcher.py
scripts/references/verified_reference_pool.py
```

Expected: 无结果。

**Step 2: 搜索裸导入**

搜索：

```text
from reference_engine
from reference_searcher
from reference_validator
from reference_merger
from verified_reference_pool
import reference_engine
import reference_searcher
import reference_validator
import reference_merger
import verified_reference_pool
```

Expected: 仅允许在 `scripts/references/` 内部的直接脚本执行 fallback 中出现。

**Step 3: 编译 Python 文件**

```bash
python -m py_compile .claude/skills/thesis-creator/scripts/references/reference_engine.py .claude/skills/thesis-creator/scripts/references/reference_searcher.py .claude/skills/thesis-creator/scripts/references/reference_validator.py .claude/skills/thesis-creator/scripts/references/reference_merger.py .claude/skills/thesis-creator/scripts/references/verified_reference_pool.py
```

Expected: 无输出且退出码为 0。

**Step 4: 运行引用测试**

```bash
python .claude/skills/thesis-creator/scripts/test_reference_merger.py
python .claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py
python .claude/skills/thesis-creator/scripts/test_reference_validator.py
```

Expected: 全部通过。

---

### Task 10: 代码审查与收尾

**Files:**
- Review all changed files.

**Step 1: 调用代码审查**

使用 `everything-claude-code:code-reviewer` 或 `superpowers:code-reviewer` 检查：

- 迁移后导入是否稳定
- 文档路径是否一致
- 是否留下双入口歧义
- 测试覆盖是否足够

**Step 2: 根据审查反馈修正**

只修复本次迁移相关问题，不扩大重构范围。

**Step 3: 输出完成摘要**

报告：

- 新增/迁移的索引文件
- references 模块迁移结果
- 已运行测试及结果
- 若有未执行项，明确说明原因
