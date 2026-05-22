#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import sys

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

"""
论文创作生命周期管理器（Thesis Lifecycle Manager）

统一管理日志与状态：
- 步骤开始/完成/失败
- 章节完成上报
- 状态查看与断点续写
"""

import argparse
import shutil
import venv
from pathlib import Path
from typing import Dict, Any

from core.status_manager import ThesisStatusManager, STEPS
from core.logger import init_logger, get_logger
from core.config_resolver import write_runtime_config


def _load_lifecycle_config(workspace: Path) -> Dict[str, Any]:
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


def _should_copy_runtime_item(path: Path) -> bool:
    excluded_names = {"__pycache__", ".venv", ".pytest_cache"}
    if any(part in excluded_names for part in path.parts):
        return False
    if path.name.startswith("test_") or path.suffix.lower() in {".pyc", ".pyo"}:
        return False
    return path.is_dir() or path.suffix.lower() in {".py", ".txt", ".yaml", ".yml", ".md"}


def _copy_runtime_scripts(source_dir: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        if not _should_copy_runtime_item(item):
            continue
        target = target_dir / item.name
        if item.is_dir():
            _copy_runtime_scripts(item, target)
            continue
        if not target.exists():
            shutil.copyfile(item, target)


def _copy_tree_if_missing(source_dir: Path, target_dir: Path):
    if not source_dir.exists():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        target = target_dir / item.name
        if item.is_dir():
            _copy_tree_if_missing(item, target)
            continue
        if not target.exists():
            shutil.copyfile(item, target)


def _ensure_workspace_references(workspace: Path):
    template_candidates = [
        workspace.parent / ".claude" / "skills" / "thesis-creator" / "references",
        Path(__file__).resolve().parents[2] / "references",
    ]
    for template_root in template_candidates:
        if template_root.exists():
            _copy_tree_if_missing(template_root, workspace / "references")
            return



def _ensure_workspace_config(workspace: Path):
    target_config = workspace / ".thesis-config.yaml"
    if target_config.exists():
        return

    template_candidates = [
        workspace.parent / ".claude" / "skills" / "thesis-creator" / "config" / ".thesis-config.yaml",
        Path(__file__).resolve().parents[2] / "config" / ".thesis-config.yaml",
    ]
    for template in template_candidates:
        if template.exists():
            shutil.copyfile(template, target_config)
            return



def _ensure_image_manifest(workspace: Path):
    manifest_path = workspace / "workspace" / "references" / "images.yaml"
    if manifest_path.exists():
        return

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "images: []\n",
        encoding="utf-8",
    )



def _ensure_workspace_output_dirs(workspace: Path):
    for relative_path in (
        "workspace/drafts",
        "workspace/final",
        "workspace/final/images",
        "workspace/final/images/sources",
        "workspace/reports",
        "workspace/references",
    ):
        (workspace / relative_path).mkdir(parents=True, exist_ok=True)



def ensure_workspace_structure(workspace_path: str, sync_scripts: bool = True) -> Path:
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)

    scripts_dir = workspace / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "logs").mkdir(parents=True, exist_ok=True)

    venv_dir = scripts_dir / ".venv"
    if not venv_dir.exists():
        venv.create(venv_dir, with_pip=True)

    if sync_scripts:
        _copy_runtime_scripts(Path(__file__).resolve().parents[1], scripts_dir)

    _ensure_workspace_output_dirs(workspace)
    _ensure_workspace_references(workspace)

    target_background = workspace / "references" / "prompt" / "background.md"
    if not target_background.exists():
        template_candidates = [
            workspace / "references" / "prompt" / "background_template.md",
            workspace.parent / ".claude" / "skills" / "thesis-creator" / "references" / "prompt" / "background_template.md",
            Path(__file__).resolve().parents[2] / "references" / "prompt" / "background_template.md",
        ]
        target_background.parent.mkdir(parents=True, exist_ok=True)
        for template in template_candidates:
            if template.exists():
                shutil.copyfile(template, target_background)
                break

    _ensure_workspace_config(workspace)
    write_runtime_config(Path(__file__).resolve().parents[2], workspace)
    _ensure_image_manifest(workspace)
    ThesisStatusManager(str(workspace)).ensure()

    return workspace



