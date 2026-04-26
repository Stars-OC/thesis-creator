#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文创作生命周期管理器（Thesis Lifecycle Manager）

统一管理日志与状态：
- 步骤开始/完成/失败
- 章节完成上报
- 状态查看与断点续写
"""

import argparse
from pathlib import Path
from typing import Dict, Any

from status_manager import ThesisStatusManager, STEPS
from logger import init_logger, get_logger


def _load_lifecycle_config(workspace: Path) -> Dict[str, Any]:
    """加载 lifecycle 配置（可选）。"""
    default = {
        "logging": {"enabled": True},
        "status": {"enabled": True, "auto_init": True},
    }

    config_path = workspace / ".thesis-config.yaml"
    if not config_path.exists():
        return default

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        lifecycle_cfg = data.get("lifecycle", {}) if isinstance(data, dict) else {}
        if isinstance(lifecycle_cfg, dict):
            for section in ("logging", "status"):
                if isinstance(lifecycle_cfg.get(section), dict):
                    default[section].update(lifecycle_cfg[section])
    except Exception:
        pass

    return default


class LifecycleEvent:
    START = "start"
    COMPLETE = "complete"
    ERROR = "error"
    CHAPTER_DONE = "chapter-done"


class ThesisLifecycle:
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self.config = _load_lifecycle_config(self.workspace)

        if self.config["logging"]["enabled"]:
            self.logger = init_logger(session_name="lifecycle", workspace_path=str(self.workspace))
        else:
            self.logger = get_logger(check_config=False)

        self.status_mgr = ThesisStatusManager(str(self.workspace))
        if self.config["status"].get("auto_init", True):
            self.status_mgr.ensure()

    def step_start(self, step: int):
        if self.config["status"]["enabled"]:
            ok, missing = self.status_mgr.check_prerequisites(step)
            if not ok:
                msg = f"步骤{step} 前置条件未满足: {'; '.join(missing)}"
                self.logger.error(msg)
                print(f"[错误] {msg}")
                return
            self.status_mgr.update_step(step, "start")

        self.logger.step(f"Step {step}({STEPS.get(step, {}).get('name', 'Unknown')})", "start")

    def step_complete(self, step: int):
        if self.config["status"]["enabled"]:
            self.status_mgr.update_step(step, "complete")
        self.logger.step(f"Step {step}({STEPS.get(step, {}).get('name', 'Unknown')})", "complete")

    def step_error(self, step: int, message: str):
        self.logger.step(f"Step {step}({STEPS.get(step, {}).get('name', 'Unknown')})", "error")
        self.logger.error(message)

    def chapter_done(self, chapter: str, words: int):
        if self.config["status"]["enabled"]:
            self.status_mgr.mark_chapter_done(chapter, words)
        self.logger.chapter_progress(chapter, words, words)

    def print_status(self):
        self.status_mgr.print_status()

    def resume(self):
        step = self.status_mgr.get_resume_point()
        print(f"[断点续写] 应从步骤 {step}({STEPS[step]['name']}) 继续")


def main():
    parser = argparse.ArgumentParser(description="论文生命周期管理器")
    parser.add_argument("--workspace", required=True, help="thesis-workspace 路径")
    parser.add_argument("--step", type=int, help="步骤编号")
    parser.add_argument("--event", choices=[LifecycleEvent.START, LifecycleEvent.COMPLETE, LifecycleEvent.ERROR, LifecycleEvent.CHAPTER_DONE], help="生命周期事件")
    parser.add_argument("--chapter", help="章节标识，如 chapter_3")
    parser.add_argument("--words", type=int, default=0, help="章节字数")
    parser.add_argument("--message", default="", help="错误信息")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--resume", action="store_true", help="查看断点续写位置")

    args = parser.parse_args()

    lifecycle = ThesisLifecycle(args.workspace)

    if args.status:
        lifecycle.print_status()
        return

    if args.resume:
        lifecycle.resume()
        return

    if args.event == LifecycleEvent.CHAPTER_DONE:
        if not args.chapter:
            print("[错误] chapter-done 事件必须提供 --chapter")
            return
        lifecycle.chapter_done(args.chapter, args.words)
        return

    if args.event == LifecycleEvent.ERROR:
        if args.step is None:
            print("[错误] error 事件必须提供 --step")
            return
        lifecycle.step_error(args.step, args.message or "未提供错误信息")
        return

    if args.step is None or not args.event:
        parser.print_help()
        return

    if args.event == LifecycleEvent.START:
        lifecycle.step_start(args.step)
    elif args.event == LifecycleEvent.COMPLETE:
        lifecycle.step_complete(args.step)


if __name__ == "__main__":
    main()
