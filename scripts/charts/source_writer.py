# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List

import yaml

try:
    from .er_dot_builder import build_er_dot_from_background
    from .single_entity_er_dot_builder import build_single_entity_er_dot
    from .schemas import ImageItem, dump_manifest, load_manifest, source_suffix
except ImportError:
    from er_dot_builder import build_er_dot_from_background
    from single_entity_er_dot_builder import build_single_entity_er_dot
    from schemas import ImageItem, dump_manifest, load_manifest, source_suffix

PLACEHOLDER_MARKER = "CHART_SOURCE_PLACEHOLDER"

USECASE_PROMPT = """请基于以下业务描述，生成一个符合软件工程论文规范的 PlantUML 用例图（Use Case Diagram）。

要求：

1. 使用标准 UML 用例图规范
2. 风格偏学术化、简洁、黑白
3. 不使用彩色、渐变、阴影
4. actor 使用中文
5. 系统边界使用 rectangle 包裹
6. 用例名称简洁，避免长句
7. 控制整体节点数量，保持论文可读性
8. 避免复杂交叉线
9. 使用 left to right direction 布局
10. 输出完整可运行的 PlantUML 代码
11. 使用如下 skinparam 风格：

skinparam shadowing false
skinparam packageStyle rectangle
skinparam usecase {
    BackgroundColor white
    BorderColor black
}
skinparam defaultFontName Microsoft YaHei

12. 若功能较多，仅保留核心业务用例
13. include / extend 仅在确实存在复用关系时使用
14. 图的整体风格应接近高校计算机专业毕业论文中的 UML 用例图
"""


def _source_path_for_item(item: ImageItem, sources_dir: Path) -> Path | None:
    suffix = source_suffix(item.engine)
    if not suffix:
        return None
    return sources_dir / f"{item.id}{suffix}"


def _apply_engine(item: ImageItem, engine: str) -> None:
    item.engine = engine
    item.source_file = ""


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
    if item.diagram_type.strip().lower() == "usecase":
        lines.extend(f"# {line}" if line else "#" for line in USECASE_PROMPT.splitlines())
    if item.prompt_hint:
        lines.append(f"# prompt_hint: {item.prompt_hint}")
    lines.append("# 请用正式图表源码替换本文件内容。")
    return "\n".join(lines) + "\n"


def _is_er_item(item: ImageItem) -> bool:
    return item.diagram_type.strip().lower() in {"er", "erd", "dot", "overall_er", "overall-er", "entity_er", "entity-er", "single_entity_er", "single-entity-er", "总体er图", "总体er", "实体er图", "单实体er图"}


def _is_single_entity_er_item(item: ImageItem) -> bool:
    return item.diagram_type.strip().lower() in {"entity_er", "entity-er", "single_entity_er", "single-entity-er", "实体er图", "单实体er图"}


def _workspace_root(manifest_path: Path) -> Path:
    return manifest_path.parent.parent.parent if len(manifest_path.parents) >= 3 else manifest_path.parent


def _resolve_fact_source(item: ImageItem, manifest_path: Path) -> Path:
    root = _workspace_root(manifest_path)
    background = root / "references" / "prompt" / "background.md"
    if _is_er_item(item) and background.exists():
        return background
    fact_source = Path(item.fact_source) if item.fact_source else Path("references/prompt/background.md")
    if fact_source.is_absolute():
        return fact_source
    primary = root / fact_source
    if primary.exists():
        return primary
    return background


def _er_modeling_config(manifest_path: Path) -> dict:
    config = _workspace_root(manifest_path) / ".thesis-config.yaml"
    if not config.exists():
        return {}
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    er_modeling = data.get("er_modeling") or {}
    if not isinstance(er_modeling, dict):
        return {}
    return er_modeling



def _er_graph_type(manifest_path: Path) -> str:
    er_modeling = _er_modeling_config(manifest_path)
    return str(er_modeling.get("graph_type") or "dot").strip().lower()


