# Template Package Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 thesis-creator 改造为“通用核心 + 技能包式模板契约”的跨学科论文写作框架，让新学科能主要通过模板包接入，而不修改核心流程代码。

**Architecture:** 新增 `packages/` 模板包体系，使用 `manifest.yaml` 作为类似 skill 的统一入口；新增 `package_validator.py`、`package_loader.py`、`config_resolver.py` 负责校验、加载、继承合并与运行时配置生成。现有 `lifecycle.py` 只接入解析结果，不承载学科规则，保证 CS/SE 默认行为兼容。

**Tech Stack:** Python 3、PyYAML、pytest、Markdown 工作流文档、Claude Code Skill 目录结构。

---

## 执行前约定

- 工作目录：`E:/AIAgent/thesis-creator/.claude/skills/thesis-creator`
- 测试命令统一在该目录下执行：

```bash
python -m pytest test/test_package_validator.py test/test_package_loader.py test/test_config_resolver.py -v
```

- 若执行环境没有 `pytest`，先使用当前项目已有方式安装测试依赖，不要把依赖安装写进核心脚本。
- 每个任务完成后只提交与该任务相关的文件。
- 所有新增配置、文档正文使用中文。

---

## Task 1: 建立模板包目录与最小契约样例

**Files:**
- Create: `packages/base/manifest.yaml`
- Create: `packages/base/structure.yaml`
- Create: `packages/base/writing_rules.yaml`
- Create: `packages/base/checklist.yaml`
- Create: `packages/base/prompts/writer.md`
- Create: `packages/base/examples/README.md`
- Create: `packages/disciplines/cs_se/manifest.yaml`
- Create: `packages/disciplines/cs_se/structure.yaml`
- Create: `packages/disciplines/cs_se/writing_rules.yaml`
- Create: `packages/disciplines/cs_se/checklist.yaml`
- Create: `packages/disciplines/cs_se/diagrams.yaml`
- Create: `packages/disciplines/cs_se/prompts/writer.md`
- Create: `packages/modes/undergraduate.yaml`
- Create: `packages/modes/master.yaml`

**Step 1: Create base package manifest**

Write `packages/base/manifest.yaml`:

```yaml
id: base
name: 通用论文基础模板
version: 1.0.0
extends: null
supports:
  - undergraduate
  - master
capabilities:
  - outline
  - writing
  - citation
  - quality_gate
required_files:
  - structure.yaml
  - writing_rules.yaml
  - checklist.yaml
  - prompts/writer.md
optional_files:
  - diagrams.yaml
  - examples/
```

**Step 2: Create base structure**

Write `packages/base/structure.yaml`:

```yaml
schema_version: 1
structure:
  abstract:
    required: true
    position: before_toc
  chapters:
    - id: ch1
      title: 绪论
      required: true
      sections:
        - id: "1.1"
          title: 研究背景与意义
        - id: "1.2"
          title: 国内外研究现状
        - id: "1.3"
          title: 研究内容与方法
    - id: ch2
      title: 理论基础与相关研究
      required: true
      sections:
        - id: "2.1"
          title: 核心概念界定
        - id: "2.2"
          title: 理论基础
    - id: ch3
      title: 研究设计与分析
      required: true
      sections:
        - id: "3.1"
          title: 研究设计
        - id: "3.2"
          title: 分析过程
    - id: ch4
      title: 结论与展望
      required: true
      sections:
        - id: "4.1"
          title: 研究结论
        - id: "4.2"
          title: 不足与展望
  back_matter:
    references:
      required: true
      format: gbt7714
    acknowledgement:
      required: true
```

**Step 3: Create base writing rules**

Write `packages/base/writing_rules.yaml`:

```yaml
schema_version: 1
writing:
  total_word_count: [8000, 15000]
  paragraph_word_count: [150, 300]
  min_citations_per_1000: 2
  citation_format: gbt7714
abstract:
  zh_word_count: [500, 600]
  en_word_count: [250, 350]
  keywords_count: [3, 5]
aigc:
  threshold: 0.30
  reduction_strategy: full_pipeline
artifacts:
  code_required: false
  screenshot_required: false
  diagrams_required: false
```

**Step 4: Create base checklist**

Write `packages/base/checklist.yaml`:

