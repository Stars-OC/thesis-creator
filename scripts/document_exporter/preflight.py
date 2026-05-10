import re
from pathlib import Path
from typing import Tuple

import yaml


def _load_pending_user_image_ids(markdown_path: Path) -> set:
    candidates = [
        markdown_path.parent / "workspace" / "references" / "images.yaml",
        markdown_path.parent.parent / "references" / "images.yaml",
        markdown_path.parent.parent / "workspace" / "references" / "images.yaml",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            images = data.get("images", []) if isinstance(data, dict) else []
            pending = set()
            for item in images:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source", "")).strip()
                status = str(item.get("status", "")).strip()
                diagram_type = str(item.get("diagram_type", "")).strip()
                image_id = str(item.get("id", "")).strip()
                if image_id and source == "user" and (status in {"pending", "pending_user"} or diagram_type == "screenshot"):
                    pending.add(image_id)
            return pending
        except Exception:
            continue
    return set()


def preflight_validate_images(markdown_path: Path) -> Tuple[bool, str]:
    content = markdown_path.read_text(encoding='utf-8')

    remaining = re.findall(r'\[(image_(?:\d+_)?\d+)\]', content)
    if remaining:
        pending_user_ids = _load_pending_user_image_ids(markdown_path)
        blocking = [image_id for image_id in remaining if image_id not in pending_user_ids]
        if blocking:
            return False, f"检测到未替换图片占位符: {', '.join(f'[{item}]' for item in blocking)}"
        return True, f"图片预检查通过，保留用户待补图片: {', '.join(f'[{item}]' for item in remaining)}"

    image_refs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
    missing = []
    empty = []
    for image_ref in image_refs:
        candidate = (markdown_path.parent / image_ref).resolve()
        if not candidate.exists():
            missing.append(image_ref)
            continue
        if candidate.stat().st_size <= 0:
            empty.append(image_ref)

    if missing:
        return False, f"检测到缺失图片文件: {', '.join(missing)}"
    if empty:
        return False, f"检测到空图片文件: {', '.join(empty)}"

    return True, "图片预检查通过"
