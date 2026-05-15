# scripts 脚本总索引

本目录存放 thesis-creator Skill 的执行脚本。模型优先从本文件进入，再按任务读取对应模块的 `INDEX.md`。

## 模块目录

| 模块 | 索引 | 职责 |
|---|---|---|
| Core | `core/INDEX.md` | 生命周期、状态管理、日志、终端编码与任务分发 |
| Content | `content/INDEX.md` | 正文读取、关键词抽取、格式检查与终稿合并 |
| AIGC | `aigc/INDEX.md` | AIGC 检测、技术论文表达检测与降重替换辅助 |
| 图表 | `charts/INDEX.md` | 图片需求抽取、源码准备、渲染、回填与验证 |
| 参考文献 | `references/INDEX.md` | 文献搜索、验证、合并、文献池管理 |
| 文档导出 | `document_exporter/INDEX.md` | Word/PDF 导出、图片插入、导出前检查 |

## 根目录文件

| 文件 | 职责 |
|---|---|
| `INDEX.md` | 脚本模块总索引 |
| `requirements.txt` | 脚本依赖清单 |
| `install.ps1` | Windows 环境安装辅助脚本 |

## 推荐读取顺序

1. 先读本文件判断任务类型
2. 再读对应模块的 `INDEX.md`
3. 最后只读取需要执行或修改的具体脚本

## 路径约定

- 根目录不再保留 Python 脚本入口
- 执行脚本时使用模块路径，例如 `python scripts/core/lifecycle.py`
- 跨模块导入统一从 `scripts/` 作为包根开始，例如 `from core.logger import get_logger`
