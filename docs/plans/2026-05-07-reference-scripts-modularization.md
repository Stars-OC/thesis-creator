# Reference Scripts Modularization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 thesis-creator 的参考文献相关脚本重构为清晰的 `scripts/references/` 领域包，优先建立架构边界，并保留现有 CLI 入口作为兼容薄封装。

**Architecture:** 新增 `scripts/references/` 包承载统一模型、I/O、语种识别、评分、去重、格式化、搜索器、合并器、文献池与验证器。原 `reference_engine.py`、`reference_merger.py`、`verified_reference_pool.py`、`reference_validator.py` 逐步瘦身为 CLI 兼容入口，避免一次性破坏现有 workflow 与测试导入路径。

**Tech Stack:** Python 3 标准库、`dataclasses`、`argparse`、`pathlib`、`yaml`、`requests`、现有 `unittest` 测试风格。

---

## 关键约束

- 本轮目标是「彻底重构 + 架构优先」，但仍保留旧脚本文件名，避免文档与已有命令立即失效。
- 不引入新依赖；继续使用 PyYAML 与 requests。
- 迁移过程必须保持现有测试通过：
  - `python scripts/test_reference_merger.py`
  - `python scripts/test_reference_engine_verification_states.py`
  - `python scripts/test_reference_validator.py`
- 每个旧入口的公开导入符号需临时兼容，例如：
  - `from reference_merger import select_top, save_yaml, assess_reference_quality`
  - `from reference_engine import VerifiedReference, ReferenceFormatter`
  - `from reference_validator import Reference, ReferenceValidator`

---

### Task 1: 创建 references 包骨架

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/references/__init__.py`
- Create: `.claude/skills/thesis-creator/scripts/references/models.py`
- Create: `.claude/skills/thesis-creator/scripts/references/io.py`
- Create: `.claude/skills/thesis-creator/scripts/references/language.py`
- Create: `.claude/skills/thesis-creator/scripts/references/scoring.py`
- Create: `.claude/skills/thesis-creator/scripts/references/dedupe.py`
- Create: `.claude/skills/thesis-creator/scripts/references/formatters.py`
- Create: `.claude/skills/thesis-creator/scripts/references/searchers.py`
- Create: `.claude/skills/thesis-creator/scripts/references/merger.py`
- Create: `.claude/skills/thesis-creator/scripts/references/pool.py`
- Create: `.claude/skills/thesis-creator/scripts/references/validator.py`
- Create: `.claude/skills/thesis-creator/scripts/references/cli/__init__.py`

**Step 1: Write the failing smoke test**

Create `.claude/skills/thesis-creator/scripts/test_references_package_imports.py`:

```python
# -*- coding: utf-8 -*-

import unittest


class ReferencesPackageImportsTest(unittest.TestCase):
    def test_imports_package_modules(self):
        from references import models, io, language, scoring, dedupe, formatters, merger, pool, validator

        self.assertIsNotNone(models)
        self.assertIsNotNone(io)
        self.assertIsNotNone(language)
        self.assertIsNotNone(scoring)
        self.assertIsNotNone(dedupe)
        self.assertIsNotNone(formatters)
        self.assertIsNotNone(merger)
        self.assertIsNotNone(pool)
        self.assertIsNotNone(validator)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run from `.claude/skills/thesis-creator`:

```bash
python scripts/test_references_package_imports.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'references'` or missing module.

**Step 3: Add minimal package files**

Create empty package/module files listed above. Keep `__init__.py` minimal:

```python
# -*- coding: utf-8 -*-
```

**Step 4: Run test to verify it passes**

```bash
python scripts/test_references_package_imports.py
```

Expected: PASS.

---

### Task 2: 迁移统一文献模型

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/models.py`
- Modify later wrappers only after tests pass:
  - `.claude/skills/thesis-creator/scripts/references/reference_engine.py`
  - `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py`
  - `.claude/skills/thesis-creator/scripts/references/reference_validator.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_models.py`

**Step 1: Write failing model tests**

Create `.claude/skills/thesis-creator/scripts/test_references_models.py`:

```python
# -*- coding: utf-8 -*-

import unittest

from references.models import PoolReference, Reference, VerifiedReference


