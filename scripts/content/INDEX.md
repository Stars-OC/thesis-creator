# content 内容处理脚本索引

本目录负责论文正文内容的读取、关键词抽取、格式检查和终稿合并。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `merge_drafts.py` | 合并章节草稿、摘要、致谢与参考文献，生成终稿 Markdown |
| `document_reader.py` | 读取 Markdown、DOCX、PDF 等输入文档并抽取文本内容 |
| `format_checker.py` | 检查论文格式、章节结构、字数与规范性问题 |
| `keyword_extractor.py` | 从论文主题、背景或正文中抽取关键词，辅助检索和写作 |

## 推荐命令

```bash
python scripts/content/merge_drafts.py thesis-workspace/workspace/drafts --outline thesis-workspace/workspace/outline.md --output thesis-workspace/workspace/final/论文终稿.md
python scripts/content/format_checker.py thesis-workspace/workspace/final/论文终稿.md
```
