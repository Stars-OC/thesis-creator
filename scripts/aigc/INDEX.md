# AIGC 脚本索引

本目录负责论文 AIGC 检测与技术论文表达检测，供 Step 6/Step 7 质量门禁调用。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `detect.py` | 通用 AIGC 检测，支持文本、文件和目录检测 |
| `technical_detect.py` | 面向技术论文的 AIGC 检测，结合技术术语白名单降低误判 |
| `reduce_workflow.py` | 章节级降重流程编排，生成改写策略、唯一输出与自检结果 |
| `simple_replace.py` | 轻量同义替换辅助 |
| `synonym_replace.py` | 基于词典的同义词替换辅助 |
| `enhanced_replace.py` | 增强替换辅助，结合术语保护和替换比例控制 |
| `text_analysis.py` | 文本统计分析辅助，用于降重和 AIGC 风险判断 |
| `aigc_detect.py` | 历史包装入口，导出 `detect.py` 的核心 API |
| `aigc_detect_technical.py` | 历史包装入口，导出 `technical_detect.py` 的核心 API |

## 资源文件

| 文件 | 用途 |
|---|---|
| `term_whitelist.txt` | 技术术语保护白名单 |
| `enhanced_synonyms.txt` | 增强同义替换词典 |

## 推荐命令

```bash
python scripts/aigc/detect.py --input workspace/final/论文终稿.md --format json
python scripts/aigc/technical_detect.py --input workspace/final/论文终稿.md --format json
```

## 推荐顺序

1. `detect.py`
2. `technical_detect.py`
3. 根据检测结果进入 Step 6 改写与自检
