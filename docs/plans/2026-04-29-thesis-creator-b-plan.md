# Thesis Creator B 方案改造 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 thesis-creator 改造成以 `[image_N] + references/images.yaml` 为核心的图片链路，同时完成工作区自动初始化、允许无 DOI 的分层文献校验、以及替换记录统一入日志。

**Architecture:** 保留现有 Step 0-9 与主要脚本入口，围绕 Step 0 / Step 4 / Step 8 / Step 9 做中度重构。图片链路由“正文旧图表占位符驱动”切换为“正文图片占位符 + YAML 清单驱动”；DOI 校验由单一链接可达性判断改为“DOI 优先、元数据兜底”的枚举状态模型；替换行为统一通过 logger 记录文本摘要与 JSONL 结构化日志。

**Tech Stack:** Python 3、unittest、PyYAML、python-docx、现有 thesis-creator workflow 文档与 scripts。

---

### Task 1: 更新 Skill 总体入口文档

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py`

**Step 1: 先写/改失败的文档测试**

在 `test_workflow_p0_repairs.py` 新增断言，覆盖：
- Step 0 工作区不存在时直接初始化
- 图片占位符改为 `[image_1]`
- `references/images.yaml` 被列为图片需求清单
- DOI 规则允许“无 DOI 但元数据通过”

示例断言：
```python
self.assertIn("工作区不存在直接初始化", content)
self.assertIn("[image_1]", content)
self.assertIn("references/images.yaml", content)
self.assertIn("verified_metadata_only", content)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: FAIL，提示 `SKILL.md` 中缺少新规则文案。

**Step 3: 最小化修改 `SKILL.md`**

修改点：
- 触发与 Step 0 说明中，明确“工作区不存在时直接初始化工作区，再引导填写 `references/prompt/background.md`”
- 将 Step 4/8 的图片链路改为 `[image_N] + references/images.yaml`
- 将文献校验规则改为：`verified_doi / verified_metadata_only / broken_doi_metadata_ok / missing_doi_unverified / invalid_reference`
- 将“替换记录”落点改成日志

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add SKILL.md scripts/test_workflow_p0_repairs.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "docs: align thesis skill entry rules"
```

---

### Task 2: 更新 Step 0 初始化流程文档与校验点

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_0_init.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py`

**Step 1: 扩展失败测试**

在 `test_workflow_p0_repairs.py` 新增对 `step_0_init.md` 的断言：
```python
content = (WORKFLOWS_DIR / "step_0_init.md").read_text(encoding="utf-8")
self.assertIn("工作区不存在时直接初始化", content)
self.assertIn("填写 references/prompt/background.md", content)
self.assertNotIn("是否初始化工作区", content)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: FAIL

**Step 3: 修改 `step_0_init.md`**

修改点：
- 流程图和详细步骤中取消“初始化前再问用户”的语义
- 明确自动创建工作区、README、logs、background.md
- 初始化完成后的主提示聚焦“请填写 `background.md` 再继续”

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add workflows/step_0_init.md scripts/test_workflow_p0_repairs.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "docs: make workspace init automatic"
```

---

### Task 3: 更新文献工作流文档与 DOI 状态口径

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/reference_workflow.md`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_7_merge_detect.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py`

**Step 1: 先写失败测试**

新增断言覆盖：
- 允许无 DOI 的真实文献
- 明确解释“为什么 DOI 链接不存在”
- Step 7 合并前只阻断 `missing_doi_unverified` 与 `invalid_reference`

示例：
```python
content = (WORKFLOWS_DIR / "reference_workflow.md").read_text(encoding="utf-8")
self.assertIn("verified_metadata_only", content)
self.assertIn("broken_doi_metadata_ok", content)
self.assertIn("文献本身没有 DOI", content)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: FAIL

**Step 3: 修改文档**

修改点：
- `reference_workflow.md` 中将 DOI 校验逻辑改成分层状态模型
- 加入“无 DOI != 假文献”的解释
- `step_7_merge_detect.md` 中将阻断条件改成状态驱动

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add workflows/reference_workflow.md workflows/step_7_merge_detect.md scripts/test_workflow_p0_repairs.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "docs: adopt layered reference verification states"
```

