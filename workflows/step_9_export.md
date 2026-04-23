# Step 9: 文档导出与图片插入

> **自动将图片插入到 Word 文档，并添加规范图注**

---

## 执行流程

```mermaid
flowchart TD
    A[读取终稿 Markdown] --> B[解析文档结构]
    B --> C[识别图片引用]
    C --> D[创建 Word 文档]
    D --> E[写入标题/正文]
    E --> F{遇到图片引用?}
    F -->|是| G[插入图片居中显示]
    G --> H[添加图注五号宋体]
    H --> F
    F -->|否| I[继续下一个元素]
    I --> J[处理表格/代码块]
    J --> K[保存文档]
    K --> L[输出导出报告]
    L --> M[✅ 完成]
```

---

## 图片插入特性

| 特性 | 说明 | 格式标准 |
|------|------|----------|
| 自动居中 | 图片居中显示 | `doc.add_picture()` + 段落居中 |
| 尺寸控制 | 自动计算，默认最大宽度 14cm | 适合 A4 纸张 |
| 图注格式 | 五号宋体、居中 | 符合学术论文规范 |
| 路径解析 | 支持相对路径，自动 resolve 为绝对路径 | 处理 Windows 反斜杠 |
| 格式检查 | 仅支持 png/jpg/jpeg/gif/bmp/tiff/emf/wmf | 非法格式自动跳过 |
| 失败处理 | 图片不存在/格式不支持时插入红色占位文字 | 不中断导出流程 |

---

## 执行命令

```bash
# 导出 Word 文档（自动插入图片）
python scripts/document_exporter.py --input workspace/final/论文终稿.md --output workspace/final/ --format docx

# 导出 PDF 文档
python scripts/document_exporter.py --input workspace/final/论文终稿.md --output workspace/final/ --format pdf

# 同时导出两种格式
python scripts/document_exporter.py --input workspace/final/论文终稿.md --output workspace/final/ --format both
```

---

## 导出成功示例

```
[信息] 正在读取: workspace/final/论文终稿.md
[成功] Word 文档已保存: workspace/final/论文终稿.docx
[信息] 成功插入 12 张图片
==================================================
[文档导出报告]
输入文件: workspace/final/论文终稿.md
输出目录: workspace/final/
导出时间: 20260411_194041
--------------------------------------------------
DOCX: [成功]
  路径: workspace/final/论文终稿.docx
  图片: 12 张已插入
==================================================
```

---

## 文档格式规范

- 页边距：上下 2.54cm，左右 3.17cm
- 正文字体：宋体 12pt
- 标题字体：黑体，一级标题 14pt，二级标题 12pt
- 行距：1.5 倍行距
- 首行缩进：0.74cm（两个字符）

---

## 输出文件

- `workspace/final/论文终稿.docx` - Word 文档（含图片）
- `workspace/final/论文终稿.pdf` - PDF 文档
- `workspace/final/导出报告.md` - 导出报告