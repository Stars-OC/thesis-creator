#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任务分发器 - 将耗时任务分发到 subAgent 执行

支持的子任务类型：
1. AIGC 检测
2. 同义词替换
3. 文献搜索
4. 图表生成

使用方法：
    # 作为模块使用
    from task_dispatcher import TaskDispatcher, TaskType, SubTask

    dispatcher = TaskDispatcher()
    task = SubTask(task_type=TaskType.AIGC_DETECT, input_data={'file_path': 'paper.md'})
    task_id = dispatcher.dispatch(task)
    result = dispatcher.get_result(task_id)

    # 作为 CLI 使用
    python scripts/task_dispatcher.py --type aigc_detect --input paper.md
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    AIGC_DETECT = "aigc_detect"
    SYNONYM_REPLACE = "synonym_replace"
    REFERENCE_SEARCH = "reference_search"
    CHART_GENERATE = "chart_generate"
    DOC_EXPORT = "doc_export"
    FORMAT_CHECK = "format_check"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubTask:
    """子任务数据结构"""
    task_type: TaskType
    input_data: Dict[str, Any]
    description: str = ""
    priority: int = 1  # 1=低, 2=中, 3=高
    timeout: int = 300  # 超时时间（秒）

    def to_dict(self) -> Dict:
        """to_dict"""
        return {
            "task_type": self.task_type.value,
            "input_data": self.input_data,
            "description": self.description,
            "priority": self.priority,
            "timeout": self.timeout
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SubTask':
        """from_dict"""
        return cls(
            task_type=TaskType(data["task_type"]),
            input_data=data["input_data"],
            description=data.get("description", ""),
            priority=data.get("priority", 1),
            timeout=data.get("timeout", 300)
        )


@dataclass
class TaskResult:
    """任务结果数据结构"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        """__post_init__"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """to_dict"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp
        }


