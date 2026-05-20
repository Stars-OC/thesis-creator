# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass, field

from typing import List


@dataclass
class ErTable:
    name: str
    fields: List[str] = field(default_factory=list)
    field_display_names: dict[str, str] = field(default_factory=dict)


def _clean_cell(text: str) -> str:
    return text.strip().strip("`'\"").strip()


def _dot_id(value: str) -> str:
    escaped = _clean_cell(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped or "ER图"}"'


def _node_id(*parts: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_一-鿿]+", "_", "_".join(parts))
    return value.strip("_") or "node"


def _field_id(table: str, field_name: str) -> str:
    return _node_id(table, field_name)


def _split_fields(text: str) -> List[str]:
    fields = []
    for part in re.split(r"[,，、;；\s]+", text):
        field_name = _clean_cell(part)
        if field_name and field_name not in fields:
            fields.append(field_name)
    return fields


def _add_table(tables: dict[str, ErTable], name: str, fields_text: str) -> None:
    table_name = _clean_cell(name)
    if not table_name or "表" not in table_name:
        return
    table = tables.setdefault(table_name, ErTable(table_name))
    for field_name in _split_fields(fields_text):
        if field_name not in table.fields:
            table.fields.append(field_name)


def _parse_markdown_table_line(line: str, tables: dict[str, ErTable]) -> None:
    if not line.startswith("|") or "---" in line:
        return
    cells = [_clean_cell(cell) for cell in line.strip("|").split("|")]
    if len(cells) < 2 or cells[0] in {"表名", "数据表", "实体"}:
        return
    _add_table(tables, cells[0], cells[1])


def _normalize_table_name(text: str) -> str:
    value = _clean_cell(text)
    if value.endswith("表结构"):
        return value[:-2]
    return value


def _parse_heading_table_line(line: str) -> str:
    match = re.match(r"^#+\s*(.+?表)(?:结构)?\s*$", line)
    if not match:
        return ""
    return _normalize_table_name(match.group(1))


def _parse_text_table_line(line: str, tables: dict[str, ErTable]) -> None:
    match = re.match(r"^([^：:，,。；;\s]*表)\s*[：:]\s*(.+)$", line)
    if match and _clean_cell(match.group(1)) != "关联表":
        _add_table(tables, _normalize_table_name(match.group(1)), match.group(2))


def _parse_relations(text: str, tables: dict[str, ErTable]) -> List[tuple[str, str, str]]:
    relations = []
    table_names = sorted(tables, key=len, reverse=True)
    table_pattern = "|".join(re.escape(name) for name in table_names)
    explicit_pattern = re.compile(
        rf"(?P<start>{table_pattern})[.。．]\s*(?P<field>[0-9A-Za-z_一-鿿]+).*?关联\s*(?P<end>{table_pattern})[.。．]",
    ) if table_names else None
    for line in text.splitlines():
        if line.strip().startswith("关联表"):
            continue
        if "关联" not in line:
            continue
        if explicit_pattern:
            match = explicit_pattern.search(line)
            if match:
                relation = (
                    match.group("start"),
                    match.group("end"),
                    match.group("field") or "关联",
                )
                if relation not in relations:
                    relations.append(relation)
                continue
        matched = [name for name in table_names if name in line]
        if len(matched) >= 2:
            start, end = matched[0], matched[1]
            relation = (start, end, "关联")
            if relation not in relations:
                relations.append(relation)
    return relations


def _is_overall_er(title: str) -> bool:
    title_text = _clean_cell(title)
    return "总体ER图" in title_text or "总体 ER 图" in title_text



def _normalize_match_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-鿿]+", "", _clean_cell(text)).lower()



def _table_aliases(table_name: str) -> list[str]:
    normalized_name = _clean_cell(table_name)
    aliases = {_normalize_match_text(normalized_name)}

    bracket_match = re.match(r"^(?P<label>[^（(]+?)(?:表)?\s*[（(](?P<physical>[^）)]+)[）)]\s*$", normalized_name)
    if bracket_match:
        label = _clean_cell(bracket_match.group("label"))
        physical = _clean_cell(bracket_match.group("physical"))
        if label:
            aliases.add(_normalize_match_text(f"{label}表"))
            aliases.add(_normalize_match_text(label))
        if physical:
            aliases.add(_normalize_match_text(physical))

    if normalized_name.endswith("表"):
        aliases.add(_normalize_match_text(normalized_name[:-1]))
    return [alias for alias in aliases if alias]



