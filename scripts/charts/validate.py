# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

try:
    from .schemas import load_manifest
except ImportError:
    from schemas import load_manifest


def _resolve_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return root / path


def validate_pipeline(input_path: Path, manifest_path: Path, root: Path | None = None, images_dir: Path | None = None) -> Dict[str, Any]:
    root = root or Path.cwd()
    content = input_path.read_text(encoding="utf-8")
    errors: List[str] = []
    user_required: List[str] = []

    for item in load_manifest(manifest_path):
        placeholder = f"[{item.id}]"
        if item.engine == "user":
            if item.status in {"pending_user", "pending"} and placeholder in content:
                user_required.append(item.id)
            continue

        source_path = _resolve_path(item.source_file, root)
        if not source_path.exists():
            errors.append(f"{item.id} 源码文件缺失: {item.source_file}")

        output_path = _resolve_path(item.output_file, root)
        if item.render_status == "rendered":
            if placeholder in content:
                errors.append(f"{item.id} 已渲染但正文仍残留占位符")
            if not output_path.exists():
                errors.append(f"{item.id} 图片文件缺失: {item.output_file}")
            elif output_path.stat().st_size <= 1024:
                errors.append(f"{item.id} 图片文件小于等于 1KB: {item.output_file}")

    return {"errors": errors, "user_required": user_required}


def main() -> None:
    parser = argparse.ArgumentParser(description="校验图表生成链路完整性")
    parser.add_argument("--input", required=True, help="输入 Markdown 文件")
    parser.add_argument("--manifest", required=True, help="images.yaml 路径")
    parser.add_argument("--root", default=".", help="解析相对路径的根目录")
    parser.add_argument("--images-dir", default="workspace/final/images", help="图片目录")
    args = parser.parse_args()

    report = validate_pipeline(Path(args.input), Path(args.manifest), Path(args.root), Path(args.images_dir))
    if report["errors"]:
        for error in report["errors"]:
            print(f"[FAIL] {error}")
        raise SystemExit(1)
    if report["user_required"]:
        print(f"[WARN] 待用户补充图片: {', '.join(report['user_required'])}")
    print("[OK] 图表链路校验通过")


if __name__ == "__main__":
    main()