class TaskDispatcher:
    """
    任务分发器

    负责将耗时任务分发到 Claude Code 的 subAgent 执行
    """

    def __init__(self, max_concurrent: int = 4, output_dir: str = "workspace/tasks"):
        """
        初始化分发器

        Args:
            max_concurrent: 最大并发任务数
            output_dir: 任务结果输出目录
        """
        self.max_concurrent = max_concurrent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pending_tasks: List[SubTask] = []
        self.running_tasks: Dict[str, SubTask] = {}
        self.completed_results: Dict[str, TaskResult] = {}

        # 加载历史任务结果
        self._load_history()

    def _load_history(self):
        """加载历史任务结果"""
        history_file = self.output_dir / "task_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    for task_id, result_data in history.items():
                        self.completed_results[task_id] = TaskResult(
                            task_id=result_data["task_id"],
                            task_type=TaskType(result_data["task_type"]),
                            status=TaskStatus(result_data["status"]),
                            output_data=result_data.get("output_data"),
                            error_message=result_data.get("error_message"),
                            execution_time=result_data.get("execution_time", 0),
                            timestamp=result_data.get("timestamp", "")
                        )
            except Exception as e:
                print(f"[警告] 加载任务历史失败: {e}")

    def _save_history(self):
        """保存任务历史"""
        history_file = self.output_dir / "task_history.json"
        try:
            history = {
                task_id: result.to_dict()
                for task_id, result in self.completed_results.items()
            }
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存任务历史失败: {e}")

    def dispatch(self, task: SubTask) -> str:
        """
        分发任务到 subAgent

        Args:
            task: 子任务

        Returns:
            task_id: 任务 ID，用于后续获取结果
        """
        # 生成任务 ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_id = f"{task.task_type.value}_{timestamp}_{len(self.pending_tasks)}"

        # 添加到待处理队列
        self.pending_tasks.append(task)

        print(f"[分发] 任务 {task_id} 已加入队列")
        print(f"  类型: {task.task_type.value}")
        print(f"  描述: {task.description or '无'}")

        return task_id

    def dispatch_batch(self, tasks: List[SubTask]) -> List[str]:
        """
        批量分发任务

        Args:
            tasks: 任务列表

        Returns:
            task_ids: 任务 ID 列表
        """
        task_ids = []
        for task in tasks:
            task_id = self.dispatch(task)
            task_ids.append(task_id)
        return task_ids

    def build_task_prompt(self, task: SubTask, task_id: str) -> str:
        """
        构建任务 Prompt

        Args:
            task: 子任务
            task_id: 任务 ID

        Returns:
            任务 Prompt
        """
        prompts = {
            TaskType.AIGC_DETECT: self._build_aigc_detect_prompt,
            TaskType.SYNONYM_REPLACE: self._build_synonym_replace_prompt,
            TaskType.REFERENCE_SEARCH: self._build_reference_search_prompt,
            TaskType.CHART_GENERATE: self._build_chart_generate_prompt,
            TaskType.DOC_EXPORT: self._build_doc_export_prompt,
            TaskType.FORMAT_CHECK: self._build_format_check_prompt,
        }

        builder = prompts.get(task.task_type)
        if builder:
            return builder(task, task_id)
        else:
            return f"未知任务类型: {task.task_type.value}"

    def _build_aigc_detect_prompt(self, task: SubTask, task_id: str) -> str:
        """构建 AIGC 检测任务 Prompt"""
        file_path = task.input_data.get('file_path', '')
        mode = task.input_data.get('mode', 'lite')

        return f'''请执行 AIGC 检测任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: AIGC 检测
- **输入文件**: {file_path}
- **检测模式**: {mode}

## 执行命令
```bash
python scripts/aigc_detect.py --input "{file_path}" --mode {mode} --format json
```

## 输出要求
1. 执行上述命令
2. 读取并解析输出结果
3. 返回检测结果 JSON

## 预期输出格式
```json
{{
  "overall_score": 28.0,
  "high_risk_paragraphs": [2, 5, 8],
  "suggestion": "建议重点改写第 2、5、8 段"
}}
```
'''

    def _build_synonym_replace_prompt(self, task: SubTask, task_id: str) -> str:
        """构建同义词替换任务 Prompt"""
        file_path = task.input_data.get('file_path', '')
        ratio = task.input_data.get('ratio', 0.5)
        output_path = task.input_data.get('output_path', '')

        if not output_path:
            output_path = str(Path(file_path).with_suffix('.replaced.md'))

        return f'''请执行同义词替换任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: 同义词替换
- **输入文件**: {file_path}
- **替换比例**: {ratio}
- **输出文件**: {output_path}

## 执行命令
```bash
python scripts/enhanced_replace.py --input "{file_path}" --output "{output_path}" --ratio {ratio}
```

## 输出要求
1. 执行上述命令
2. 验证输出文件已生成
3. 返回替换统计信息

## 预期输出格式
```json
{{
  "output_file": "{output_path}",
  "total_replacements": 150,
  "unique_words": 45
}}
```
'''

    def _build_reference_search_prompt(self, task: SubTask, task_id: str) -> str:
        """构建文献搜索任务 Prompt"""
        query = task.input_data.get('query', '')
        year_range = task.input_data.get('year_range', '2020-2025')
        limit = task.input_data.get('limit', 10)

        return f'''请执行文献搜索任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: 文献搜索
- **关键词**: {query}
- **年份范围**: {year_range}
- **结果数量**: {limit}

## 执行命令
```bash
python scripts/reference_searcher.py --query "{query}" --year-range {year_range} --limit {limit} --format gbt7714
```

## 输出要求
1. 执行上述命令
2. 解析搜索结果
3. 返回格式化的参考文献列表

## 预期输出格式
```json
{{
  "query": "{query}",
  "total_results": 10,
  "references": [
    "[1] 张三, 李四. 大数据技术研究[J]. 管理科学学报, 2023, 26(3): 45-52.",
    "..."
  ]
}}
```
'''

    def _build_chart_generate_prompt(self, task: SubTask, task_id: str) -> str:
        """构建图表生成任务 Prompt"""
        file_path = task.input_data.get('file_path', '')
        output_dir = task.input_data.get('output_dir', 'charts')

        return f'''请执行图表生成任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: 图表生成
- **输入文件**: {file_path}
- **输出目录**: {output_dir}

## 执行命令
```bash
python scripts/chart_generator.py "{file_path}" --output {output_dir} --format md
```

## 输出要求
1. 执行上述命令
2. 解析生成的图表
3. 返回图表列表

## 预期输出格式
```json
{{
  "total_charts": 5,
  "output_file": "{output_dir}/charts_xxx.md",
  "charts": [
    {{"id": "图4-1", "type": "架构图", "name": "系统架构图"}},
    "..."
  ]
}}
```
'''

    def _build_doc_export_prompt(self, task: SubTask, task_id: str) -> str:
        """构建文档导出任务 Prompt"""
        file_path = task.input_data.get('file_path', '')
        output_path = task.input_data.get('output_path', '')
        format_type = task.input_data.get('format', 'docx')

        return f'''请执行文档导出任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: 文档导出
- **输入文件**: {file_path}
- **输出文件**: {output_path}
- **格式**: {format_type}

## 执行命令
```bash
python scripts/enhanced_md_to_docx.py --input "{file_path}" --output "{output_path}"
```

## 输出要求
1. 执行上述命令
2. 验证输出文件已生成
3. 返回导出结果
'''

    def _build_format_check_prompt(self, task: SubTask, task_id: str) -> str:
        """构建格式检查任务 Prompt"""
        file_path = task.input_data.get('file_path', '')

        return f'''请执行格式检查任务。

## 任务 ID
{task_id}

## 任务信息
- **类型**: 格式检查
- **输入文件**: {file_path}

## 执行命令
```bash
python scripts/format_checker.py --input "{file_path}"
```

## 输出要求
1. 执行上述命令
2. 解析检查结果
3. 返回问题列表
'''

    def get_result(self, task_id: str, timeout: int = 300) -> Optional[TaskResult]:
        """
        获取任务结果

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            任务结果，如果任务未完成则返回 None
        """
        # 检查已完成任务
        if task_id in self.completed_results:
            return self.completed_results[task_id]

        # 检查任务文件
        result_file = self.output_dir / f"{task_id}_result.json"
        if result_file.exists():
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = TaskResult(
                        task_id=data["task_id"],
                        task_type=TaskType(data["task_type"]),
                        status=TaskStatus(data["status"]),
                        output_data=data.get("output_data"),
                        error_message=data.get("error_message"),
                        execution_time=data.get("execution_time", 0),
                        timestamp=data.get("timestamp", "")
                    )
                    self.completed_results[task_id] = result
                    return result
            except Exception as e:
                print(f"[错误] 读取任务结果失败: {e}")

        return None

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict]:
        """
        列出任务

        Args:
            status: 筛选状态

        Returns:
            任务列表
        """
        tasks = []

        # 待处理任务
        for task in self.pending_tasks:
            tasks.append({
                "status": TaskStatus.PENDING.value,
                "task_type": task.task_type.value,
                "description": task.description
            })

        # 已完成任务
        for task_id, result in self.completed_results.items():
            if status is None or result.status == status:
                tasks.append({
                    "task_id": task_id,
                    "status": result.status.value,
                    "task_type": result.task_type.value,
                    "timestamp": result.timestamp
                })

        return tasks

    def clear_history(self, keep_recent: int = 100):
        """
        清理历史记录

        Args:
            keep_recent: 保留最近的记录数
        """
        if len(self.completed_results) > keep_recent:
            # 按时间排序
            sorted_results = sorted(
                self.completed_results.items(),
                key=lambda x: x[1].timestamp,
                reverse=True
            )

            # 保留最近的记录
            self.completed_results = dict(sorted_results[:keep_recent])

            # 重新保存
            self._save_history()

            print(f"[清理] 已清理历史记录，保留最近 {keep_recent} 条")