```yaml
schema_version: 1
checks:
  - id: background_completed
    level: fatal
    description: background.md 必须补全后才能进入写作流程
  - id: references_verified
    level: severe
    description: 参考文献必须经过验证，禁止虚构文献
  - id: duplicate_reference_blocked
    level: fatal
    description: 同一 ref_id 在全文中不得重复引用
  - id: aigc_checklist_required
    level: severe
    description: AIGC 降低必须输出处理计划、改写文本和自检清单
```

**Step 5: Create base prompt**

Write `packages/base/prompts/writer.md`:

```markdown
# 通用论文写作提示词

请遵循两阶段写作法：先输出本章要点规划，用户确认后再扩写正文。

写作要求：
- 保持学术表达，避免口语化。
- 每节围绕一个明确问题展开。
- 引用必须来自已验证文献池。
- 不得在章节内自建参考文献列表。
```

**Step 6: Create CS/SE package manifest**

Write `packages/disciplines/cs_se/manifest.yaml`:

```yaml
id: cs_se
name: 计算机科学与软件工程
version: 1.0.0
extends: base
supports:
  - undergraduate
  - master
capabilities:
  - outline
  - writing
  - citation
  - chart
  - code_block
  - screenshot
required_files:
  - structure.yaml
  - writing_rules.yaml
  - checklist.yaml
  - prompts/writer.md
optional_files:
  - diagrams.yaml
  - examples/
```

**Step 7: Create CS/SE package files**

Write minimal CS/SE files. `packages/disciplines/cs_se/structure.yaml`:

```yaml
schema_version: 1
structure:
  chapters:
    - id: ch1
      title: 绪论
      required: true
    - id: ch2
      title: 关键技术
      required: true
    - id: ch3
      title: 需求分析
      required: true
    - id: ch4
      title: 系统设计
      required: true
      is_core_chapter: true
    - id: ch5
      title: 系统实现
      required: true
      is_core_chapter: true
    - id: ch6
      title: 系统测试
      required: true
    - id: ch7
      title: 总结与展望
      required: true
```

Write `packages/disciplines/cs_se/writing_rules.yaml`:

```yaml
schema_version: 1
artifacts:
  code_required: true
  screenshot_required: true
  diagrams_required: true
  min_database_tables: 11
  min_test_cases: 8
code_block:
  enabled: true
  max_lines: 30
  require_comments: true
```

Write `packages/disciplines/cs_se/checklist.yaml`:

```yaml
schema_version: 1
checks:
  - id: design_implementation_separated
    level: fatal
    description: 系统设计与系统实现必须分离
  - id: database_tables_enough
    level: severe
    description: 数据库表数量建议不少于 11 张
  - id: test_cases_enough
    level: severe
    description: 功能测试用例建议不少于 8 条
```

Write `packages/disciplines/cs_se/diagrams.yaml`:

```yaml
schema_version: 1
diagrams:
  flowchart:
    engine: plantuml
    extension: puml
  usecase:
    engine: plantuml
    extension: puml
  module:
    engine: mermaid
    extension: mmd
  overall_er:
    engine: graphviz
    extension: dot
  entity_er:
    engine: graphviz
    extension: dot
```

Write `packages/disciplines/cs_se/prompts/writer.md`:

```markdown
# 计算机科学与软件工程论文写作提示词

在系统设计、系统实现和系统测试章节中，必须体现软件工程论文特征。

要求：
- 需求分析、系统设计、系统实现、系统测试必须分章处理。
- 系统设计章节重点写架构、模块、流程和数据库。
- 系统实现章节按模块描述功能、界面、关键代码和效果分析。
- 系统测试章节至少包含功能测试表。
```

**Step 8: Create mode files**

Write `packages/modes/undergraduate.yaml`:

```yaml
id: undergraduate
name: 本科毕业论文
defaults:
  word_count_range: [8000, 15000]
  reference_count: [20, 30]
  zh_reference_ratio: 0.65
  abstract_word_count: [500, 600]
  english_abstract_word_count: [250, 350]
  chapter_depth: 2
  aigc_threshold: 0.30
```

Write `packages/modes/master.yaml`:

```yaml
id: master
name: 硕士学位论文
defaults:
  word_count_range: [25000, 40000]
  reference_count: [50, 80]
  zh_reference_ratio: 0.50
  abstract_word_count: [800, 1000]
  english_abstract_word_count: [400, 600]
  chapter_depth: 3
  aigc_threshold: 0.20
```