def _focus_tables_from_hint(focus_hint: str, tables: dict[str, ErTable]) -> set[str]:
    normalized_hint = _normalize_match_text(focus_hint)
    if not normalized_hint:
        return set()

    focused = set()
    for table_name in tables:
        if any(alias and alias in normalized_hint for alias in _table_aliases(table_name)):
            focused.add(table_name)
    return focused


def _cardinality_labels(relation_name: str) -> tuple[str, str]:
    relation_text = _clean_cell(relation_name).lower()
    if relation_text.endswith("_id") or relation_text == "关联":
        return "N", "1"
    return "1", "1"


def _infer_relation_field(start: str, end: str, tables: dict[str, ErTable]) -> str:
    start_table = tables.get(_clean_cell(start))
    if not start_table:
        return "关联"

    preferred_fields = {
        "角色表": ["role_id"],
        "知识库表": ["kb_id"],
        "用户表": ["user_id", "owner_id", "uploader_id"],
        "文档表": ["doc_id", "document_id"],
        "文档分段表": ["segment_id"],
        "对话会话表": ["conversation_id"],
        "对话消息表": ["message_id"],
        "API密钥表": ["key_id"],
        "系统配置表": ["config_id"],
        "知识图谱节点表": ["node_id"],
    }
    for field_name in preferred_fields.get(_clean_cell(end), []):
        if field_name in start_table.fields:
            return field_name

    foreign_keys = [field for field in start_table.fields if field.lower().endswith("_id") and field.lower() != "id"]
    if len(foreign_keys) == 1:
        return foreign_keys[0]
    return "关联"


def _semantic_relation_name(start: str, end: str, relation_name: str) -> str:
    relation_text = _clean_cell(relation_name).lower()
    pair_map = {
        ("用户表", "角色表", "role_id"): "拥有",
        ("知识库表", "用户表", "owner_id"): "创建",
        ("文档表", "知识库表", "kb_id"): "包含",
        ("文档分段表", "文档表", "doc_id"): "切分",
        ("向量索引表", "文档分段表", "segment_id"): "索引",
        ("对话会话表", "用户表", "user_id"): "发起",
        ("对话会话表", "知识库表", "kb_id"): "基于",
        ("对话消息表", "对话会话表", "conversation_id"): "包含",
        ("API密钥表", "用户表", "user_id"): "持有",
        ("操作日志表", "用户表", "user_id"): "产生",
        ("知识图谱节点表", "知识库表", "kb_id"): "包含",
    }
    pair_key = (_clean_cell(start), _clean_cell(end), relation_text)
    if pair_key in pair_map:
        return pair_map[pair_key]

    keyword_map = {
        "role_id": "拥有",
        "kb_id": "包含",
        "owner_id": "创建",
        "uploader_id": "上传",
        "doc_id": "切分",
        "document_id": "切分",
        "segment_id": "索引",
        "conversation_id": "包含",
        "message_id": "产生",
        "key_id": "持有",
        "config_id": "配置",
        "node_id": "构成",
        "user_id": "归属",
    }
    if relation_text in keyword_map:
        return keyword_map[relation_text]
    return "对应"


def _relation_node_name(start: str, end: str, relation_name: str, seen: dict[str, int]) -> str:
    base = _semantic_relation_name(start, end, relation_name)
    count = seen.get(base, 0)
    seen[base] = count + 1
    return base + ("​" * count)


def _field_label(table: ErTable, field_name: str, field_language: str = "english") -> str:
    if field_language == "chinese":
        display_name = table.field_display_names.get(field_name, "")
        if display_name:
            return display_name
    return field_name


