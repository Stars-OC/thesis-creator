# DOCX 自动目录设计说明

## 背景

`thesis-creator` 当前通过 `scripts/document_exporter/docx_writer.py` 使用 `python-docx` 将 Markdown 终稿导出为 Word 文档。现有实现已经把 Markdown 标题映射到 Word `Heading 1` 至 `Heading 4` 样式，因此 Word 导航窗格、标题折叠和手动插入目录具备基础条件，但导出的 `.docx` 文件本身没有预置 Word 原生目录字段。

## 用户确认的目标

导出 `论文终稿.docx` 时，自动在摘要/Abstract 后、第一章前插入 Word 原生自动目录。

## 推荐方案

采用 OOXML 字段方式在 `docx_writer.py` 中插入 TOC 字段，字段指令为：

```text
TOC \o "1-4" \h \z \u
```

含义：

- `\o "1-4"`：收录大纲级别 1-4，即 `Heading 1` 至 `Heading 4`。
- `\h`：目录项使用超链接。
- `\z`：Web 布局隐藏制表符和页码。
- `\u`：使用段落大纲级别。

## 插入位置

目录插入在摘要/Abstract 后、第一章或第一个正文 Heading 1 前。

判定规则：

1. 遍历解析后的 Markdown 元素。
2. 记录是否已看到摘要类标题：`摘要`、`Abstract`。
3. 当遇到第一个非摘要类 `h1` 标题，且目录尚未插入时，先插入目录页。
4. 目录页后添加分页符，再写入正文标题。

## 不做的事情

- 不手写目录文本。
- 不计算页码。
- 不引入 Pandoc 或 docx-js。
- 不改变现有 Heading 样式生成逻辑。

## 限制说明

`python-docx` 可以写入 Word TOC 字段，但不能计算和刷新目录页码。用户打开 Word/WPS 后，需要执行“更新域/更新目录”来显示或刷新页码。这是 Word 原生自动目录字段的正常机制。

## 影响范围

主要修改：

- `scripts/document_exporter/docx_writer.py`

新增测试：

- `test/test_document_exporter_toc.py`

后续文档同步：

- `.vibe-context/project/modules/document_exporter.yaml` 增加自动目录能力说明。
