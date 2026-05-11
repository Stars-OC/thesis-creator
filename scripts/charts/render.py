# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

if __package__ in {None, ""}:
    scripts_dir = Path(__file__).resolve().parents[1]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

try:
    from .engines import graphviz, mermaid, plantuml
    from .schemas import dump_manifest, load_manifest
except ImportError:
    from engines import graphviz, mermaid, plantuml
    from schemas import dump_manifest, load_manifest


def _resolve_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return root / path


def _load_plantuml_method(root: Path) -> str:
    config = root / ".thesis-config.yaml"
    if not config.exists():
        return "auto"
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return "auto"
    plantuml_render = data.get("plantuml_render") or {}
    if not isinstance(plantuml_render, dict):
        return "auto"
    method = str(plantuml_render.get("method") or "auto").strip().lower()
    if method in {"auto", "plantuml", "kroki", "official_server"}:
        return method
    return "auto"


def _effective_method(item, root: Path, method: str) -> str:
    if item.engine == "plantuml" and method == "auto":
        return _load_plantuml_method(root)
    return method


def _render_item(item, root: Path, method: str) -> bool:
    source = _resolve_path(item.source_file, root)
    output = _resolve_path(item.output_file, root)
    effective_method = _effective_method(item, root, method)
    if item.engine == "mermaid":
        mermaid.render(source, output, method=effective_method)
        return True
    if item.engine == "graphviz":
        graphviz.render(source, output)
        return True
    if item.engine == "plantuml":
        plantuml.render(source, output, method=effective_method)
        return True
    return False


def render_manifest(manifest_path: Path, root: Path | None = None, method: str = "auto", report_path: Path | None = None) -> Dict[str, Any]:
    root = root or Path.cwd()
    items = load_manifest(manifest_path)
    rendered = 0
    failed = 0
    skipped = 0

    for item in items:
        if item.engine == "user":
            skipped += 1
            continue
        try:
            if _render_item(item, root, method):
                item.render_status = "rendered"
                item.render_error = ""
                rendered += 1
            else:
                skipped += 1
        except Exception as exc:
            item.render_status = "failed"
            item.render_error = str(exc)
            failed += 1

    dump_manifest(manifest_path, items)
    report = {"total": len(items), "rendered": rendered, "failed": failed, "skipped": skipped}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_format_report(report), encoding="utf-8")
    return report


def _format_report(report: Dict[str, Any]) -> str:
    return "\n".join([
        "# 图表渲染报告",
        "",
        f"- 总数: {report['total']}",
        f"- 渲染成功: {report['rendered']}",
        f"- 渲染失败: {report['failed']}",
        f"- 跳过: {report['skipped']}",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="按 images.yaml 渲染图表")
    parser.add_argument("--manifest", required=True, help="images.yaml 路径")
    parser.add_argument("--method", default="auto", help="渲染方法")
    parser.add_argument("--root", default=".", help="解析相对路径的根目录")
    parser.add_argument("--report", action="store_true", help="输出渲染报告")
    args = parser.parse_args()

    report_path = None
    if args.report:
        report_path = Path(args.root) / "workspace/final/images/render_report.md"
    report = render_manifest(Path(args.manifest), Path(args.root), args.method, report_path)
    print(f"[OK] 渲染完成: 成功 {report['rendered']}，失败 {report['failed']}，跳过 {report['skipped']}")


if __name__ == "__main__":
    main()
