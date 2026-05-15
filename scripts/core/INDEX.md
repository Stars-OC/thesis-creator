# core 核心脚本索引

本目录负责 thesis-creator Skill 的生命周期、状态、日志、终端编码与任务分发等基础能力。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `lifecycle.py` | 工作区生命周期检查与统一流程入口，整合状态管理和日志记录 |
| `status_manager.py` | 管理 `thesis-workspace/.thesis-status.json`，记录步骤状态和质量门禁 |
| `logger.py` | 写入流程日志，统一日志目录、格式和替换记录 |
| `terminal_encoding.py` | 提供跨平台子进程文本编码参数，避免 Windows 终端乱码 |
| `task_dispatcher.py` | 根据任务类型分发到论文写作、检测、图片、导出等流程 |

## 推荐命令

```bash
python scripts/core/lifecycle.py --workspace thesis-workspace/ --check-workspace
python scripts/core/status_manager.py --workspace thesis-workspace/ --show
```