def _global_er_dot_mode(manifest_path: Path) -> str:
    er_modeling = _er_modeling_config(manifest_path)
    return str(er_modeling.get("dot_mode") or "").strip().lower()


def _field_language(manifest_path: Path) -> str:
    er_modeling = _er_modeling_config(manifest_path)
    value = str(er_modeling.get("field_language") or "english").strip().lower()
    return value if value in {"english", "chinese"} else "english"


def _effective_er_dot_mode(item: ImageItem, manifest_path: Path) -> str:
    if _er_graph_type(manifest_path) != "dot":
        return ""
    if item.dot_mode:
        return item.dot_mode.strip().lower()
    return _global_er_dot_mode(manifest_path)


def _should_use_single_entity_ring(item: ImageItem, manifest_path: Path) -> bool:
    return _is_single_entity_er_item(item) and _effective_er_dot_mode(item, manifest_path) in {"", "textbook-single-entity-ring"}


def _er_diagram_scope(manifest_path: Path) -> str:
    er_modeling = _er_modeling_config(manifest_path)
    return str(er_modeling.get("diagram_scope") or "multi").strip().lower()


def _build_erd_source(item: ImageItem, manifest_path: Path) -> str:
    fact_source = _resolve_fact_source(item, manifest_path)
    background = fact_source.read_text(encoding="utf-8") if fact_source.exists() else ""
    lines = ["erDiagram", f"  %% {item.title}"]
    for raw_line in background.splitlines():
        if "表" in raw_line and "|" in raw_line and "---" not in raw_line:
            cells = [cell.strip().strip("`'\"") for cell in raw_line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in {"表名", "数据表", "实体"}:
                table = cells[0]
                fields = [field.strip() for field in cells[1].replace("，", ",").split(",") if field.strip()]
                lines.append(f"  {table} {{")
                for field in fields:
                    lines.append(f"    string {field}")
                lines.append("  }")
    return "\n".join(lines) + "\n"


def _er_dot_source(item: ImageItem, manifest_path: Path) -> str:
    fact_source = _resolve_fact_source(item, manifest_path)
    background = fact_source.read_text(encoding="utf-8") if fact_source.exists() else ""
    focus_hint = ""
    if _er_diagram_scope(manifest_path) == "single" and not _is_overall_er_item(item):
        focus_hint = " ".join(part for part in [item.title, item.purpose, item.description] if part)
    field_lang = _field_language(manifest_path)
    dot, warnings = build_er_dot_from_background(background, title=item.title, focus_hint=focus_hint, field_language=field_lang)
    if warnings:
        item.prompt_hint = "; ".join(warnings)
    return dot


def _single_entity_er_dot_source(item: ImageItem, manifest_path: Path) -> str:
    fact_source = _resolve_fact_source(item, manifest_path)
    background = fact_source.read_text(encoding="utf-8") if fact_source.exists() else ""
    focus_hint = " ".join(part for part in [item.title, item.purpose, item.description] if part)
    field_lang = _field_language(manifest_path)
    dot, warnings = build_single_entity_er_dot(background, title=item.title, focus_hint=focus_hint, field_language=field_lang)
    if warnings:
        item.prompt_hint = "; ".join(warnings)
    return dot


def _is_overall_er_item(item: ImageItem) -> bool:
    return item.diagram_type.strip().lower() in {"overall_er", "overall-er", "总体er图", "总体er"}


def _prioritize_overall_er(items: List[ImageItem]) -> List[ImageItem]:
    return [item for item in items if _is_overall_er_item(item)] + [item for item in items if not _is_overall_er_item(item)]


def _should_write_source(item: ImageItem, source_path: Path, manifest_path: Path) -> bool:
    if not source_path.exists():
        return True
    field_lang = _field_language(manifest_path)
    if _should_use_single_entity_ring(item, manifest_path):
        content = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
        has_chinese_fields = any(cn in content for cn in ["编号", "名称", "时间", "状态", "描述", "密码", "邮箱", "手机", "地址"])
        has_overlap_true = "overlap=true" in content
        has_fixed_field_pos = bool(re.search(r'pos="[^"]*!"', content.replace('pos="0,0!"', "")))
        has_field_pos = any(
            "shape=ellipse" in attrs and "pos=" in attrs
            for attrs in re.findall(r'\[([^\]]+)\]', content.replace(" ", ""))
        )
        has_overwide_edge_len = any(
            float(value) > 4.0 for value in re.findall(r'\blen=(\d+(?:\.\d+)?)', content)
        )
        has_spline_curves = "splines=true" in content or "splines=curved" in content or "splines=polyline" in content
        return (
            "label=" in content
            or "rank=" in content
            or "graph ER" not in content
            or "layout=neato" not in content
            or 'pos="' not in content
            or "shape=diamond" in content
            or "->" in content
            or "fontname=" not in content
            or has_overlap_true
            or has_fixed_field_pos
            or has_field_pos
            or has_overwide_edge_len
            or has_spline_curves
            or (field_lang == "chinese" and not has_chinese_fields)
            or (field_lang == "english" and has_chinese_fields)
        )
    if not _is_er_item(item):
        return False
    content = source_path.read_text(encoding="utf-8")
    has_chinese_fields = any(cn in content for cn in ["编号", "名称", "时间", "状态", "描述", "密码", "邮箱", "手机", "地址"])
    if item.engine == "graphviz":
        stripped = content.lstrip()
        if _is_overall_er_item(item):
            return (
                "label=" in content
                or not stripped.startswith("digraph")
                or "shape=box" not in content
                or "shape=diamond" not in content
                or "shape=ellipse" in content
                or 'taillabel="' not in content
                or 'headlabel="' not in content
                or '_关联_' in content
                or '_id_关联_' in content
                or '"关联" [shape=diamond];' in content
                or '"关联​" [shape=diamond];' in content
                or (field_lang == "chinese" and not has_chinese_fields)
                or (field_lang == "english" and has_chinese_fields)
            )
        if _er_diagram_scope(manifest_path) == "single":
            return True
        return (
            "label=" in content
            or not stripped.startswith("digraph")
            or ("shape=box" not in content and "shape=ellipse" not in content)
            or "_关联_" in content
            or "_id_关联_" in content
            or (field_lang == "chinese" and not has_chinese_fields)
            or (field_lang == "english" and has_chinese_fields)
        )
    if item.engine == "mermaid":
        return "erDiagram" not in content
    return False


def prepare_sources(manifest_path: Path, sources_dir: Path) -> List[ImageItem]:
    items = load_manifest(manifest_path)
    sources_dir.mkdir(parents=True, exist_ok=True)

    updated: List[ImageItem] = []
    for item in items:
        if _is_single_entity_er_item(item):
            _apply_engine(item, "graphviz")
        elif _is_er_item(item):
            graph_type = _er_graph_type(manifest_path)
            if graph_type == "erd":
                _apply_engine(item, "mermaid")
            else:
                _apply_engine(item, "graphviz")
        if item.engine == "user":
            updated.append(item)
            continue
        source_path = _source_path_for_item(item, sources_dir)
        if source_path is None:
            updated.append(item)
            continue
        item.source_file = _manifest_source_path(item, source_path)
        if _should_write_source(item, source_path, manifest_path):
            if _should_use_single_entity_ring(item, manifest_path) and item.engine == "graphviz":
                source = _single_entity_er_dot_source(item, manifest_path)
            elif _is_er_item(item) and item.engine == "graphviz":
                source = _er_dot_source(item, manifest_path)
            elif _is_er_item(item) and item.engine == "mermaid":
                source = _build_erd_source(item, manifest_path)
            else:
                source = _placeholder_source(item)
            source_path.write_text(source, encoding="utf-8")
        updated.append(item)

    updated = _prioritize_overall_er(updated)
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
