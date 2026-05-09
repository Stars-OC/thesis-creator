# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ErTable:
    name: str
    fields: List[str] = field(default_factory=list)


def _clean_cell(text: str) -> str:
    return text.strip().strip("`'\"").strip()


def _dot_id(value: str) -> str:
    escaped = _clean_cell(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped or "ER图"}"'


def _field_id(table: str, field_name: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_一-鿿]+", "_", f"{table}_{field_name}")
    return value.strip("_") or "field"


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


def _parse_text_table_line(line: str, tables: dict[str, ErTable]) -> None:
    match = re.match(r"^([^：:，,。；;\s]*表)\s*[：:]\s*(.+)$", line)
    if match:
        _add_table(tables, match.group(1), match.group(2))


def _parse_relations(text: str, tables: dict[str, ErTable]) -> List[tuple[str, str]]:
    relations = []
    table_names = sorted(tables, key=len, reverse=True)
    for line in text.splitlines():
        if "关联" not in line:
            continue
        matched = [name for name in table_names if name in line]
        if len(matched) >= 2:
            start, end = matched[0], matched[1]
            if (start, end) not in relations:
                relations.append((start, end))
    return relations


def build_er_dot_from_background(background_text: str, title: str = "") -> tuple[str, list[str]]:
    tables: dict[str, ErTable] = {}
    warnings = []

    for raw_line in background_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        _parse_markdown_table_line(line, tables)
        _parse_text_table_line(line, tables)

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

    relations = _parse_relations(background_text, tables)
    lines = [
        f"digraph {graph_id} {{",
        "  graph [rankdir=LR, bgcolor=white, nodesep=0.5, ranksep=0.8];",
        "  node [fontname=\"Microsoft YaHei\", shape=box, style=rounded];",
        "  edge [fontname=\"Microsoft YaHei\", color=\"#555555\"];",
    ]
    for table in tables.values():
        table_id = _dot_id(table.name)
        lines.append(f"  {table_id} [shape=box, style=\"rounded,filled\", fillcolor=\"#F8FBFF\"];")
        for field_name in table.fields:
            field_node = _dot_id(_field_id(table.name, field_name))
            lines.append(f"  {field_node} [shape=plaintext];")
            lines.append(f"  {table_id} -> {field_node} [style=dotted, arrowhead=none];")
    for start, end in relations:
        lines.append(f"  {_dot_id(start)} -> {_dot_id(end)};")
    lines.append("}")
    return "\n".join(lines) + "\n", warnings
