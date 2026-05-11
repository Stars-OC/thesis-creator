# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

try:
    from .schemas import load_manifest
except ImportError:
    from schemas import load_manifest


def _resolve_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return root / path


def _should_replace(item) -> bool:
    return item.engine != "user" and item.render_status == "rendered"


def _remove_image_requirement_block(content: str, image_id: str) -> str:
    pattern = re.compile(r"\n?<!--\s*image-requirement\b(?:(?!-->).)*?\bid\s*:\s*" + re.escape(image_id) + r"\b(?:(?!-->).)*?-->\n?", re.DOTALL)
    return pattern.sub("\n", content)


def _placeholder_key(item) -> str:
    return str(item.placeholder_id or item.id)


def update_markdown(input_path: Path, manifest_path: Path, in_place: bool = False, root: Path | None = None) -> str:
    root = root or Path.cwd()
    content = input_path.read_text(encoding="utf-8")

    grouped_items = {}
    for item in load_manifest(manifest_path):
        if not _should_replace(item):
            continue
        grouped_items.setdefault(_placeholder_key(item), []).append(item)

    for placeholder_id, items in grouped_items.items():
        markdown_images = []
        for item in items:
            output_path = _resolve_path(item.output_file, root)
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise ValueError(f"图片文件缺失或为空: {item.id} -> {item.output_file}")
            relative = Path(os.path.relpath(output_path, start=input_path.parent)).as_posix()
            markdown_images.append(f"![{item.title}]({relative})")
        placeholder = f"[{placeholder_id}]"
        content = content.replace(placeholder, "\n\n".join(markdown_images))
        content = _remove_image_requirement_block(content, placeholder_id)

    if in_place:
        input_path.write_text(content, encoding="utf-8")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="将 [image_N] 回填为 Markdown 图片引用")
    parser.add_argument("--input", required=True, help="输入 Markdown 文件")
    parser.add_argument("--manifest", required=True, help="images.yaml 路径")
    parser.add_argument("--root", default=".", help="解析相对路径的根目录")
    parser.add_argument("--in-place", action="store_true", help="原位覆盖 Markdown")
    args = parser.parse_args()

    update_markdown(Path(args.input), Path(args.manifest), args.in_place, Path(args.root))
    print("[OK] Markdown 图片引用回填完成")


if __name__ == "__main__":
    main()
