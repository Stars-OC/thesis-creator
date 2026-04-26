#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文状态管理器（Thesis Status Manager）

管理论文写作流程的状态文件（.thesis-status.json），
支持步骤级跟踪、前置条件检查和断点续写。

使用方法：
    python scripts/status_manager.py --init thesis-workspace/
    python scripts/status_manager.py --check-step 4 thesis-workspace/
    python scripts/status_manager.py --update-step 4 --action start thesis-workspace/
    python scripts/status_manager.py --mark-done chapter_3 --words 3000 thesis-workspace/
    python scripts/status_manager.py --resume thesis-workspace/
"""

import json
import argparse
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from typing import Tuple, List


# 步骤定义
STEPS = {
    0: {"name": "初始化", "prerequisites": []},
    1: {"name": "主题确认", "prerequisites": [0]},
    2: {"name": "文献搜索", "prerequisites": [1]},
    3: {"name": "大纲生成", "prerequisites": [1]},
    4: {"name": "分章节撰写", "prerequisites": [2, 3]},
    5: {"name": "AIGC降重", "prerequisites": [4]},
    6: {"name": "审校润色", "prerequisites": [5]},
    7: {"name": "合并检测", "prerequisites": [4]},
    8: {"name": "图片生成", "prerequisites": [4]},
    9: {"name": "文档导出", "prerequisites": [5, 7, 8]},
}

DEFAULT_STATUS = {
    "version": "2.0",
    "created_at": "",
    "updated_at": "",
    "current_step": 0,
    "steps": {},
    "chapter_status": {},
    "references_status": {
        "pool_created": False,
        "pool_path": "",
        "total_refs": 0,
        "zh_ratio": 0.0
    }
}


class ThesisStatusManager:
    """论文状态管理器"""

    def __init__(self, workspace_dir: str):
        self.workspace_dir = self._resolve_workspace_dir(workspace_dir)
        self.status_file = self.workspace_dir / ".thesis-status.json"

    def _resolve_workspace_dir(self, workspace_dir: str) -> Path:
        """解析并兼容工作区路径格式"""
        p = Path(workspace_dir)

        if p.name == "workspace":
            p = p.parent

        if p.is_file():
            p = p.parent

        candidate = p / ".thesis-status.json"
        if candidate.exists():
            return p

        child_workspace = p / "workspace"
        if child_workspace.exists():
            return p

        if p.name == "thesis-workspace":
            return p

        return p

    def _normalize_status_schema(self, status: dict) -> dict:
        """兼容旧版字段并补齐默认字段"""
        if status is None:
            return status

        if "chapter_status" not in status:
            status["chapter_status"] = status.pop("chapters", {}) if "chapters" in status else {}
        if "references_status" not in status:
            status["references_status"] = status.pop("references", {}) if "references" in status else {}

        if "steps" not in status or not isinstance(status["steps"], dict):
            status["steps"] = {}
        if "chapter_status" not in status or not isinstance(status["chapter_status"], dict):
            status["chapter_status"] = {}
        if "references_status" not in status or not isinstance(status["references_status"], dict):
            status["references_status"] = {
                "pool_created": False,
                "pool_path": "",
                "total_refs": 0,
                "zh_ratio": 0.0
            }

        return status

    def load(self) -> dict:
        """加载状态文件（不存在时自动初始化）"""
        if not self.status_file.exists():
            print(f"[信息] 状态文件不存在，自动初始化: {self.status_file}")
            return self.init()
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                return self._normalize_status_schema(loaded)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[错误] 状态文件读取失败: {e}")
            return None

    def ensure(self) -> dict:
        """确保状态文件存在，不存在则初始化"""
        if self.status_file.exists():
            return self.load()
        return self.init()

    def save(self, status: dict):
        """保存状态文件"""
        status = self._normalize_status_schema(status)
        status["updated_at"] = datetime.now().isoformat()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)

    def init(self) -> dict:
        """初始化状态文件（v2.0）"""
        status = deepcopy(DEFAULT_STATUS)
        status["created_at"] = datetime.now().isoformat()
        status["updated_at"] = status["created_at"]

        for step_num, step_info in STEPS.items():
            status["steps"][str(step_num)] = {
                "name": step_info["name"],
                "status": "pending",
                "started_at": None,
                "completed_at": None
            }

        self.save(status)
        print(f"[成功] 状态文件已初始化: {self.status_file}")
        return status

    def update_step(self, step: int, action: str) -> dict:
        """
        更新步骤状态

        Args:
            step: 步骤编号
            action: 'start' 或 'complete'（兼容 'completed'）
        """
        status = self.load()
        if status is None:
            print("[错误] 状态文件不存在，请先运行 --init")
            return None

        if action == "completed":
            action = "complete"
        elif action == "in_progress":
            action = "start"

        step_key = str(step)
        if step_key not in status["steps"]:
            print(f"[错误] 无效步骤编号: {step}")
            return status

        if action == "start":
            status["steps"][step_key]["status"] = "in_progress"
            status["steps"][step_key]["started_at"] = datetime.now().isoformat()
            status["current_step"] = step
        elif action == "complete":
            status["steps"][step_key]["status"] = "completed"
            status["steps"][step_key]["completed_at"] = datetime.now().isoformat()

        self.save(status)
        print(f"[成功] 步骤 {step}({STEPS[step]['name']}) 状态更新: {action}")
        return status

    def mark_chapter_done(self, chapter: str, word_count: int) -> dict:
        """标记章节完成"""
        status = self.load()
        if status is None:
            print("[错误] 状态文件不存在，请先运行 --init")
            return None

        status["chapter_status"][chapter] = {
            "status": "completed",
            "word_count": word_count,
            "completed_at": datetime.now().isoformat()
        }

        self.save(status)
        print(f"[成功] 章节 {chapter} 已标记完成（{word_count} 字）")
        return status

    def check_prerequisites(self, step: int) -> Tuple[bool, List[str]]:
        """
        检查步骤前置条件

        Returns:
            (是否满足, 未满足的前置步骤列表)
        """
        status = self.load()
        if status is None:
            return False, ["状态文件不存在"]

        if step not in STEPS:
            return False, [f"无效步骤编号: {step}"]

        missing = []
        for prereq in STEPS[step]["prerequisites"]:
            prereq_key = str(prereq)
            if prereq_key not in status["steps"]:
                missing.append(f"步骤{prereq}({STEPS[prereq]['name']})未初始化")
            elif status["steps"][prereq_key]["status"] != "completed":
                missing.append(f"步骤{prereq}({STEPS[prereq]['name']})未完成")

        return len(missing) == 0, missing

    def get_resume_point(self) -> int:
        """获取断点续写位置"""
        status = self.load()
        if status is None:
            return 0

        current_step = status.get("current_step", 0)
        if current_step and str(current_step) in status.get("steps", {}):
            step_state = status["steps"][str(current_step)].get("status")
            if step_state in ("in_progress", "pending"):
                return current_step

        for step_num in sorted(STEPS.keys()):
            step_key = str(step_num)
            if step_key not in status["steps"]:
                return step_num
            if status["steps"][step_key]["status"] != "completed":
                return step_num

        return max(STEPS.keys())

    def print_status(self):
        """打印当前状态"""
        status = self.load()
        if status is None:
            print("[错误] 状态文件不存在")
            return

        print(f"\n{'='*50}")
        print(f"论文写作状态（v{status.get('version', '1.0')}）")
        print(f"{'='*50}")
        print(f"创建时间: {status.get('created_at', 'N/A')}")
        print(f"更新时间: {status.get('updated_at', 'N/A')}")
        print(f"当前步骤: {status.get('current_step', 0)}")
        print(f"{'-'*50}")

        for step_num in sorted(STEPS.keys()):
            step_key = str(step_num)
            step_info = STEPS[step_num]
            step_status = status["steps"].get(step_key, {})
            status_str = step_status.get("status", "unknown")
            icon = {"completed": "[OK]", "in_progress": "[ING]", "pending": "[PEND]"}.get(status_str, "[?]")
            print(f"  {icon} 步骤{step_num}: {step_info['name']} [{status_str}]")

        if status.get("chapter_status"):
            print(f"{'-'*50}")
            print("章节进度:")
            for chapter, info in status["chapter_status"].items():
                words = info.get("word_count", 0)
                print(f"  [OK] {chapter}: {words} 字")

        ref_info = status.get("references_status", {})
        if ref_info.get("pool_created"):
            print(f"{'-'*50}")
            print(f"文献池: {ref_info.get('total_refs', 0)} 篇 (中文占比: {ref_info.get('zh_ratio', 0):.0%})")

        print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="论文状态管理器")
    parser.add_argument("workspace", help="工作区目录路径")
    parser.add_argument("--init", action="store_true", help="初始化状态文件")
    parser.add_argument("--check-step", type=int, help="检查指定步骤的前置条件")
    parser.add_argument("--update-step", type=int, help="更新指定步骤状态")
    parser.add_argument("--action", choices=["start", "complete", "completed", "in_progress"], help="步骤动作")
    parser.add_argument("--mark-done", help="标记章节完成（如 chapter_3）")
    parser.add_argument("--words", type=int, default=0, help="章节字数")
    parser.add_argument("--resume", action="store_true", help="获取断点续写位置")
    parser.add_argument("--status", action="store_true", help="显示当前状态")
    parser.add_argument("--ensure", action="store_true", help="确保状态文件存在（不存在则初始化）")

    args = parser.parse_args()
    manager = ThesisStatusManager(args.workspace)

    if args.init:
        manager.init()
    elif args.ensure:
        manager.ensure()
    elif args.check_step is not None:
        ok, missing = manager.check_prerequisites(args.check_step)
        if ok:
            print(f"[通过] 步骤{args.check_step}的前置条件已满足")
        else:
            print(f"[未满足] 步骤{args.check_step}前置条件不足:")
            for m in missing:
                print(f"  - {m}")
    elif args.update_step is not None and args.action:
        manager.update_step(args.update_step, args.action)
    elif args.mark_done:
        manager.mark_chapter_done(args.mark_done, args.words)
    elif args.resume:
        step = manager.get_resume_point()
        print(f"[断点续写] 应从步骤 {step}({STEPS[step]['name']}) 继续")
    elif args.status:
        manager.print_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
