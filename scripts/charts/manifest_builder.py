# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

try:
    from .schemas import ImageItem, dump_manifest
except ImportError:
    from schemas import ImageItem, dump_manifest

IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\[(image_(?:\d+_)?\d+)\]")
REQUIREMENT_BLOCK_PATTERN = re.compile(
    r"<!--\s*image-requirement\s*\n(.*?)\n\s*-->",
    re.DOTALL | re.IGNORECASE,
)


def parse_image_placeholders(content: str) -> List[str]:
    seen = set()
    placeholders: List[str] = []
    for match in IMAGE_PLACEHOLDER_PATTERN.finditer(content):
        image_id = match.group(1)
        if image_id in seen:
            continue
        seen.add(image_id)
        placeholders.append(image_id)
    return placeholders


def parse_requirement_blocks(content: str) -> Dict[str, Dict[str, Any]]:
    requirements: Dict[str, Dict[str, Any]] = {}
    for match in REQUIREMENT_BLOCK_PATTERN.finditer(content):
        raw_yaml = match.group(1).strip()
        data = yaml.safe_load(raw_yaml) or {}
        if not isinstance(data, dict):
            continue
        image_id = str(data.get("id", "")).strip()
        if image_id:
            requirements[image_id] = data
    return requirements


def remove_requirement_blocks(content: str) -> str:
    return REQUIREMENT_BLOCK_PATTERN.sub("", content)


def _missing_requirement_item(image_id: str) -> ImageItem:
    return ImageItem(
        id=image_id,
        title=image_id,
        chapter="待补充",
        section="待补充",
        source="ai",
        diagram_type="unknown",
        purpose="待补充图片用途",
        fact_source="待补充事实来源",
        placement="待补充图文位置说明",
        status="missing_requirement",
        description="正文中存在图片占位符，但缺少 image-requirement 需求块。",
        engine="mermaid",
        source_file=f"workspace/final/images/sources/{image_id}.mmd",
        output_file=f"workspace/final/images/{image_id}.png",
        render_status="blocked",
        prompt_hint="请先补充 image-requirement 需求块，再生成图表源码。",
    )


def build_manifest(input_path: Path, output_path: Path, image_dir: Path | None = None) -> List[ImageItem]:
    content = input_path.read_text(encoding="utf-8")
    placeholders = parse_image_placeholders(content)
    requirements = parse_requirement_blocks(content)

    items: List[ImageItem] = []
    for image_id in placeholders:
        data = requirements.get(image_id)
        if not data:
            items.append(_missing_requirement_item(image_id))
            continue
        data = dict(data)
        data.setdefault("id", image_id)
        if image_dir is not None and not data.get("output_file"):
            data["output_file"] = f"{image_dir.as_posix().rstrip('/')}/{image_id}.png"
        items.append(ImageItem.from_dict(data))

    dump_manifest(output_path, items)
    input_path.write_text(remove_requirement_blocks(content), encoding="utf-8")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="从 Markdown 图片占位符生成 images.yaml")
    parser.add_argument("--input", "-i", required=True, help="输入 Markdown 文件")
    parser.add_argument("--output", "-o", required=True, help="输出 images.yaml 路径")
    parser.add_argument("--images-dir", default="workspace/final/images", help="图片输出目录")
    args = parser.parse_args()

    items = build_manifest(Path(args.input), Path(args.output), Path(args.images_dir))
    missing = [item.id for item in items if item.status == "missing_requirement"]
    print(f"[OK] 已生成图片清单: {args.output}")
    print(f"[INFO] 图片记录数: {len(items)}")
    if missing:
        print(f"[WARN] 缺少需求块: {', '.join(missing)}")


if __name__ == "__main__":
    main()
