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


# 字段中文名来自大模型生成的 background.md 显式显示名列；脚本只负责读取，不做语义翻译或强制截断。


def _clean_cell(text: str) -> str:
    return text.strip().strip("`'\"").strip()


def _normalize_match_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-鿿]+", "", _clean_cell(text)).lower()


def _table_aliases(table_name: str) -> list[str]:
    normalized_name = _clean_cell(table_name)
    aliases = {_normalize_match_text(normalized_name)}

    bracket_match = re.match(
        r"^(?P<label>[^（(]+?)(?:表)?\s*[（(](?P<physical>[^）)]+)[）)]\s*$",
        normalized_name,
    )
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


def _dot_id(value: str) -> str:
    escaped = _clean_cell(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped or "ER图"}"'


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


def _normalize_table_name(text: str) -> str:
    value = _clean_cell(text)
    if value.endswith("表结构"):
        return value[:-2]
    return value


def _parse_markdown_table_line(line: str, tables: dict[str, ErTable]) -> None:
    if not line.startswith("|") or "---" in line:
        return
    cells = [_clean_cell(cell) for cell in line.strip("|").split("|")]
    if len(cells) < 2 or cells[0] in {"表名", "数据表", "实体"}:
        return
    _add_table(tables, cells[0], cells[1])


def _parse_heading_table_line(line: str) -> str:
    match = re.match(r"^#+\s*(.+?表)(?:结构)?\s*$", line)
    if not match:
        return ""
    return _normalize_table_name(match.group(1))


def _parse_text_table_line(line: str, tables: dict[str, ErTable]) -> None:
    match = re.match(r"^([^：:，,。；;\s]*表)\s*[：:]\s*(.+)$", line)
    if match and _clean_cell(match.group(1)) != "关联表":
        _add_table(tables, _normalize_table_name(match.group(1)), match.group(2))


def _parse_tables(background_text: str) -> dict[str, ErTable]:
    tables: dict[str, ErTable] = {}
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

    return tables




def _focus_tables_from_hint(focus_hint: str, tables: dict[str, ErTable]) -> set[str]:
    normalized_hint = _normalize_match_text(focus_hint)
    if not normalized_hint:
        return set()

    matches: list[tuple[int, str]] = []
    for table_name in tables:
        alias_lengths = [len(alias) for alias in _table_aliases(table_name) if alias and alias in normalized_hint]
        if alias_lengths:
            matches.append((max(alias_lengths), table_name))
    if not matches:
        return set()
    max_len = max(length for length, _ in matches)
    return {table_name for length, table_name in matches if length == max_len}


def _field_edge_len(count: int) -> float:
    if count <= 0:
        return 1
    return 1 if count <= 8 else 1.4


def extract_single_entity_er_context(
    background_text: str, focus_hint: str = ""
) -> tuple[str, ErTable | None, list[str]]:
    tables = _parse_tables(background_text)
    warnings = []

    focused_tables = _focus_tables_from_hint(focus_hint, tables)
    if len(focused_tables) == 1:
        target_table_name = next(iter(focused_tables))
    elif not focused_tables:
        target_table_name = ""
        if not tables:
            warnings.append("未从 background.md 识别到明确的数据表定义。")
        elif len(tables) == 1:
            target_table_name = next(iter(tables))
        else:
            warnings.append(
                "单实体ER图要求只匹配一个目标表，但提示匹配到零个或多个表。请在标题、用途或描述中明确写出唯一目标表名。"
            )
    else:
        target_table_name = ""
        warnings.append("单实体ER图要求只匹配一个目标表，但提示匹配到多个表。请在标题、用途或描述中明确写出唯一目标表名。")

    if not target_table_name:
        return "", None, warnings
    return target_table_name, tables[target_table_name], warnings


def _field_display_name(field_name: str, table: ErTable, field_language: str = "english") -> str:
    if field_language == "chinese":
        display_name = table.field_display_names.get(field_name, "")
        if display_name:
            return display_name
    return field_name


def _dedup_display_names(table: ErTable, field_language: str) -> dict[str, str]:
    name_map: dict[str, str] = {}
    seen: dict[str, int] = {}
    for field_name in table.fields:
        display = _field_display_name(field_name, table, field_language)
        count = seen.get(display, 0)
        seen[display] = count + 1
        name_map[field_name] = display if count == 0 else f"{display}{count + 1}"
    return name_map


def build_single_entity_er_dot(
    background_text: str, title: str = "", focus_hint: str = "", field_language: str = "english"
) -> tuple[str, list[str]]:
    target_table_name, er_table, warnings = extract_single_entity_er_context(background_text, focus_hint)

    if not target_table_name or er_table is None:
        return "\n".join([
            "graph ER {",
            "  graph [layout=neato, bgcolor=white];",
            '  node [fontname="Microsoft YaHei", shape=box];',
            '  "ER图" [shape=box, style=rounded];',
            "}",
        ]) + "\n", warnings

    table = er_table
    table_id = _dot_id(target_table_name)
    edge_len = _field_edge_len(len(table.fields))
    display_names = _dedup_display_names(table, field_language)

    lines = [
        'graph ER {',
        '  graph [layout=neato, overlap=scale, splines=false, bgcolor=white, margin=0, pad=0, nodesep=0.3, sep="+5"];',
        '  node [fontname="Microsoft YaHei", color=black, fontsize=10, margin="0.08,0.04"];',
        '  edge [fontname="Microsoft YaHei", color=black, fontsize=9];',
        "",
        f'  {table_id} [shape=rectangle, pos="0,0!"];',
    ]

    for field_name in table.fields:
        display_name = display_names[field_name]
        field_id = _dot_id(display_name)
        lines.append(f'  {field_id} [shape=ellipse];')

    lines.append("")
    for field_name in table.fields:
        display_name = display_names[field_name]
        lines.append(f'  {table_id} -- {_dot_id(display_name)} [len={edge_len}];')

    lines.append("}")
    return "\n".join(lines) + "\n", warnings