**Step 9: Commit**

```bash
git add packages/base packages/disciplines packages/modes
git commit -m "feat: add thesis template package skeleton"
```

---

## Task 2: 实现模板包校验器

**Files:**
- Create: `scripts/core/package_validator.py`
- Test: `test/test_package_validator.py`

**Step 1: Write failing tests**

Create `test/test_package_validator.py`:

```python
from pathlib import Path

from scripts.core.package_validator import PackageValidationError, validate_package


def test_validate_package_accepts_complete_base_package():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "base")
    assert result["id"] == "base"
    assert result["valid"] is True


def test_validate_package_rejects_missing_required_file(tmp_path):
    package_dir = tmp_path / "broken"
    package_dir.mkdir()
    (package_dir / "manifest.yaml").write_text(
        """
id: broken
name: 损坏模板
version: 1.0.0
extends: base
required_files:
  - structure.yaml
""".strip(),
        encoding="utf-8",
    )

    try:
        validate_package(package_dir)
    except PackageValidationError as exc:
        assert "structure.yaml" in str(exc)
    else:
        raise AssertionError("缺少必填文件时必须报错")
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest test/test_package_validator.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.core.package_validator'`.

**Step 3: Implement validator**

Create `scripts/core/package_validator.py`:

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class PackageValidationError(ValueError):
    pass


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise PackageValidationError(f"YAML 解析失败: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackageValidationError(f"YAML 顶层必须是对象: {path}")
    return data


def validate_package(package_dir: Path) -> Dict[str, Any]:
    package_dir = Path(package_dir)
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise PackageValidationError(f"缺少 manifest.yaml: {package_dir}")

    manifest = _read_yaml(manifest_path)
    package_id = str(manifest.get("id") or "").strip()
    if not package_id:
        raise PackageValidationError(f"manifest.yaml 缺少 id: {manifest_path}")

    required_files = manifest.get("required_files", [])
    if not isinstance(required_files, list):
        raise PackageValidationError("required_files 必须是列表")

    missing = []
    for relative_path in required_files:
        if not (package_dir / str(relative_path)).exists():
            missing.append(str(relative_path))
    if missing:
        raise PackageValidationError(f"模板包 {package_id} 缺少必填文件: {', '.join(missing)}")

    return {
        "id": package_id,
        "valid": True,
        "manifest": manifest,
        "package_dir": str(package_dir),
    }
```

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest test/test_package_validator.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/core/package_validator.py test/test_package_validator.py
git commit -m "feat: validate thesis template packages"
```

---

## Task 3: 实现模板包加载器与继承合并

**Files:**
- Create: `scripts/core/package_loader.py`
- Test: `test/test_package_loader.py`

**Step 1: Write failing tests**

Create `test/test_package_loader.py`:

```python
from pathlib import Path

from scripts.core.package_loader import deep_merge, load_discipline_package


def test_deep_merge_overrides_nested_values():
    base = {"writing": {"a": 1, "b": 2}, "checks": ["base"]}
    override = {"writing": {"b": 3}, "checks": ["discipline"]}
    assert deep_merge(base, override) == {
        "writing": {"a": 1, "b": 3},
        "checks": ["discipline"],
    }


def test_load_discipline_package_inherits_base():
    root = Path(__file__).resolve().parents[1]
    package = load_discipline_package(root, "cs_se")
    assert package["manifest"]["id"] == "cs_se"
    assert package["structure"]["structure"]["chapters"][0]["title"] == "绪论"
    assert package["writing_rules"]["artifacts"]["code_required"] is True
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest test/test_package_loader.py -v
```

Expected: FAIL with missing module.

**Step 3: Implement loader**

Create `scripts/core/package_loader.py`:

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from core.package_validator import validate_package
except ImportError:
    from .package_validator import validate_package


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _load_package_files(package_dir: Path) -> Dict[str, Any]:
    validate_package(package_dir)
    return {
        "manifest": read_yaml(package_dir / "manifest.yaml"),
        "structure": read_yaml(package_dir / "structure.yaml"),
        "writing_rules": read_yaml(package_dir / "writing_rules.yaml"),
        "checklist": read_yaml(package_dir / "checklist.yaml"),
        "diagrams": read_yaml(package_dir / "diagrams.yaml"),
        "package_dir": str(package_dir),
    }


def load_base_package(skill_root: Path) -> Dict[str, Any]:
    return _load_package_files(Path(skill_root) / "packages" / "base")


def load_discipline_package(skill_root: Path, discipline: str) -> Dict[str, Any]:
    skill_root = Path(skill_root)
    discipline_dir = skill_root / "packages" / "disciplines" / discipline
    discipline_package = _load_package_files(discipline_dir)
    parent_id = discipline_package["manifest"].get("extends")

    if parent_id == "base":
        base_package = load_base_package(skill_root)
        return deep_merge(base_package, discipline_package)

    return discipline_package
```

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest test/test_package_loader.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/core/package_loader.py test/test_package_loader.py
git commit -m "feat: load and merge thesis template packages"
```

---

## Task 4: 实现运行时配置解析器

**Files:**
- Create: `scripts/core/config_resolver.py`
- Test: `test/test_config_resolver.py`

**Step 1: Write failing tests**

Create `test/test_config_resolver.py`:

```python
from pathlib import Path

import yaml

from scripts.core.config_resolver import resolve_runtime_config


def test_resolve_runtime_config_defaults_to_cs_undergraduate(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "thesis-workspace"
    workspace.mkdir()

    result = resolve_runtime_config(root, workspace)

    assert result["thesis"]["discipline"] == "cs_se"
    assert result["thesis"]["mode"] == "undergraduate"
    assert result["package"]["manifest"]["id"] == "cs_se"
    assert result["mode"]["defaults"]["reference_count"] == [20, 30]


def test_resolve_runtime_config_reads_workspace_config(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "thesis-workspace"
    workspace.mkdir()
    (workspace / ".thesis-config.yaml").write_text(
        yaml.safe_dump({"thesis": {"discipline": "cs_se", "mode": "master"}}, allow_unicode=True),
        encoding="utf-8",
    )

    result = resolve_runtime_config(root, workspace)

    assert result["thesis"]["mode"] == "master"
    assert result["mode"]["defaults"]["reference_count"] == [50, 80]
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest test/test_config_resolver.py -v
```

Expected: FAIL with missing module.

**Step 3: Implement resolver**

Create `scripts/core/config_resolver.py`:

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from core.package_loader import deep_merge, load_discipline_package, read_yaml
except ImportError:
    from .package_loader import deep_merge, load_discipline_package, read_yaml


DEFAULT_THESIS = {
    "discipline": "cs_se",
    "mode": "undergraduate",
}


def _load_workspace_config(workspace: Path) -> Dict[str, Any]:
    config_path = Path(workspace) / ".thesis-config.yaml"
    if not config_path.exists():
        return {}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _load_mode(skill_root: Path, mode: str) -> Dict[str, Any]:
    mode_path = Path(skill_root) / "packages" / "modes" / f"{mode}.yaml"
    mode_data = read_yaml(mode_path)
    if not mode_data:
        raise FileNotFoundError(f"模式配置不存在: {mode_path}")
    return mode_data


def resolve_runtime_config(skill_root: Path, workspace: Path) -> Dict[str, Any]:
    skill_root = Path(skill_root)
    workspace = Path(workspace)
    workspace_config = _load_workspace_config(workspace)
    thesis_config = deep_merge(DEFAULT_THESIS, workspace_config.get("thesis", {}))

    discipline = thesis_config["discipline"]
    mode = thesis_config["mode"]

    package = load_discipline_package(skill_root, discipline)
    mode_config = _load_mode(skill_root, mode)

    runtime_config = {
        "thesis": thesis_config,
        "package": package,
        "mode": mode_config,
        "workspace_config": workspace_config,
    }

    return runtime_config


def write_runtime_config(skill_root: Path, workspace: Path) -> Path:
    runtime_config = resolve_runtime_config(skill_root, workspace)
    output_path = Path(workspace) / ".thesis-runtime-config.yaml"
    output_path.write_text(
        yaml.safe_dump(runtime_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path
```

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest test/test_config_resolver.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/core/config_resolver.py test/test_config_resolver.py
git commit -m "feat: resolve thesis runtime configuration"
```

---

## Task 5: 将 lifecycle 接入运行时配置生成

**Files:**
- Modify: `scripts/core/lifecycle.py:25-27,143-178,182-215`
- Test: `test/test_lifecycle_package_config.py`

**Step 1: Write failing test**

Create `test/test_lifecycle_package_config.py`:

```python
from pathlib import Path

import yaml

from scripts.core.lifecycle import init_and_check_workspace


def test_init_workspace_writes_runtime_config(tmp_path):
    workspace = tmp_path / "thesis-workspace"

    report = init_and_check_workspace(str(workspace), sync_scripts=False)

    assert report["ok"] is True
    runtime_config_path = workspace / ".thesis-runtime-config.yaml"
    assert runtime_config_path.exists()
    runtime_config = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8"))
    assert runtime_config["thesis"]["discipline"] == "cs_se"
    assert runtime_config["package"]["manifest"]["id"] == "cs_se"
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest test/test_lifecycle_package_config.py -v
```

Expected: FAIL because `.thesis-runtime-config.yaml` is not created.

**Step 3: Import runtime config writer**

Modify `scripts/core/lifecycle.py` near imports:

```python
from core.status_manager import ThesisStatusManager, STEPS
from core.logger import init_logger, get_logger
try:
    from core.config_resolver import write_runtime_config
except ImportError:
    from .config_resolver import write_runtime_config
```

**Step 4: Write runtime config during workspace initialization**

Modify `ensure_workspace_structure()` after `_ensure_workspace_config(workspace)`:

```python
    _ensure_workspace_config(workspace)
    write_runtime_config(Path(__file__).resolve().parents[2], workspace)
    _ensure_image_manifest(workspace)
```

**Step 5: Include runtime config in preflight**

Modify `check_workspace_preflight()` required paths:

```python
        ".thesis-runtime-config.yaml",
```

Place it after `.thesis-config.yaml`.

**Step 6: Run test to verify it passes**

Run:

```bash
python -m pytest test/test_lifecycle_package_config.py test/test_lifecycle_workspace_check.py -v
```

Expected: PASS.

**Step 7: Commit**

```bash
git add scripts/core/lifecycle.py test/test_lifecycle_package_config.py
git commit -m "feat: write runtime package config during workspace init"
```

---

## Task 6: 更新 Step 0 与 Step 3 工作流文档

**Files:**
- Modify: `workflows/step_0_init.md`
- Modify: `workflows/step_3_outline.md`
- Modify: `SKILL.md:64-70,74-85,140-165`

**Step 1: Update Step 0 documentation**

In `workflows/step_0_init.md`, add a section named `模板包加载规则`:

```markdown
## 模板包加载规则

Step 0 初始化时必须完成以下动作：

1. 读取 `thesis-workspace/.thesis-config.yaml` 中的 `thesis.discipline` 与 `thesis.mode`。
2. 未指定时默认使用：
   - `discipline: cs_se`
   - `mode: undergraduate`
3. 加载 skill 内置模板包：
   - `packages/base/`
   - `packages/disciplines/{discipline}/`
   - `packages/modes/{mode}.yaml`
4. 按优先级合并配置：

`用户覆盖 > 学科模板 > 模式模板 > 基础模板 > 系统默认`

5. 输出运行时配置到：

`thesis-workspace/.thesis-runtime-config.yaml`

如果模板包缺少 `manifest.yaml` 或必填文件，必须停止流程并提示用户修复模板包，禁止继续进入 Step 3。
```

**Step 2: Update Step 3 documentation**

In `workflows/step_3_outline.md`, add a section named `配置驱动大纲生成`:

```markdown
## 配置驱动大纲生成

生成大纲时，不再直接假设七章制结构。必须优先读取：

`thesis-workspace/.thesis-runtime-config.yaml`

大纲来源优先级：

1. 用户覆盖层中的自定义结构
2. 学科模板 `structure.yaml`
3. 基础模板 `structure.yaml`

CS/SE 学科默认仍使用七章结构：绪论、关键技术、需求分析、系统设计、系统实现、系统测试、总结与展望。

非 CS/SE 学科不得强制要求代码、截图、数据库表或测试用例，除非对应学科模板明确要求。
```

**Step 3: Update SKILL.md**

Modify relevant sections in `SKILL.md`:

- In Step 0 pause point, add `.thesis-runtime-config.yaml` as required output.
- In workflow table, note Step 0 loads template packages.
- In user workspace tree, add `.thesis-runtime-config.yaml`.
- In Script files table, add:

```markdown
| `scripts/core/package_validator.py` | 校验学科模板包 manifest 和必填文件 |
| `scripts/core/package_loader.py` | 加载并继承合并基础模板与学科模板 |
| `scripts/core/config_resolver.py` | 解析学科、模式与用户覆盖，生成运行时配置 |
```

**Step 4: Manual verification**

Run:

```bash
python scripts/core/lifecycle.py --workspace thesis-workspace-test --init-and-check
```

Expected output includes success, and `thesis-workspace-test/.thesis-runtime-config.yaml` exists.

**Step 5: Commit**

```bash
git add workflows/step_0_init.md workflows/step_3_outline.md SKILL.md
git commit -m "docs: document template package workflow loading"
```

---

## Task 7: 新增经管与法学示例模板包

**Files:**
- Create: `packages/disciplines/business_management/manifest.yaml`
- Create: `packages/disciplines/business_management/structure.yaml`
- Create: `packages/disciplines/business_management/writing_rules.yaml`
- Create: `packages/disciplines/business_management/checklist.yaml`
- Create: `packages/disciplines/business_management/prompts/writer.md`
- Create: `packages/disciplines/law/manifest.yaml`
- Create: `packages/disciplines/law/structure.yaml`
- Create: `packages/disciplines/law/writing_rules.yaml`
- Create: `packages/disciplines/law/checklist.yaml`
- Create: `packages/disciplines/law/prompts/writer.md`
- Test: `test/test_example_discipline_packages.py`

**Step 1: Write failing tests**

Create `test/test_example_discipline_packages.py`:

```python
from pathlib import Path

from scripts.core.package_loader import load_discipline_package
from scripts.core.package_validator import validate_package


def test_business_management_package_is_valid():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "disciplines" / "business_management")
    assert result["valid"] is True


def test_law_package_is_valid():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "disciplines" / "law")
    assert result["valid"] is True


def test_business_management_does_not_require_code_by_default():
    root = Path(__file__).resolve().parents[1]
    package = load_discipline_package(root, "business_management")
    assert package["writing_rules"]["artifacts"]["code_required"] is False
```

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest test/test_example_discipline_packages.py -v
```

Expected: FAIL because packages do not exist.

**Step 3: Create business management package**

Use `manifest.yaml`:

```yaml
id: business_management
name: 经济管理
version: 1.0.0
extends: base
supports:
  - undergraduate
  - master
capabilities:
  - outline
  - writing
  - citation
  - chart
required_files:
  - structure.yaml
  - writing_rules.yaml
  - checklist.yaml
  - prompts/writer.md
optional_files:
  - diagrams.yaml
  - examples/
```

Use `structure.yaml`:

```yaml
schema_version: 1
structure:
  chapters:
    - id: ch1
      title: 绪论
      required: true
    - id: ch2
      title: 相关理论与文献综述
      required: true
    - id: ch3
      title: 研究设计
      required: true
    - id: ch4
      title: 实证分析或案例分析
      required: true
      is_core_chapter: true
    - id: ch5
      title: 研究结论与建议
      required: true
```

Use `writing_rules.yaml`:

```yaml
schema_version: 1
artifacts:
  code_required: false
  screenshot_required: false
  diagrams_required: true
  required_tables:
    - 变量定义表
    - 描述性统计表
references:
  zh_reference_ratio: 0.50
```

Use `checklist.yaml`:

```yaml
schema_version: 1
checks:
  - id: research_method_clear
    level: severe
    description: 必须说明研究方法、样本或案例来源
  - id: conclusion_matches_analysis
    level: severe
    description: 结论必须回应前文分析结果
```

Use `prompts/writer.md`:

```markdown
# 经济管理论文写作提示词

写作时应突出研究问题、理论基础、研究设计、分析过程和管理建议。

要求：
- 不要求代码和系统截图。
- 实证类论文应说明变量、数据来源和分析方法。
- 案例类论文应说明案例背景、问题诊断和建议依据。
```

**Step 4: Create law package**

Use analogous files with this `structure.yaml`:

```yaml
schema_version: 1
structure:
  chapters:
    - id: ch1
      title: 引言
      required: true
    - id: ch2
      title: 基本理论概述
      required: true
    - id: ch3
      title: 现状考察与案例分析
      required: true
      is_core_chapter: true
    - id: ch4
      title: 问题与原因分析
      required: true
    - id: ch5
      title: 完善建议
      required: true
    - id: ch6
      title: 结语
      required: true
```

Use `writing_rules.yaml`:

```yaml
schema_version: 1
artifacts:
  code_required: false
  screenshot_required: false
  diagrams_required: false
references:
  zh_reference_ratio: 0.70
law:
  require_case_analysis: true
  require_normative_basis: true
```

Use `checklist.yaml`:

```yaml
schema_version: 1
checks:
  - id: legal_basis_clear
    level: severe
    description: 法学论文必须明确法条、案例或制度依据
  - id: recommendation_has_basis
    level: severe
    description: 完善建议必须有前文问题分析支撑
```

Use `prompts/writer.md`:

```markdown
# 法学论文写作提示词

写作时应突出概念界定、法律规范、典型案例、问题分析和制度建议。

要求：
- 不要求代码、截图、数据库表或系统测试。
- 法条、案例和制度分析必须服务于论文中心问题。
- 完善建议必须回应前文问题。
```

**Step 5: Run test to verify it passes**

Run:

```bash
python -m pytest test/test_example_discipline_packages.py -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add packages/disciplines/business_management packages/disciplines/law test/test_example_discipline_packages.py
git commit -m "feat: add example discipline template packages"
```

---

## Task 8: 增加模板作者文档

**Files:**
- Create: `docs/template-package-authoring.md`
- Modify: `docs/usage_guide.md`
- Modify: `docs/ROADMAP.md`

**Step 1: Create authoring guide**

Create `docs/template-package-authoring.md`:

```markdown
# 学科模板包编写指南

## 模板包是什么

模板包是 thesis-creator 的学科能力模块，作用类似 skill。每个模板包通过 `manifest.yaml` 暴露能力，通过 YAML 文件和提示词定义学科差异。

## 最小目录

```text
packages/disciplines/your_discipline/
├── manifest.yaml
├── structure.yaml
├── writing_rules.yaml
├── checklist.yaml
└── prompts/
    └── writer.md
```

## 新增学科步骤

1. 复制 `packages/disciplines/cs_se/` 或 `packages/base/`。
2. 修改 `manifest.yaml` 的 `id`、`name`、`supports` 和 `capabilities`。
3. 修改 `structure.yaml`，只描述章节结构。
4. 修改 `writing_rules.yaml`，只描述写作和产物要求。
5. 修改 `checklist.yaml`，只描述质量门禁。
6. 修改 `prompts/writer.md`，补充学科语境。
7. 运行模板包测试。

## 合并优先级

`用户覆盖 > 学科模板 > 模式模板 > 基础模板 > 系统默认`

## 注意事项

- 不要在模板包里写核心流程逻辑。
- 非 CS/SE 学科不要继承代码、截图、数据库表等要求。
- 如果某个学科确实需要特殊图表，优先补 `diagrams.yaml`，不要改图表主流程。
```

**Step 2: Link from usage guide**

In `docs/usage_guide.md`, add a section pointing to `docs/template-package-authoring.md`.

**Step 3: Update roadmap**

In `docs/ROADMAP.md`, add v2.0 section:

```markdown
## v2.0 - 通用核心与学科模板包

目标：将 thesis-creator 从单一 CS/SE 论文辅助系统升级为支持多学科模板包的通用框架。

核心能力：
- 技能包式模板契约
- 基础模板、学科模板、模式模板分层
- 运行时配置解析
- 新学科低代码接入
```

**Step 4: Manual verification**

Open `docs/template-package-authoring.md` and check:

- Has minimal package structure
- Has required files list
- Has merge priority
- Has new discipline onboarding steps

**Step 5: Commit**

```bash
git add docs/template-package-authoring.md docs/usage_guide.md docs/ROADMAP.md
git commit -m "docs: add template package authoring guide"
```

---

## Task 9: 端到端回归验证

**Files:**
- No code changes expected
- May update tests only if an existing assertion is obsolete because of `.thesis-runtime-config.yaml`

**Step 1: Run focused tests**

Run:

```bash
python -m pytest test/test_package_validator.py test/test_package_loader.py test/test_config_resolver.py test/test_lifecycle_package_config.py test/test_example_discipline_packages.py -v
```

Expected: PASS.

**Step 2: Run existing lifecycle and chart tests**

Run:

```bash
python -m pytest test/test_lifecycle_workspace_check.py test/test_charts_schema.py test/test_charts_manifest_builder.py -v
```

Expected: PASS.

**Step 3: Run full test suite**

Run:

```bash
python -m pytest test -v
```

Expected: PASS.

**Step 4: Manual workspace check**

Run:

```bash
python scripts/core/lifecycle.py --workspace thesis-workspace-test --init-and-check
```

Expected:

- Output includes `[成功] 工作区初始化与检查通过`
- `thesis-workspace-test/.thesis-config.yaml` exists
- `thesis-workspace-test/.thesis-runtime-config.yaml` exists
- `thesis-workspace-test/workspace/references/images.yaml` exists

**Step 5: Manual non-CS config check**

Edit `thesis-workspace-test/.thesis-config.yaml`:

```yaml
thesis:
  discipline: business_management
  mode: undergraduate
```

Run:

```bash
python scripts/core/lifecycle.py --workspace thesis-workspace-test --prepare-runtime
```

Expected:

- `.thesis-runtime-config.yaml` contains `discipline: business_management`
- package manifest id is `business_management`
- artifacts do not require code by default

**Step 6: Commit any test-only adjustment**

```bash
git add test scripts packages docs SKILL.md workflows
git commit -m "test: verify template package integration"
```

Only run this commit if there are actual changes from regression fixes.

---

## Task 10: 完成前检查

**Files:**
- No file changes expected

**Step 1: Use verification skill**

Before reporting complete, use `@superpowers:verification-before-completion`.

**Step 2: Review changed files**

Run:

```bash
git status
```

Expected: no unexpected files.

Run:

```bash
git diff --stat
```

Expected: changes are limited to packages, core config scripts, tests, docs, workflows, and SKILL.md.

**Step 3: Final acceptance checklist**

Verify:

- `packages/base/manifest.yaml` exists
- `packages/disciplines/cs_se/manifest.yaml` exists
- `packages/disciplines/business_management/manifest.yaml` exists
- `packages/disciplines/law/manifest.yaml` exists
- `scripts/core/package_validator.py` exists
- `scripts/core/package_loader.py` exists
- `scripts/core/config_resolver.py` exists
- `lifecycle.py --init-and-check` writes `.thesis-runtime-config.yaml`
- Existing CS/SE workflow still defaults to `cs_se + undergraduate`
- Non-CS template does not inherit code/screenshot/database requirements unless explicitly configured

**Step 4: Final commit if needed**

If previous tasks left uncommitted final cleanup:

```bash
git add packages scripts test docs workflows SKILL.md
git commit -m "chore: finalize template package contract integration"
```

---

## 关键设计取舍

| 决策点 | 方案 A | 方案 B | 推荐 |
|---|---|---|---|
| 模板扩展方式 | 单层配置目录 | 技能包式 `manifest.yaml` 契约 | ⭐ 方案 B，入口清晰、可校验 |
| 继承层级 | 多级继承 | `base -> discipline -> override` 浅继承 | ⭐ 浅继承，用户更容易理解 |
| 新学科接入 | 修改核心流程 | 新增模板包 | ⭐ 新增模板包，降低维护成本 |
| 工作流改造 | 一次性重写 Step 0~9 | 先接入 Step 0/3/4/8 | ⭐ 渐进接入，风险更低 |

---

## 完成定义

本实施计划完成后，应满足：

1. 模板包有统一入口 `manifest.yaml`。
2. 系统能校验模板包必填文件。
3. 系统能加载 `base` 与 `discipline` 并合并配置。
4. 系统能根据 `.thesis-config.yaml` 生成 `.thesis-runtime-config.yaml`。
5. 默认行为仍为 `cs_se + undergraduate`。
6. 经管和法学两个非 CS 示例模板包可通过校验。
7. Step 0 和 Step 3 文档明确说明模板包加载规则。
8. 模板作者文档说明如何新增一个学科包。
