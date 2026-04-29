# Step 7: 合并与检测

> **状态管理(强制执行)**：
> 1. 启动前：`python scripts/status_manager.py thesis-workspace/ --ensure`
> 2. 启动时：`python scripts/status_manager.py thesis-workspace/ --check-step 7`
> 3. 前置条件通过后：`--update-step 7 --action start`
> 4. 完成后：`--update-step 7 --action complete`
>
> **统一入口(推荐)**：`python scripts/lifecycle.py --workspace thesis-workspace/ --step 7 --event start|complete`

---

## 流程顺序(重要)

```mermaid
flowchart TD
    A[Step 7: 合并章节] --> B[重排引用并生成参考文献]
    B --> C[参考文献在线校验与404检查]
    C --> D[AIGC 检测]
    D --> E{检测通过?}
    E -->|是| F[Step 8: 图片生成]
    E -->|否| G[返回 Step 5/6 改写与复检]
    G --> D
    F --> H[Step 9: 导出 Word]
    H --> I[✅ 完成]
```

> **⚠️ 流程顺序**：合并 → 引用重排/生成参考文献 → 在线校验 → AIGC 检测 → 图片生成 → 导出 Word

---

## ⚠️ 合并规则(铁律)

> **禁止使用 LLM 上下文合并文档！**
>
> LLM 上下文合并会导致：
> - 内容丢失(上下文窗口限制)
> - 格式混乱(Markdown 标记错乱)
> - 章节顺序错误
> - 章节拼接顺序错误
>
> **必须使用 `scripts/merge_drafts.py` Python 脚本合并！**

---

## 7.1 章节合并

使用 `scripts/merge_drafts.py` 合并各章节文件：

```bash
# 合并所有章节，并完成引用重排与参考文献生成
python scripts/merge_drafts.py -i workspace/drafts/ -o workspace/final/论文终稿.md --references workspace/references/verified_references.yaml --outline workspace/outline.md

# 输出简要结果（不打印详细报告）
python scripts/merge_drafts.py -i workspace/drafts/ -o workspace/final/论文终稿.md --references workspace/references/verified_references.yaml --outline workspace/outline.md --no-report
```

### 合并脚本执行的关键操作

1. **自动匹配章节文件名并按顺序拼接**（支持 `chapter_1.md` / `chapter-1.md` / `chapter_1_xxx.md` / `第1章xxx.md`）
2. **清理章节冗余分隔符和空白**，统一版式
3. **自动补充分页标记**（章节间分页）
4. **按正文出现顺序重排临时引用编号**（`[ref_001] → [1]`）
5. **从 `verified_references.yaml` 生成独立参考文献文件**（`workspace/drafts/参考文献.md`）
6. **生成最终 Markdown 文件**（`workspace/final/论文终稿.md`）

---

## 7.2 参考文献在线校验

> **硬约束**：`workspace/drafts/参考文献.md` 生成后，进入 AIGC 检测前必须执行在线验证与 404 检查。

```bash
python scripts/reference_validator.py workspace/drafts/参考文献.md --validate-online --check-404
```

- 允许继续的状态：`verified_doi`、`verified_metadata_only`、`broken_doi_metadata_ok`
- 必须阻断并先修复的状态：`missing_doi_unverified`、`invalid_reference`
- 若存在 `missing_doi_unverified` 或 `invalid_reference`：先替换文献或回退 Step 6 审校后，再重新执行 Step 7。
- 仅当参考文献在线校验通过后，才允许继续 AIGC 检测。

---

## 7.3 AIGC 检测

调用 `scripts/aigc_detect.py` 进行检测：

```bash
python scripts/aigc_detect.py workspace/final/论文终稿.md
```

---

## 7.4 检测不通过处理

- 若 AIGC 检测不通过：必须返回 Step 5/6 进行人性化改写与审校后，再回到 Step 7 复检。
- **AIGC 未通过时，禁止进入 Step 8 图片生成或 Step 9 导出。**
- 检测通过后：进入 Step 8 图片生成。

---

## 输出文件

- `workspace/final/论文终稿.md` - 终稿(Markdown)
- `workspace/drafts/参考文献.md` - 独立参考文献列表（GB/T 7714）
- `workspace/reports/reference_validation_*.md` - 参考文献在线校验报告