def build_er_dot_from_background(background_text: str, title: str = "", focus_hint: str = "", field_language: str = "english") -> tuple[str, list[str]]:
    tables: dict[str, ErTable] = {}
    warnings = []
    explicit_relations: list[tuple[str, str, str]] = []
    pending_relation_targets: list[tuple[str, str]] = []
    current_table = ""
    in_field_table = False
    field_table_headers: list[str] = []

    for raw_line in background_text.splitlines():
        line = raw_line.strip()
        if not line:
            in_field_table = False
            continue

        heading_table = _parse_heading_table_line(line)
        if heading_table:
            current_table = heading_table
            tables.setdefault(current_table, ErTable(current_table))
            in_field_table = False
            continue

        relation_match = re.match(r"^关联表\s*[：:]\s*(.+)$", line)
        if relation_match and current_table:
            targets = re.findall(r"[^，,、；;\s]*表", relation_match.group(1))
            for target in targets:
                table_name = _normalize_table_name(target)
                tables.setdefault(table_name, ErTable(table_name))
                pending_relation_targets.append((current_table, table_name))
            continue

        if line.startswith("|") and "---" not in line:
            cells = [_clean_cell(cell) for cell in line.strip("|").split("|")]
            if cells and cells[0] == "字段名":
                in_field_table = True
                field_table_headers = cells
                continue
            if in_field_table and current_table and cells:
                field_name = _clean_cell(cells[0])
                skip_names = {"字段名", "类型", "长度", "允许空", "主键", "说明", "备注"}
                if field_name and field_name not in skip_names:
                    table = tables.setdefault(current_table, ErTable(current_table))
                    if field_name not in table.fields:
                        table.fields.append(field_name)
                    display_headers = {"显示名", "中文名", "字段中文名", "图中名称", "ER显示名"}
                    for index, header in enumerate(field_table_headers):
                        if header in display_headers and index < len(cells):
                            display_name = _clean_cell(cells[index])
                            if display_name and display_name not in skip_names:
                                table.field_display_names[field_name] = display_name
                            break
                    continue

        _parse_markdown_table_line(line, tables)
        _parse_text_table_line(line, tables)

    for start_table, end_table in pending_relation_targets:
        relation_field = _infer_relation_field(start_table, end_table, tables)
        relation = (start_table, end_table, relation_field)
        if relation not in explicit_relations:
            explicit_relations.append(relation)

    graph_name = _clean_cell(title) or "ER图"
    graph_id = _dot_id(graph_name)
    if not tables:
        warnings.append("未从 background.md 识别到明确的数据表定义，请补充表名、字段、主外键关系。")
        return "\n".join([
            f"digraph {graph_id} {{",
            "  graph [rankdir=LR, bgcolor=white];",
            "  node [fontname=\"Microsoft YaHei\", shape=box];",
            f"  {_dot_id(graph_name)} [shape=box, style=rounded];",
            "}",
        ]) + "\n", warnings

    relations = explicit_relations + [relation for relation in _parse_relations(background_text, tables) if relation not in explicit_relations]
    overall_er = _is_overall_er(title)

    if focus_hint and not overall_er:
        focused_tables = _focus_tables_from_hint(focus_hint, tables)
        if not focused_tables:
            warnings.append("未根据单图提示匹配到目标数据表，请在标题、用途或描述中明确写出目标表名。")
            return "\n".join([
                f"digraph {graph_id} {{",
                "  graph [rankdir=LR, bgcolor=white];",
                "  node [fontname=\"Microsoft YaHei\", shape=box];",
                f"  {_dot_id(graph_name)} [shape=box, style=rounded];",
                "}",
            ]) + "\n", warnings
        tables = {name: table for name, table in tables.items() if name in focused_tables}
        relations = [relation for relation in relations if relation[0] in tables and relation[1] in tables]

    lines = [
        f"digraph {graph_id} {{",
        "  graph [rankdir=LR, bgcolor=white, nodesep=0.25, ranksep=0.35, margin=0, pad=0];",
        "  node [fontname=\"Microsoft YaHei\", color=black, fontsize=10, margin=\"0.04,0.02\"];",
        "  edge [fontname=\"Microsoft YaHei\", color=black, fontsize=9, arrowsize=0.6];",
    ]
    for table in tables.values():
        table_id = _dot_id(table.name)
        lines.append(f"  {table_id} [shape=box];")
        if overall_er:
            continue
        for field_name in table.fields:
            field_node = _dot_id(_field_id(table.name, field_name))
            display_label = _field_label(table, field_name, field_language)
            if display_label != field_name:
                lines.append(f"  {field_node} [shape=ellipse, label={_dot_id(display_label)}];")
            else:
                lines.append(f"  {field_node} [shape=ellipse];")
            lines.append(f"  {table_id} -> {field_node} [style=dotted, arrowhead=none];")
    relation_name_seen: dict[str, int] = {}
    for start, end, relation_name in relations:
        relation_id = _dot_id(_relation_node_name(start, end, relation_name, relation_name_seen))
        lines.append(f"  {relation_id} [shape=diamond];")
        if overall_er:
            tail_label, head_label = _cardinality_labels(relation_name)
            lines.append(f"  {_dot_id(start)} -> {relation_id} [arrowhead=none, taillabel=\"{tail_label}\", labeldistance=1.5];")
            lines.append(f"  {relation_id} -> {_dot_id(end)} [arrowhead=none, headlabel=\"{head_label}\", labeldistance=1.5];")
            continue
        lines.append(f"  {_dot_id(start)} -> {relation_id} [arrowhead=none];")
        lines.append(f"  {relation_id} -> {_dot_id(end)} [arrowhead=none];")
    lines.append("}")
    return "\n".join(lines) + "\n", warnings
