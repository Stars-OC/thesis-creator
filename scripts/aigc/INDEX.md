# AIGC 脚本索引

本目录负责论文 AIGC 检测与技术论文表达检测，供 Step 6/Step 7 质量门禁调用。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `detect.py` | 通用 AIGC 检测，支持文本、文件和目录检测 |
| `technical_detect.py` | 面向技术论文的 AIGC 检测，结合技术术语白名单降低误判 |

## 资源文件

| 文件 | 用途 |
|---|---|
| `term_whitelist.txt` | 技术术语保护白名单 |

## 推荐命令

```bash
python scripts/aigc/detect.py --input workspace/final/论文终稿.md --format json
python scripts/aigc/technical_detect.py --input workspace/final/论文终稿.md --format json
```

## 推荐顺序

1. `detect.py`
2. `technical_detect.py`
3. 根据检测结果进入 Step 6 改写与自检