class ReferencesModelsTest(unittest.TestCase):
    def test_verified_reference_to_dict_keeps_verification_fields(self):
        ref = VerifiedReference(title="t", authors=["a"], year=2024, doi="", doi_url="")
        ref.source_url = "https://example.com/ref"
        ref.verification_status = "verified_metadata_only"
        ref.verification_reason = "标题与作者匹配"
        ref.metadata_verified = True
        ref.doi_reachable = False

        payload = ref.to_dict()

        self.assertEqual("https://example.com/ref", payload["source_url"])
        self.assertEqual("verified_metadata_only", payload["verification_status"])
        self.assertEqual("标题与作者匹配", payload["verification_reason"])
        self.assertTrue(payload["metadata_verified"])
        self.assertFalse(payload["doi_reachable"])

    def test_pool_reference_to_dict(self):
        ref = PoolReference(
            id="ref_001",
            title="中文文献",
            authors=["作者甲"],
            year=2024,
            doi="",
            doi_url="",
        )

        payload = ref.to_dict()

        self.assertEqual("ref_001", payload["id"])
        self.assertEqual("中文文献", payload["title"])
        self.assertEqual(0, payload["used_count"])
        self.assertEqual([], payload["chapters_used"])

    def test_reference_defaults_issues_to_empty_list(self):
        ref = Reference(
            index=1,
            raw_text="[1] 示例参考文献",
            ref_type="J",
            authors=["张三"],
            title="题名",
            journal="期刊",
            year=2024,
            volume=None,
            issue=None,
            pages=None,
            publisher=None,
            doi=None,
            url=None,
        )

        self.assertEqual([], ref.issues)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_models.py
```

Expected: FAIL because classes do not exist.

**Step 3: Move dataclasses into `references/models.py`**

Copy current dataclasses exactly from existing files:

- `VerifiedReference` from `reference_engine.py:66`
- `PoolReference` from `verified_reference_pool.py:30`
- `Reference` from `reference_validator.py:54`

Use `asdict` for `to_dict()` methods and preserve all existing fields/defaults.

**Step 4: Run model tests**

```bash
python scripts/test_references_models.py
```

Expected: PASS.

**Step 5: Update compatibility imports**

In old files, replace local dataclass definitions with imports:

```python
from references.models import VerifiedReference
```

```python
from references.models import PoolReference
```

```python
from references.models import Reference
```

Do not otherwise change behavior yet.

**Step 6: Run existing import-sensitive tests**

```bash
python scripts/test_reference_engine_verification_states.py
python scripts/test_reference_validator.py
```

Expected: PASS.

---

### Task 3: 迁移 YAML/JSON I/O 与语言识别

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/io.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/language.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_merger.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_io_language.py`

**Step 1: Write failing tests**

Create `.claude/skills/thesis-creator/scripts/test_references_io_language.py`:

```python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

import yaml

from references.io import load_yaml_references, save_reference_pool_yaml
from references.language import check_language_balance, is_language


class ReferencesIoLanguageTest(unittest.TestCase):
    def test_save_reference_pool_yaml_escapes_special_titles(self):
        refs = [
            {"title": "RAG: Survey (2024)", "language": "en"},
            {"title": "中文文献：系统设计（实践）", "language": "zh"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "verified_references.yaml"
            save_reference_pool_yaml(refs, output, selection_limit=25, language_balance={"zh": 1, "en": 1})
            parsed = yaml.safe_load(output.read_text(encoding="utf-8"))

        self.assertEqual("RAG: Survey (2024)", parsed["references"][0]["title"])
        self.assertEqual(25, parsed["selection_limit"])

    def test_load_yaml_references_returns_empty_on_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.yaml"
            path.write_text("references: [", encoding="utf-8")

            refs = load_yaml_references(path)

        self.assertEqual([], refs)

    def test_language_detection_uses_explicit_lang_and_title_fallback(self):
        self.assertTrue(is_language({"language": "zh", "title": "English"}, "zh"))
        self.assertTrue(is_language({"title": "中文标题"}, "zh"))
        self.assertTrue(is_language({"title": "English Title"}, "en"))
        self.assertEqual({"zh": 2, "en": 1}, check_language_balance([
            {"language": "zh", "title": "A"},
            {"title": "中文标题"},
            {"title": "English"},
        ]))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_io_language.py
```

Expected: FAIL because functions do not exist.

**Step 3: Implement I/O helpers**

Move behavior from `reference_merger.py`:

- `load_yaml_file()` → `load_yaml_references(path: Path) -> list[dict]`
- `load_from_directory()` → `load_yaml_references_from_directory(dir_path: Path) -> list[dict]`
- `save_yaml()` → `save_reference_pool_yaml(...)`

Keep existing warning print behavior and `yaml.safe_load` / `yaml.safe_dump` behavior.

