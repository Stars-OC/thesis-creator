# -*- coding: utf-8 -*-

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

IMAGE_PATTERN = re.compile(r"\[(image_(?:\d+_)?\d+)\]")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FIGURE_TITLE_PATTERN = re.compile(r"^(图\d+-\d+\s+.+)$")
INLINE_PLACEHOLDER_TITLE_PATTERN = re.compile(r"^>\s*\*\*\[(image_(?:\d+_)?\d+)\][：:]\s*(.+?)\*\*\s*$")
BLOCK_METADATA_PATTERN = re.compile(r"^>\s*-\s*(图表编号|图表名称|图表类型|内容描述)[：:]\s*(.*)$")
METADATA_PREFIX_PATTERN = re.compile(r"^(绘图说明|绘制说明|图片说明|截图要求|图表说明|说明)[：:]\s*(.*)$")


def _chapter_from_heading(text: str) -> str:
    match = re.search(r"第\s*([一二三四五六七八九十\d]+)\s*章", text)
    if match:
        return f"第{match.group(1)}章"
    return ""


def _section_from_heading(text: str) -> str:
    match = re.search(r"(\d+(?:\.\d+)+)", text)
    return match.group(1) if match else ""


def _detect_diagram_type(title: str, description: str, chapter: str) -> str:
    text = f"{title} {description}".lower()
    if "截图" in text or chapter == "第5章":
        return "screenshot"
    if "e-r" in text or "er图" in text or "er 图" in text or "实体" in text:
        return "er"
    if "架构" in text:
        return "architecture"
    if "模块" in text:
        return "module"
    if "时序" in text:
        return "sequence"
    return "flowchart"


def _source_for_image(chapter: str, diagram_type: str) -> str:
    if chapter == "第5章" or diagram_type == "screenshot":
        return "user"
    return "ai"


def _status_for_source(source: str) -> str:
    return "pending_user" if source == "user" else "pending"


def _extract_context(lines: List[str], start_index: int) -> Dict[str, str]:
    title = ""
    description_parts: List[str] = []
    consumed_indexes = set()

    current_line = lines[start_index].strip()
    inline_title_match = INLINE_PLACEHOLDER_TITLE_PATTERN.match(current_line)
    if inline_title_match:
        title = inline_title_match.group(2).strip()

    for index in range(start_index + 1, min(len(lines), start_index + 8)):
        line = lines[index].strip()
        if not line:
            continue
        if IMAGE_PATTERN.search(line) or HEADING_PATTERN.match(line):
            break
        title_match = FIGURE_TITLE_PATTERN.match(line)
        if title_match and not title:
            title = title_match.group(1).strip()
            consumed_indexes.add(index)
            continue
        block_metadata_match = BLOCK_METADATA_PATTERN.match(line)
        if block_metadata_match:
            key = block_metadata_match.group(1).strip()
            value = block_metadata_match.group(2).strip()
            if key == "图表名称" and value and not title:
                title = value
            elif key == "内容描述" and value:
                description_parts.append(value)
            consumed_indexes.add(index)
            continue
        metadata_match = METADATA_PREFIX_PATTERN.match(line)
        if metadata_match:
            value = metadata_match.group(2).strip()
            if value:
                description_parts.append(value)
            consumed_indexes.add(index)
            continue
        if not title:
            title = line.strip()
            consumed_indexes.add(index)
        else:
            break

    return {
        "title": title,
        "description": " ".join(description_parts).strip(),
        "consumed": ",".join(str(item) for item in sorted(consumed_indexes)),
    }


def _clean_markdown(lines: List[str], consumed_indexes: set[int]) -> str:
    kept = []
    for index, line in enumerate(lines):
        if index in consumed_indexes:
            continue
        if METADATA_PREFIX_PATTERN.match(line.strip()):
            continue
        kept.append(line)
    return "\n".join(kept)


def build_image_manifest_from_markdown(markdown_path: Path, manifest_path: Path, clean: bool = False) -> List[Dict[str, Any]]:
    markdown_path = Path(markdown_path)
    manifest_path = Path(manifest_path)
    lines = markdown_path.read_text(encoding="utf-8").splitlines()

    current_chapter = ""
    current_section = ""
    images: List[Dict[str, Any]] = []
    consumed_indexes: set[int] = set()

    for index, line in enumerate(lines):
        heading = HEADING_PATTERN.match(line.strip())
        if heading:
            heading_text = heading.group(2).strip()
            chapter = _chapter_from_heading(heading_text)
            section = _section_from_heading(heading_text)
            if chapter:
                current_chapter = chapter
            if section:
                current_section = section

        for match in IMAGE_PATTERN.finditer(line):
            image_id = match.group(1)
            context = _extract_context(lines, index)
            consumed_indexes.update(int(item) for item in context["consumed"].split(",") if item)
            title = context["title"] or image_id
            description = context["description"] or title
            diagram_type = _detect_diagram_type(title, description, current_chapter)
            source = _source_for_image(current_chapter, diagram_type)
            fact_source = "用户提供的系统实际运行截图" if source == "user" else "正文图片需求描述；ER 图优先使用当前 DDL / 表结构，不足时回退 background.md"
            images.append({
                "id": image_id,
                "title": title,
                "chapter": current_chapter,
                "section": current_section,
                "source": source,
                "diagram_type": diagram_type,
                "purpose": title,
                "fact_source": fact_source,
                "placement": "正文图前引导语之后，图后分析语之前",
                "status": _status_for_source(source),
                "description": description,
            })

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump({"images": images}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    if clean:
        markdown_path.write_text(_clean_markdown(lines, consumed_indexes), encoding="utf-8")

    return images


def main():
    parser = argparse.ArgumentParser(description="从 Markdown 正文抽取图片需求清单")
    parser.add_argument("input", help="输入 Markdown 文件")
    parser.add_argument("--manifest", default="workspace/references/images.yaml", help="输出 images.yaml 路径")
    parser.add_argument("--clean", action="store_true", help="清理正文冗余图片说明")
    args = parser.parse_args()

    images = build_image_manifest_from_markdown(Path(args.input), Path(args.manifest), clean=args.clean)
    print(f"[成功] 已生成图片需求清单: {args.manifest}，共 {len(images)} 条")


if __name__ == "__main__":
    main()