---

### Task 4: 更新 Step 4 写作文档为 `[image_N] + images.yaml`

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_4_writing.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py`

**Step 1: 写失败测试**

新增断言：
```python
content = (WORKFLOWS_DIR / "step_4_writing.md").read_text(encoding="utf-8")
self.assertIn("[image_1]", content)
self.assertIn("references/images.yaml", content)
self.assertIn("Step 4 只负责记录图片需求", content)
self.assertNotIn("<!-- 图表占位符", content)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: FAIL

**Step 3: 修改 `step_4_writing.md`**

修改点：
- 系统设计章节图表规则改用 `[image_N]`
- 新增 `references/images.yaml` 文件格式与字段说明
- 区分 `source=ai` 与 `source=user`
- 说明 Step 4 只负责记录需求，不负责最终生成图片

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add workflows/step_4_writing.md scripts/test_workflow_p0_repairs.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "docs: switch writing workflow to image manifest"
```

---

### Task 5: 更新 Step 8/9 文档为清单驱动图片生成与导出前阻断

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_8_image.md`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/step_9_export.md`
- Test: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py`

**Step 1: 写失败测试**

新增断言：
```python
step8 = (WORKFLOWS_DIR / "step_8_image.md").read_text(encoding="utf-8")
step9 = (WORKFLOWS_DIR / "step_9_export.md").read_text(encoding="utf-8")
self.assertIn("读取 references/images.yaml", step8)
self.assertIn("将 [image_N] 替换为 Markdown 图片引用", step8)
self.assertIn("正文不得残留 [image_N]", step9)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: FAIL

**Step 3: 修改文档**

修改点：
- `step_8_image.md` 改为：扫描正文占位符 → 读取 `images.yaml` → 一致性校验 → 生成/校验图片 → 回填 Markdown
- `step_9_export.md` 改为：导出前禁止残留 `[image_N]`

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_workflow_p0_repairs.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add workflows/step_8_image.md workflows/step_9_export.md scripts/test_workflow_p0_repairs.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "docs: define manifest-driven image and export flow"
```

---

### Task 6: 为 logger 增加结构化替换日志能力

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/logger.py`
- Create: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_logger_replacements.py`

**Step 1: 先写失败测试**

创建 `test_logger_replacements.py`，覆盖：
- 传入工作区时能在对应 `logs/<session>/replacements.jsonl` 追加记录
- 普通日志仍可继续输出摘要

示例测试骨架：
```python
logger = init_logger(workspace_path=str(workspace))
logger.record_replacement(
    step=5,
    operation="synonym_replace",
    file="workspace/drafts/chapter_4.md",
    before="首先",
    after="先",
    reason="降低模板化表达",
)
assert replacement_log.exists()
assert "synonym_replace" in replacement_log.read_text(encoding="utf-8")
```

**Step 2: 运行测试确认失败**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_logger_replacements.py"
```
Expected: FAIL，提示缺少 `record_replacement` 或日志文件未生成。

**Step 3: 写最小实现**

在 `logger.py` 中：
- 为 `ThesisLogger` 增加 `record_replacement(...)`
- 自动在当前会话日志目录下维护 `replacements.jsonl`
- 追加 JSON 行记录：`timestamp / step / operation / file / rule_id / before / after / reason / success`
- 同时输出一条简洁 `info`

**Step 4: 运行测试确认通过**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_logger_replacements.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/logger.py scripts/test_logger_replacements.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: add structured replacement logging"
```

---

### Task 7: 改造 reference_validator 为枚举验证状态

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/reference_validator.py`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_validator.py`

**Step 1: 先写失败测试**

在现有 `test_reference_validator.py` 增加：
- 无 DOI 但 OpenAlex / CrossRef 标题匹配时，状态为 `verified_metadata_only`
- DOI 404 但元数据匹配时，状态为 `broken_doi_metadata_ok`
- 无 DOI 且无法匹配时，状态为 `missing_doi_unverified`

示例：
```python
self.assertEqual(ref.verification_status, "verified_metadata_only")
self.assertEqual(ref.verification_status, "broken_doi_metadata_ok")
self.assertEqual(ref.verification_status, "missing_doi_unverified")
```

