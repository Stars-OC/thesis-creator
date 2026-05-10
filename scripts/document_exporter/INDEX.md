# document_exporter 模块索引

文档导出模块用于将论文 Markdown 终稿导出为 DOCX/PDF，并在 DOCX 中处理标题、正文、表格、图片与图注。

## 入口

- `__main__.py`：支持 `PYTHONPATH=scripts python -m document_exporter ...`。
- `cli.py`：解析命令行参数并打印导出报告。
- `__init__.py`：导出 `export_document` 作为包级 API。

## 模块职责

| 文件 | 职责 |
|---|---|
| `config.py` | 读取 `.thesis-config.yaml` 中的格式配置。 |
| `markdown.py` | 清理 Markdown、移除导出用 DOI 链接、解析 Markdown 结构。 |
| `preflight.py` | 导出前检查图片占位符、用户待补图片和 Markdown 图片文件。 |
| `docx_writer.py` | 写入 DOCX，处理字体、段落、标题、表格、图片、图注与分页符。 |
| `pdf_converter.py` | 将 DOCX 转换为 PDF，按 `docx2pdf`、LibreOffice、Word COM 顺序尝试。 |
| `exporter.py` | 编排 DOCX/PDF 导出流程并返回结果字典。 |

## 推荐命令

```bash
PYTHONPATH=scripts python -m document_exporter --input workspace/final/论文终稿.md --output workspace/final/ --format docx
```

## 测试位置

相关测试位于 `test/`：

- `test_document_exporter_preflight.py`
- `test_document_exporter_table.py`
- `test_terminal_encoding.py`
