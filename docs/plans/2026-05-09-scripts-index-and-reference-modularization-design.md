# scripts 索引与引用脚本模块化设计

## 背景

本次改造面向 `thesis-creator` Skill 的 `scripts/` 目录，目标是让模型更容易按模块阅读脚本能力，并将引用相关脚本从根目录散放状态收敛为独立模块。

## 已确认方案

采用「完全迁移」方案：新增 `scripts/references/` 模块目录，将引用相关脚本迁入该目录，并同步更新导入、测试、文档和命令路径。

## 结构设计

### AIGC 模块索引

将 `scripts/aigc/_index.yaml` 替换为 Markdown 形式的 `scripts/aigc/INDEX.md`，风格对齐 `scripts/charts/INDEX.md`。

内容包含：

- 模块说明
- 脚本职责
- 资源文件
- 推荐使用顺序
- 兼容迁移说明

### references 模块

新增目录：

```text
scripts/references/
├── __init__.py
├── INDEX.md
├── reference_engine.py
├── reference_merger.py
├── reference_validator.py
├── reference_searcher.py
└── verified_reference_pool.py
```

引用链路相关脚本全部迁入该目录，命令示例统一改为：

```bash
python scripts/references/reference_merger.py ...
python scripts/references/reference_engine.py ...
python scripts/references/reference_validator.py ...
```

### scripts 总索引

新增 `scripts/INDEX.md`，作为模型阅读 `scripts/` 的入口。

内容包含：

- 模块目录索引：`aigc/`、`charts/`、`references/`
- 根目录通用脚本职责
- 推荐流程入口
- 测试入口说明

## 导入与路径策略

- 包内引用优先使用相对导入或兼容脚本直接执行的导入方式。
- 测试文件同步更新到新路径。
- Skill 文档、workflow、README、计划文档中的旧路径统一替换。
- 不保留根目录旧引用脚本包装入口，避免产生双入口歧义。

## 验证方式

至少运行以下测试：

```bash
python .claude/skills/thesis-creator/scripts/test_reference_merger.py
python .claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py
python .claude/skills/thesis-creator/scripts/test_reference_validator.py
```

并执行路径残留搜索，确认旧的 `scripts/reference_*.py` 命令引用不再残留。