**Step 2: 运行测试确认失败**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_validator.py"
```
Expected: FAIL

**Step 3: 最小化实现**

在 `reference_validator.py` 中：
- 为 `Reference` 增加 `verification_status`、`verification_reason`、`metadata_verified`、`doi_reachable`
- 调整 `_validate_online()` / `validate_all()`：
  - DOI 通过 → `verified_doi`
  - 无 DOI 但标题/作者/年份足够匹配 → `verified_metadata_only`
  - DOI 404 但元数据匹配 → `broken_doi_metadata_ok`
  - 无 DOI 且无匹配 → `missing_doi_unverified`
  - 明显错误 → `invalid_reference`
- 统计报告用新状态驱动

**Step 4: 运行测试确认通过**

Run:
```bash
python "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_validator.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/reference_validator.py scripts/test_reference_validator.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: add layered reference verification states"
```

---

### Task 8: 调整 reference_engine 输出以支持无 DOI 合法状态

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/reference_engine.py`
- Create: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py`

**Step 1: 先写失败测试**

新增测试覆盖：
- `VerifiedReference` 可序列化 `source_url`、`verification_status`、`verification_reason`
- 无 DOI 结果不会被立即过滤掉

示例：
```python
ref = VerifiedReference(title="t", authors=["a"], year=2024, doi="", doi_url="")
ref.verification_status = "verified_metadata_only"
self.assertEqual(ref.to_dict()["verification_status"], "verified_metadata_only")
```

**Step 2: 运行测试确认失败**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py"
```
Expected: FAIL

**Step 3: 写最小实现**

在 `reference_engine.py` 中：
- 扩展 `VerifiedReference` 数据结构，增加 `source_url`、`verification_status`、`verification_reason`、`metadata_verified`、`doi_reachable`
- 搜索阶段对无 DOI 结果保留，由后续验证决定状态

**Step 4: 运行测试确认通过**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_reference_engine_verification_states.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/reference_engine.py scripts/test_reference_engine_verification_states.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: keep metadata-only reference candidates"
```

---

### Task 9: 改造 chart_generator 解析 `[image_N]` 与 `images.yaml`

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_image_validation.py`
- Create: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_manifest_flow.py`

**Step 1: 先写失败测试**

在新测试中覆盖：
- 从 Markdown 提取 `[image_1]`、`[image_2]`
- 从 `references/images.yaml` 读取对应记录
- 正文有占位符、YAML 无记录时报错
- `source=ai` 且缺 `description` 报错
- `source=user` 仅登记，不自动生成图代码

示例：
```python
placeholders = generator.parse_image_placeholders(markdown)
self.assertEqual(placeholders, ["image_1", "image_2"])
manifest = generator.load_image_manifest(manifest_path)
self.assertEqual(manifest[0]["id"], "image_1")
```

**Step 2: 运行测试确认失败**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_image_validation.py" "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_manifest_flow.py"
```
Expected: FAIL

**Step 3: 写最小实现**

在 `chart_generator.py` 中：
- 增加 `IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\[image_(\d+)\]")`
- 增加 `parse_image_placeholders(content)`
- 增加 `load_image_manifest(path)`
- 增加 `validate_image_manifest(placeholders, manifest)`
- 保留单入口，但将旧 `parse_placeholders()` 的职责迁移到新链路
- 完整性校验改为统计残留 `[image_N]`，不再统计旧 HTML 图表占位符

**Step 4: 运行测试确认通过**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_image_validation.py" "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_manifest_flow.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/chart_generator.py scripts/test_chart_generator_image_validation.py scripts/test_chart_generator_manifest_flow.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: parse image placeholders from manifest workflow"
```

---

### Task 10: 在 Step 8 中记录图片占位符替换日志并回填 Markdown

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/chart_generator.py`
- Create: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_markdown_replace.py`

**Step 1: 先写失败测试**

新增测试覆盖：
- `[image_1]` 可替换为 `![图4-1 系统总体架构图](images/图4-1_系统总体架构图.png)`
- 调用 `record_replacement()` 记录 `placeholder_replace`
- 更新 manifest 中 `status=inserted`

**Step 2: 运行测试确认失败**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_markdown_replace.py"
```
Expected: FAIL