def check_workspace_preflight(workspace: Path) -> Dict[str, Any]:
    required_paths = [
        "scripts",
        "scripts/core/lifecycle.py",
        "scripts/charts/render.py",
        "scripts/charts/source_writer.py",
        "scripts/charts/engines/plantuml.py",
        "scripts/charts/engines/graphviz.py",
        "scripts/references/reference_engine.py",
        "scripts/aigc/detect.py",
        "logs",
        ".thesis-status.json",
        ".thesis-config.yaml",
        ".thesis-runtime-config.yaml",
        "references/prompt/background.md",
        "workspace/drafts",
        "workspace/final",
        "workspace/final/images",
        "workspace/final/images/sources",
        "workspace/reports",
        "workspace/references/images.yaml",
    ]
    missing = [relative_path for relative_path in required_paths if not (workspace / relative_path).exists()]
    incomplete = []

    suggestions = []
    if missing:
        suggestions.append("python scripts/core/lifecycle.py --workspace thesis-workspace/ --prepare-runtime")

    return {
        "ok": not missing,
        "missing": missing,
        "incomplete": incomplete,
        "suggestions": suggestions,
    }



def init_and_check_workspace(workspace_path: str, sync_scripts: bool = True) -> Dict[str, Any]:
    workspace = ensure_workspace_structure(workspace_path, sync_scripts=sync_scripts)
    return check_workspace_preflight(workspace)


class LifecycleEvent:
    START = "start"
    COMPLETE = "complete"
    ERROR = "error"
    CHAPTER_DONE = "chapter-done"


class ThesisLifecycle:
    def __init__(self, workspace_path: str):
        self.workspace = ensure_workspace_structure(workspace_path, sync_scripts=True)
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
            # 启动前先做产物-状态一致性对账，防止基于错误状态做决策
            self.status_mgr.reconcile_with_artifacts(silent=True)
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
            # complete 时校验产物，缺失则阻断（update_step 内已内置校验，此处再打一道日志）
            ok, missing = self.status_mgr.verify_step_artifacts(step)
            if not ok:
                msg = f"步骤{step} 缺少产物不能 complete: {missing}"
                self.logger.error(msg)
                print(f"[阻断] {msg}")
                return
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
    parser.add_argument("--prepare-runtime", action="store_true", help="仅准备工作区脚本目录与虚拟环境")
    parser.add_argument("--check-workspace", action="store_true", help="检查工作区初始化产物是否完整")
    parser.add_argument("--init-and-check", action="store_true", help="一键初始化工作区并执行预检")
    parser.add_argument("--reconcile", action="store_true", help="对账产物：completed 但缺产物的步骤自动降级回 in_progress")

    args = parser.parse_args()

    if args.init_and_check:
        report = init_and_check_workspace(args.workspace, sync_scripts=True)
        if report["ok"]:
            print(f"[成功] 工作区初始化与检查通过: {args.workspace}")
            return
        print(f"[错误] 工作区已初始化，但检查未通过: {args.workspace}")
        if report["missing"]:
            print("[缺失] " + ", ".join(report["missing"]))
        if report["incomplete"]:
            print("[未完成] " + ", ".join(report["incomplete"]))
        for suggestion in report["suggestions"]:
            print(f"[建议] {suggestion}")
        return

    if args.check_workspace:
        report = check_workspace_preflight(Path(args.workspace))
        if report["ok"]:
            print(f"[成功] 工作区检查通过: {args.workspace}")
            return
        print(f"[错误] 工作区检查未通过: {args.workspace}")
        if report["missing"]:
            print("[缺失] " + ", ".join(report["missing"]))
        if report["incomplete"]:
            print("[未完成] " + ", ".join(report["incomplete"]))
        for suggestion in report["suggestions"]:
            print(f"[建议] {suggestion}")
        return

    if args.prepare_runtime:
        prepared = ensure_workspace_structure(args.workspace, sync_scripts=True)
        print(f"[成功] 工作区运行环境已就绪: {prepared}")
        return

    lifecycle = ThesisLifecycle(args.workspace)

    if args.reconcile:
        downgraded = lifecycle.status_mgr.reconcile_with_artifacts(silent=False)
        if not downgraded:
            print("[通过] 所有步骤的产物与状态一致")
        else:
            print(f"[降级] 共 {len(downgraded)} 个步骤被降级")
        return

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
