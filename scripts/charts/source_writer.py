# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

try:
    from .schemas import ImageItem, dump_manifest, load_manifest, source_suffix
except ImportError:
    from schemas import ImageItem, dump_manifest, load_manifest, source_suffix

PLACEHOLDER_MARKER = "CHART_SOURCE_PLACEHOLDER"


def _source_path_for_item(item: ImageItem, sources_dir: Path) -> Path | None:
    suffix = source_suffix(item.engine)
    if not suffix:
        return None
    return sources_dir / f"{item.id}{suffix}"


def _manifest_source_path(item: ImageItem, source_path: Path) -> str:
    marker = Path("workspace/final/images/sources") / source_path.name
    return marker.as_posix()


def _placeholder_source(item: ImageItem) -> str:
    lines = [
        f"# {PLACEHOLDER_MARKER}",
        f"# id: {item.id}",
        f"# title: {item.title}",
        f"# engine: {item.engine}",
        f"# purpose: {item.purpose}",
        f"# description: {item.description}",
    ]
    if item.prompt_hint:
        lines.append(f"# prompt_hint: {item.prompt_hint}")
    lines.append("# 请用正式图表源码替换本文件内容。")
    return "\n".join(lines) + "\n"


def prepare_sources(manifest_path: Path, sources_dir: Path) -> List[ImageItem]:
    items = load_manifest(manifest_path)
    sources_dir.mkdir(parents=True, exist_ok=True)

    updated: List[ImageItem] = []
    for item in items:
        if item.engine == "user":
            updated.append(item)
            continue
        source_path = _source_path_for_item(item, sources_dir)
        if source_path is None:
            updated.append(item)
            continue
        item.source_file = _manifest_source_path(item, source_path)
        if not source_path.exists():
            source_path.write_text(_placeholder_source(item), encoding="utf-8")
        updated.append(item)

    dump_manifest(manifest_path, updated)
    return updated


def _resolve_source_path(source_file: str, root: Path) -> Path:
    source = Path(source_file)
    if source.is_absolute():
        return source
    primary = root / source
    if primary.exists():
        return primary
    fallback = root / "sources" / source.name
    if fallback.exists():
        return fallback
    return primary


def validate_sources(manifest_path: Path, root: Path | None = None) -> None:
    root = root or Path.cwd()
    missing = []
    placeholders = []
    for item in load_manifest(manifest_path):
        if item.engine == "user":
            continue
        if not item.source_file:
            missing.append(item.id)
            continue
        source_path = _resolve_source_path(item.source_file, root)
        if not source_path.exists():
            missing.append(item.id)
            continue
        content = source_path.read_text(encoding="utf-8")
        if PLACEHOLDER_MARKER in content:
            placeholders.append(item.id)
    if missing:
        raise ValueError(f"源码文件缺失: {', '.join(missing)}")
    if placeholders:
        raise ValueError(f"仍是占位源码: {', '.join(placeholders)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="准备或校验图表源码文件")
    parser.add_argument("--manifest", required=True, help="images.yaml 路径")
    parser.add_argument("--sources-dir", default="workspace/final/images/sources", help="源码目录")
    parser.add_argument("--validate", action="store_true", help="校验源码文件已由大模型填充")
    parser.add_argument("--root", default=".", help="解析相对路径的根目录")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    if args.validate:
        validate_sources(manifest, Path(args.root))
        print("[OK] 图表源码校验通过")
        return

    items = prepare_sources(manifest, Path(args.sources_dir))
    generated = [item.id for item in items if item.engine != "user"]
    print(f"[OK] 已准备图表源码文件: {len(generated)} 个")


if __name__ == "__main__":
    main()