def generate_skill_instructions() -> str:
    """
    生成 Skill 使用说明

    Returns:
        Skill 集成说明
    """
    return '''## 任务分发集成说明

### 在 Skill 中使用 Task 工具

```markdown
## Step 5: 降重处理（并行执行）

使用 Task 工具并行处理各章节降重：

1. 创建子任务列表
2. 调用 Task 工具分发任务
3. 等待所有任务完成
4. 汇总结果

### 示例 Prompt

```
请执行以下并行任务：

**任务 1**: AIGC 检测
- 文件: workspace/drafts/chapter_01.md
- 模式: lite

**任务 2**: 同义词替换
- 文件: workspace/drafts/chapter_02.md
- 比例: 0.5

**任务 3**: 文献搜索
- 关键词: 精准营销 大数据
- 年份: 2020-2025
```

### CLI 命令

```powershell
# 分发单个任务
python scripts/task_dispatcher.py --type aigc_detect --input paper.md

# 批量分发
python scripts/task_dispatcher.py --batch tasks.json

# 查看任务状态
python scripts/task_dispatcher.py --list

# 获取结果
python scripts/task_dispatcher.py --result task_id_here
```
'''


def main():
    """main"""
    parser = argparse.ArgumentParser(description="任务分发器")
    parser.add_argument("--type", "-t", choices=[e.value for e in TaskType],
                        help="任务类型")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--query", "-q", help="搜索关键词（文献搜索用）")
    parser.add_argument("--ratio", "-r", type=float, default=0.5, help="替换比例")
    parser.add_argument("--limit", "-l", type=int, default=10, help="结果数量")
    parser.add_argument("--batch", "-b", help="批量任务文件（JSON）")
    parser.add_argument("--list", action="store_true", help="列出任务")
    parser.add_argument("--result", help="获取任务结果")
    parser.add_argument("--generate-prompt", action="store_true", help="生成任务 Prompt")

    args = parser.parse_args()

    dispatcher = TaskDispatcher()

    # 列出任务
    if args.list:
        tasks = dispatcher.list_tasks()
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return

    # 获取结果
    if args.result:
        result = dispatcher.get_result(args.result)
        if result:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"任务 {args.result} 未找到或未完成")
        return

    # 批量任务
    if args.batch:
        with open(args.batch, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)

        tasks = [SubTask.from_dict(t) for t in batch_data.get("tasks", [])]
        task_ids = dispatcher.dispatch_batch(tasks)

        print(f"已分发 {len(task_ids)} 个任务:")
        for i, task_id in enumerate(task_ids):
            print(f"  {i+1}. {task_id}")
        return

    # 单个任务
    if args.type:
        task_type = TaskType(args.type)
        input_data = {}

        if args.input:
            input_data["file_path"] = args.input
        if args.output:
            input_data["output_path"] = args.output
        if args.query:
            input_data["query"] = args.query
        if args.ratio:
            input_data["ratio"] = args.ratio
        if args.limit:
            input_data["limit"] = args.limit

        task = SubTask(
            task_type=task_type,
            input_data=input_data,
            description=f"{task_type.value} 任务"
        )

        task_id = dispatcher.dispatch(task)

        # 生成 Prompt
        if args.generate_prompt:
            prompt = dispatcher.build_task_prompt(task, task_id)
            print("\n" + "=" * 50)
            print("任务 Prompt:")
            print("=" * 50)
            print(prompt)
        else:
            print(f"\n任务已分发: {task_id}")
            print("使用 --generate-prompt 查看任务详情")


if __name__ == "__main__":
    main()