**Step 3: 写最小实现**

在 `chart_generator.py` 中：
- 增加替换函数，如 `replace_image_placeholders(content, manifest_items)`
- 每次替换调用 logger 的 `record_replacement(step=8, operation="placeholder_replace", ...)`
- 更新 `status` 与 `output_path`

**Step 4: 运行测试确认通过**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_markdown_replace.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/chart_generator.py scripts/test_chart_generator_markdown_replace.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: log and replace image placeholders"
```

---

### Task 11: 改造 document_exporter 做导出前强校验

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/document_exporter.py`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_table.py`
- Create: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_preflight.py`

**Step 1: 先写失败测试**

覆盖：
- 正文残留 `[image_1]` 时拒绝导出
- Markdown 图片路径缺失时拒绝导出
- 全部图片存在时通过预检查

示例：
```python
ok, message = preflight_validate_images(markdown_path)
self.assertFalse(ok)
self.assertIn("[image_1]", message)
```

**Step 2: 运行测试确认失败**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_table.py" "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_preflight.py"
```
Expected: FAIL

**Step 3: 写最小实现**

在 `document_exporter.py` 中：
- 增加导出前校验函数（例如 `preflight_validate_images`）
- 检查残留 `[image_N]`
- 检查 `![]()` 引用的图片文件存在且非空
- 校验失败时阻断导出命令路径

**Step 4: 运行测试确认通过**

Run:
```bash
python -m unittest "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_table.py" "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_document_exporter_preflight.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts/document_exporter.py scripts/test_document_exporter_table.py scripts/test_document_exporter_preflight.py
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "feat: block export when image placeholders remain"
```

---

### Task 12: 完整回归测试与旧测试迁移收尾

**Files:**
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_generator_er_diagram.py`
- Modify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/test_chart_renderer_report.py`
- Modify/Delete as needed: any old placeholder-format-specific tests

**Step 1: 先整理需要迁移/删除的测试清单**

检查以下测试是否仍依赖旧 HTML 图表占位符：
- `scripts/test_chart_generator_image_validation.py`
- `scripts/test_chart_generator_er_diagram.py`
- `scripts/test_chart_renderer_report.py`
- 其他包含 `<!-- 图表占位符` 的测试文件

**Step 2: 运行完整测试集，记录失败项**

Run:
```bash
python -m unittest discover -s "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts" -p "test_*.py"
```
Expected: 部分 FAIL，列出仍依赖旧格式的测试。

**Step 3: 最小化迁移/删除旧测试**

- 迁移能保留业务价值的测试到 `[image_N] + images.yaml` 链路
- 删除纯粹绑定旧占位符语法、且已无业务价值的测试
- 保留 ER 图、报告、渲染结果等仍然有效的能力测试

**Step 4: 重新运行完整回归测试**

Run:
```bash
python -m unittest discover -s "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts" -p "test_*.py"
```
Expected: PASS

**Step 5: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add scripts
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "test: migrate regression suite to image manifest flow"
```

---

### Task 13: 手工验收文档与实现一致性

**Files:**
- Verify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/SKILL.md`
- Verify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/workflows/*.md`
- Verify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts/*.py`
- Verify: `E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/docs/plans/2026-04-29-thesis-creator-b-plan.md`

**Step 1: 手动核对关键口径**

逐项检查：
- Step 0 自动初始化是否与文档一致
- `[image_N] + references/images.yaml` 是否在文档、解析、导出前校验中一致
- DOI 枚举状态是否在 workflow 与脚本中一致
- 替换日志是否覆盖文本替换与图片占位符替换

**Step 2: 运行完整测试作为最终验收**

Run:
```bash
python -m unittest discover -s "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator/scripts" -p "test_*.py"
```
Expected: PASS

**Step 3: 记录最终变更摘要**

在本次实现的 PR / 交付说明中列出：
- 改动文件
- 新增测试
- 删除/迁移的旧测试
- 已知未覆盖边界（若有）

**Step 4: Commit**

```bash
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" add .
git -C "E:/AIAgent/thesis-creator/.claude/skills/thesis-creator" commit -m "refactor: complete thesis creator manifest workflow migration"
```
