# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

REQUIRED_FIELDS = [
    "id",
    "title",
    "chapter",
    "section",
    "source",
    "diagram_type",
    "purpose",
    "fact_source",
    "placement",
    "status",
    "description",
]


@dataclass
class ImageItem:
    id: str
    title: str
    chapter: str
    section: str
    source: str
    diagram_type: str
    purpose: str
    fact_source: str
    placement: str
    status: str
    description: str
    engine: str
    source_file: str
    output_file: str
    render_status: str = "pending"
    prompt_hint: str = ""
    render_error: str = ""
    placeholder_id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageItem":
        missing = [field for field in REQUIRED_FIELDS if not str(data.get(field, "")).strip()]
        if missing:
            image_id = str(data.get("id", "<unknown>"))
            raise ValueError(f"{image_id} 缺少必填字段: {', '.join(missing)}")

        item = dict(data)
        diagram_type = str(item.get("diagram_type", "")).strip().lower()
        if diagram_type == "architecture":
            item["source"] = "user"
            item["engine"] = "user"
            item["status"] = "pending_user"
            item["render_status"] = "pending_user"
            item["source_file"] = ""
            item["prompt_hint"] = str(item.get("prompt_hint") or "架构图由用户自行生成；如需 AI 生成，请使用 GPT image 生图后作为用户图片补入。")
        item["engine"] = str(item.get("engine") or infer_engine(item))
        if item["engine"] == "user":
            item["source_file"] = ""
        else:
            item["source_file"] = str(item.get("source_file") or default_source_file(item["id"], item["engine"]))
        item["output_file"] = str(item.get("output_file") or f"workspace/final/images/{item['id']}.png")
        item["render_status"] = str(item.get("render_status") or "pending")
        item["prompt_hint"] = str(item.get("prompt_hint") or "")
        item["render_error"] = str(item.get("render_error") or "")
        return cls(**{field.name: item.get(field.name, "") for field in cls.__dataclass_fields__.values()})

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value != ""}


def infer_engine(item: Dict[str, Any]) -> str:
    source = str(item.get("source", "")).strip().lower()
    diagram_type = str(item.get("diagram_type", "")).strip().lower()
    if source == "user":
        return "user"
    if diagram_type in {"er", "erd", "dot", "overall_er", "overall-er", "总体er图", "总体er"}:
        return "graphviz"
    if diagram_type in {"sequence", "usecase", "class", "activity", "plantuml", "flowchart", "flow", "workflow", "流程图"}:
        return "plantuml"
    return "mermaid"


def source_suffix(engine: str) -> str:
    suffixes = {
        "graphviz": ".dot",
        "mermaid": ".mmd",
        "plantuml": ".puml",
    }
    return suffixes.get(engine, "")


def default_source_file(image_id: str, engine: str) -> str:
    suffix = source_suffix(engine)
    if not suffix:
        return ""
    return f"workspace/final/images/sources/{image_id}{suffix}"


def load_manifest(path: Path) -> List[ImageItem]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    images = data.get("images", [])
    if not isinstance(images, list):
        raise ValueError("images.yaml 中的 images 必须是列表")
    return [ImageItem.from_dict(item) for item in images]


def dump_manifest(path: Path, items: List[ImageItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"images": [item.to_dict() for item in items]}
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
