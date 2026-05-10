# 测试目录索引

本目录统一存放 `thesis-creator` skill 的 Python 单元测试。测试文件从原 `scripts/test_*.py` 迁移至此，运行时通过文件顶部的 `SCRIPTS_DIR` 将 `scripts/` 加入 `sys.path`。

## 运行方式

```bash
python -m unittest discover -s .claude/skills/thesis-creator/test -p "test_*.py"
```

## 主要测试分组

| 文件模式 | 覆盖范围 |
|---|---|
| `test_document_exporter_*.py` | 文档导出、图片预检查、DOCX 最小导出。 |
| `test_chart_*.py`、`test_charts_*.py` | 图表生成、渲染、清单、源码和 Markdown 回填。 |
| `test_reference_*.py`、`test_verified_reference_pool.py` | 文献搜索、验证、合并和文献池。 |
| `test_aigc_modules.py`、`test_reduce_workflow_*.py` | AIGC 检测和降重流程。 |
| `test_lifecycle_workspace_check.py`、`test_logger_replacements.py` | 工作区生命周期与日志替换记录。 |
| `test_terminal_encoding.py` | 终端编码与 subprocess 文本解码配置。 |
| `test_workflow_p0_repairs.py`、`test_content_requirements.py` | 工作流约束与内容要求。 |

## 新增测试约定

- 新测试文件使用 `test_*.py` 命名。
- 顶部统一加入 `scripts/` 路径，不要把测试文件放回 `scripts/`。
- 文档导出相关测试应导入 `document_exporter` 包内子模块，不再导入旧的 `document_exporter.py` 单文件。