**Step 4: Implement language helpers**

Move behavior from `reference_merger.py`:

- `check_language_balance(refs)`
- `_is_language(ref, target_lang)` renamed to public `is_language(ref, target_lang)`
- `ZH_RATIO_MIN = 0.65`

**Step 5: Keep compatibility in `reference_merger.py`**

Import and alias old public names:

```python
from references.io import load_yaml_references as load_yaml_file
from references.io import load_yaml_references_from_directory as load_from_directory
from references.io import save_reference_pool_yaml as save_yaml
from references.language import ZH_RATIO_MIN, check_language_balance, is_language as _is_language
```

**Step 6: Run tests**

```bash
python scripts/test_references_io_language.py
python scripts/test_reference_merger.py
```

Expected: PASS.

---

### Task 4: 迁移评分、去重与合并服务

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/scoring.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/dedupe.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/merger.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_merger.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_merger_service.py`

**Step 1: Write failing service tests**

Create `.claude/skills/thesis-creator/scripts/test_references_merger_service.py`:

```python
# -*- coding: utf-8 -*-

import unittest

from references.dedupe import deduplicate, title_similarity
from references.merger import ReferenceMerger, assess_reference_quality, renumber, select_top
from references.scoring import compute_score


class ReferencesMergerServiceTest(unittest.TestCase):
    def make_ref(self, title, language, relevance, doi="", citations=0, year=2025):
        return {
            "title": title,
            "language": language,
            "relevance_score": relevance,
            "citation_count": citations,
            "year": year,
            "cross_verified": True,
            "verified": True,
            "doi": doi,
        }

    def test_title_similarity_detects_exact_match(self):
        self.assertEqual(1.0, title_similarity("Same Title", "same title"))

    def test_deduplicate_uses_doi_and_title_similarity(self):
        refs = [
            self.make_ref("A", "en", 0.9, doi="10.1/a"),
            self.make_ref("A duplicate", "en", 0.8, doi="10.1/a"),
            self.make_ref("中文文献", "zh", 0.7),
            self.make_ref("中文文献", "zh", 0.6),
        ]

        result = deduplicate(refs)

        self.assertEqual(2, len(result))

    def test_select_top_keeps_language_mix_when_possible(self):
        refs = [
            self.make_ref("English A", "en", 0.99, citations=900),
            self.make_ref("English B", "en", 0.98, citations=800),
            self.make_ref("中文文献C", "zh", 0.97, citations=700),
        ]

        selected = select_top(refs, 2)

        self.assertEqual(2, len(selected))
        self.assertTrue(any(ref["language"] == "zh" for ref in selected))

    def test_reference_merger_merge_returns_summary(self):
        merger = ReferenceMerger(top_n=2)
        refs = [
            self.make_ref("English A", "en", 0.99, doi="10.1/a"),
            self.make_ref("English A", "en", 0.95, doi="10.1/a"),
            self.make_ref("中文文献B", "zh", 0.98, doi="10.1/b"),
        ]

        result = merger.merge(refs)

        self.assertEqual(3, result.loaded_count)
        self.assertEqual(2, result.deduped_count)
        self.assertEqual(2, len(result.selected))
        self.assertEqual("ref_001", result.selected[0]["id"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_merger_service.py
```

Expected: FAIL because modules/functions do not exist.

**Step 3: Move scoring and dedupe functions**

Move these functions from `reference_merger.py`:

- `title_similarity()` → `references/dedupe.py`
- `deduplicate()` → `references/dedupe.py`
- `compute_score()` → `references/scoring.py`

**Step 4: Move merge functions into `references/merger.py`**

Move and preserve behavior:

- `assess_reference_quality()`
- `select_top()`
- `renumber()`

Add a small result model:

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MergeResult:
    loaded_count: int
    deduped_count: int
    selected: List[Dict]
    language_balance: Dict[str, int]
```

Add service:

```python
class ReferenceMerger:
    def __init__(self, top_n: int = 25):
        self.top_n = top_n

    def merge(self, refs: List[Dict]) -> MergeResult:
        loaded_count = len(refs)
        deduped = deduplicate(refs)
        selected = renumber(select_top(deduped, self.top_n))
        return MergeResult(
            loaded_count=loaded_count,
            deduped_count=len(deduped),
            selected=selected,
            language_balance=check_language_balance(selected),
        )
```

**Step 5: Update `reference_merger.py` compatibility imports**

Import old public names from new modules:

```python
from references.dedupe import deduplicate, title_similarity
from references.merger import ReferenceMerger, assess_reference_quality, renumber, select_top
from references.scoring import compute_score
```

Then update `main()` to use `ReferenceMerger` internally while preserving CLI args and output text.

**Step 6: Run merger tests**

```bash
python scripts/test_references_merger_service.py
python scripts/test_reference_merger.py
```

Expected: PASS.

---

### Task 5: 迁移格式化器与搜索器

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/formatters.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/searchers.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_engine.py`
- Test: `.claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_search_formatters.py`

**Step 1: Write failing tests for new imports**

Create `.claude/skills/thesis-creator/scripts/test_references_search_formatters.py`:

```python
# -*- coding: utf-8 -*-

import unittest

from references.formatters import ReferenceFormatter
from references.models import VerifiedReference
from references.searchers import CrossRefSearcher, MultiSourceSearcher, OpenAlexSearcher, SemanticScholarSearcher


class ReferencesSearchFormattersTest(unittest.TestCase):
    def test_yaml_formatter_keeps_metadata_only_reference(self):
        ref = VerifiedReference(title="中文文献", authors=["作者甲"], year=2024, doi="", doi_url="")
        ref.verification_status = "verified_metadata_only"
        ref.verification_reason = "文献本身没有 DOI，但元数据匹配通过"
        ref.metadata_verified = True
        ref.doi_reachable = False

        yaml_text = ReferenceFormatter.format_yaml([ref], pool_id="demo")

        self.assertIn('verification_status: "verified_metadata_only"', yaml_text)
        self.assertIn('title: "中文文献"', yaml_text)

    def test_searcher_classes_are_importable(self):
        self.assertIsNotNone(SemanticScholarSearcher)
        self.assertIsNotNone(CrossRefSearcher)
        self.assertIsNotNone(OpenAlexSearcher)
        self.assertIsNotNone(MultiSourceSearcher)
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_search_formatters.py
```

Expected: FAIL because classes are not migrated.

**Step 3: Move formatter**

Move `ReferenceFormatter` from `reference_engine.py` into `references/formatters.py`.

Keep `format_yaml()` output identical because `test_reference_engine_verification_states.py` checks exact substrings.

**Step 4: Move searchers**

Move these classes from `reference_engine.py` into `references/searchers.py`:

- `SemanticScholarSearcher`
- `CrossRefSearcher`
- `OpenAlexSearcher`
- `MultiSourceSearcher`

Also move `safe_print()` if searchers depend on it. If only searchers use it, place it in `searchers.py` and assign local `print = safe_print` there.

**Step 5: Keep wrapper compatibility in `reference_engine.py`**

Import and re-export:

```python
from references.formatters import ReferenceFormatter
from references.models import VerifiedReference
from references.searchers import CrossRefSearcher, MultiSourceSearcher, OpenAlexSearcher, SemanticScholarSearcher
```

Keep `search_and_format()` and `main()` in `reference_engine.py` for this task unless they become tiny enough to move safely.

**Step 6: Run tests**

```bash
python scripts/test_references_search_formatters.py
python scripts/test_reference_engine_verification_states.py
```

Expected: PASS.

---

### Task 6: 迁移文献池管理器

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/pool.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_pool.py`

**Step 1: Write failing pool tests**

Create `.claude/skills/thesis-creator/scripts/test_references_pool.py`:

```python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from references.pool import VerifiedReferencePool


class ReferencesPoolTest(unittest.TestCase):
    def test_add_references_persists_pool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pool_path = Path(tmpdir) / "verified_references.yaml"
            pool = VerifiedReferencePool(str(pool_path))

            added = pool.add_references([
                {
                    "id": "ref_001",
                    "title": "中文文献",
                    "authors": ["作者甲"],
                    "year": 2024,
                    "doi": "",
                    "doi_url": "",
                    "language": "zh",
                }
            ], chapter="第一章")

            loaded = VerifiedReferencePool(str(pool_path))

        self.assertEqual(1, added)
        self.assertIn("ref_001", loaded.references)
        self.assertEqual(["ref_001"], loaded.groups["第一章"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_pool.py
```

Expected: FAIL because `VerifiedReferencePool` has not been migrated.

**Step 3: Move `VerifiedReferencePool`**

Move class body from `verified_reference_pool.py` into `references/pool.py`.

Import `PoolReference` from `references.models`.

Preserve defaults:

```python
DEFAULT_POOL_FILE = "workspace/references/verified_references.yaml"
MAX_USE_PER_REFERENCE = 1
```

**Step 4: Keep wrapper compatibility**

In `verified_reference_pool.py`, import:

```python
from references.models import PoolReference
from references.pool import VerifiedReferencePool
```

Keep `main()` as CLI entry for now.

**Step 5: Run tests**

```bash
python scripts/test_references_pool.py
```

Expected: PASS.

---

### Task 7: 迁移验证器

**Files:**
- Modify: `.claude/skills/thesis-creator/scripts/references/validator.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_validator.py`
- Test: `.claude/skills/thesis-creator/scripts/test_reference_validator.py`

**Step 1: Write import test for new validator module**

Append or create `.claude/skills/thesis-creator/scripts/test_references_validator_import.py`:

```python
# -*- coding: utf-8 -*-

import unittest

from references.models import Reference
from references.validator import ReferenceValidator


class ReferencesValidatorImportTest(unittest.TestCase):
    def test_validator_is_importable_from_package(self):
        validator = ReferenceValidator(enable_online_validation=False)
        ref = Reference(
            index=1,
            raw_text="[1] 示例参考文献",
            ref_type="J",
            authors=["张三"],
            title="基于知识图谱的推荐系统研究",
            journal="计算机工程",
            year=2024,
            volume=None,
            issue=None,
            pages=None,
            publisher=None,
            doi="",
            url=None,
        )

        self.assertFalse(validator._has_broken_link_issue(ref))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_validator_import.py
```

Expected: FAIL because `ReferenceValidator` not migrated.

**Step 3: Move `ReferenceValidator`**

Move `ReferenceValidator` class from `reference_validator.py` into `references/validator.py`.

Update imports inside new module:

```python
from references.models import Reference
from references.searchers import CrossRefSearcher, OpenAlexSearcher
```

Keep fallback import for legacy `reference_searcher` only if current behavior requires it.

**Step 4: Keep wrapper compatibility**

In `reference_validator.py`, import:

```python
from references.models import Reference
from references.validator import ReferenceValidator
```

Keep `main()` in wrapper.

**Step 5: Run validation tests**

```bash
python scripts/test_references_validator_import.py
python scripts/test_reference_validator.py
```

Expected: PASS.

---

### Task 8: 提取 CLI 子模块并瘦身旧入口

**Files:**
- Create: `.claude/skills/thesis-creator/scripts/references/cli/merge.py`
- Create: `.claude/skills/thesis-creator/scripts/references/cli/search.py`
- Create: `.claude/skills/thesis-creator/scripts/references/cli/pool.py`
- Create: `.claude/skills/thesis-creator/scripts/references/cli/validate.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_merger.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_engine.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/verified_reference_pool.py`
- Modify: `.claude/skills/thesis-creator/scripts/references/reference_validator.py`
- Test: `.claude/skills/thesis-creator/scripts/test_references_cli_imports.py`

**Step 1: Write failing CLI import tests**

Create `.claude/skills/thesis-creator/scripts/test_references_cli_imports.py`:

```python
# -*- coding: utf-8 -*-

import unittest


class ReferencesCliImportsTest(unittest.TestCase):
    def test_cli_modules_export_main(self):
        from references.cli import merge, pool, search, validate

        self.assertTrue(callable(merge.main))
        self.assertTrue(callable(pool.main))
        self.assertTrue(callable(search.main))
        self.assertTrue(callable(validate.main))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python scripts/test_references_cli_imports.py
```

Expected: FAIL because CLI modules do not exist.

**Step 3: Move old `main()` functions**

Move each wrapper's `main()` implementation into matching CLI module:

- `reference_merger.py:261` → `references/cli/merge.py`
- `reference_engine.py:1155` → `references/cli/search.py`
- `verified_reference_pool.py:537` → `references/cli/pool.py`
- `reference_validator.py:1076` → `references/cli/validate.py`

Keep command-line arguments unchanged in this task.

**Step 4: Replace old entry files with thin wrappers**

Each old file should re-export compatible public symbols and delegate CLI:

```python
# reference_merger.py
from references.dedupe import deduplicate, title_similarity
from references.io import load_yaml_references as load_yaml_file
from references.io import load_yaml_references_from_directory as load_from_directory
from references.io import save_reference_pool_yaml as save_yaml
from references.language import ZH_RATIO_MIN, check_language_balance, is_language as _is_language
from references.merger import ReferenceMerger, assess_reference_quality, renumber, select_top
from references.scoring import compute_score
from references.cli.merge import main

if __name__ == "__main__":
    main()
```

Equivalent pattern for other wrappers.

**Step 5: Run CLI import and legacy tests**

```bash
python scripts/test_references_cli_imports.py
python scripts/test_reference_merger.py
python scripts/test_reference_engine_verification_states.py
python scripts/test_reference_validator.py
```

Expected: PASS.

---

### Task 9: 回归现有文献相关测试

**Files:**
- No source changes unless tests fail.

**Step 1: Run targeted tests**

From `.claude/skills/thesis-creator`:

```bash
python scripts/test_reference_merger.py
python scripts/test_reference_engine_verification_states.py
python scripts/test_reference_validator.py
python scripts/test_merge_drafts_references.py
python scripts/test_references_package_imports.py
python scripts/test_references_models.py
python scripts/test_references_io_language.py
python scripts/test_references_merger_service.py
python scripts/test_references_search_formatters.py
python scripts/test_references_pool.py
python scripts/test_references_validator_import.py
python scripts/test_references_cli_imports.py
```

Expected: all PASS.

**Step 2: Fix only regression causes**

If a test fails, fix the new package module or wrapper causing the mismatch. Do not change expected behavior unless the old behavior was demonstrably broken and user approves.

**Step 3: Run a smoke CLI command**

Use a temporary directory with tiny YAML input:

```bash
python scripts/references/reference_merger.py -i /tmp/reference-smoke --top 2 -o /tmp/reference-smoke/verified_references.yaml
```

On Windows Git Bash, use an available temp path if `/tmp` does not exist.

Expected: command completes and writes `verified_references.yaml`.

---

### Task 10: 架构文档与上下文同步

**Files:**
- Modify: `.claude/skills/thesis-creator/README.md`
- Modify: `.claude/skills/thesis-creator/docs/usage_guide.md`
- Modify: `.vibe-context/project/modules/reference_pipeline.yaml`
- Optional Modify: `.claude/skills/thesis-creator/docs/CHANGELOG.md`

**Step 1: Update README structure section**

Add `scripts/references/` as the main implementation package and mark old files as compatible CLI entry points.

Expected wording in Chinese:

```markdown
│   ├── references/              # 参考文献领域包：模型、搜索、合并、文献池、验证
│   │   ├── models.py            # 统一文献数据结构
│   │   ├── searchers.py         # 多源学术搜索
│   │   ├── merger.py            # 合并、去重、筛选
│   │   ├── pool.py              # 已验证文献池管理
│   │   ├── validator.py         # 参考文献解析与校验
│   │   └── cli/                 # CLI 子命令实现
│   ├── reference_engine.py      # 兼容入口，委托 references.cli.search
│   ├── reference_merger.py      # 兼容入口，委托 references.cli.merge
```

**Step 2: Update usage guide**

Keep existing commands unchanged, but add note:

```markdown
> 文献相关命令保留旧脚本入口；内部实现已模块化到 `scripts/references/`，后续扩展优先修改领域包。
```

**Step 3: Update Vibe Context module doc**

Modify `.vibe-context/project/modules/reference_pipeline.yaml` to reflect new package boundary.

**Step 4: Run docs grep check**

Use Grep tool, not shell grep, to verify stale claims about implementation-only old scripts if needed.

Expected: docs mention both new package and legacy CLI compatibility.

---

### Task 11: Final verification

**Files:**
- No source changes unless verification finds issues.

**Step 1: Run all targeted tests again**

```bash
python scripts/test_reference_merger.py
python scripts/test_reference_engine_verification_states.py
python scripts/test_reference_validator.py
python scripts/test_merge_drafts_references.py
python scripts/test_references_package_imports.py
python scripts/test_references_models.py
python scripts/test_references_io_language.py
python scripts/test_references_merger_service.py
python scripts/test_references_search_formatters.py
python scripts/test_references_pool.py
python scripts/test_references_validator_import.py
python scripts/test_references_cli_imports.py
```

Expected: all PASS.

**Step 2: Request code review**

Use `superpowers:requesting-code-review` or the available project code review agent after implementation completes.

Review focus:

- 是否仍有重复实体定义。
- 旧 CLI 入口是否兼容。
- 新包模块边界是否清晰。
- 是否引入网络调用测试或不稳定测试。
- 是否误改文献真实性和语种比例规则。

**Step 3: Report completion**

Summarize:

- 新增 `scripts/references/` 包。
- 旧入口兼容情况。
- 测试命令与结果。
- 文档更新情况。
