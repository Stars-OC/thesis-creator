# scripts 脚本总索引

本目录存放 thesis-creator Skill 的执行脚本。模型优先从本文件进入，再按任务读取对应模块的 `INDEX.md`。

## 模块目录

| 模块 | 索引 | 职责 |
|---|---|---|
| AIGC | `aigc/INDEX.md` | AIGC 检测与技术论文表达检测 |
| 图表 | `charts/INDEX.md` | 图片需求抽取、源码准备、渲染、回填与验证 |
| 参考文献 | `references/INDEX.md` | 文献搜索、验证、合并、文献池管理 |

## 根目录脚本

| 脚本 | 职责 |
|---|---|
| `lifecycle.py` | 工作区生命周期检查与状态入口 |
| `status_manager.py` | `.thesis-status.json` 状态管理 |
| `logger.py` | 流程日志记录 |
| `merge_drafts.py` | 合并章节草稿、致谢与参考文献 |
| `document_exporter.py` | 导出 Word/PDF 并处理图片插入 |
| `format_checker.py` | 格式检查 |
| `document_reader.py` | 文档读取辅助 |
| `keyword_extractor.py` | 关键词抽取 |
| `chart_generator.py` | 旧图表生成入口，优先使用 `charts/` 模块链路 |
| `chart_renderer.py` | 旧图表渲染入口，优先使用 `charts/render.py` |

## 推荐读取顺序

1. 先读本文件判断任务类型
2. 再读对应模块的 `INDEX.md`
3. 最后只读取需要执行或修改的具体脚本
