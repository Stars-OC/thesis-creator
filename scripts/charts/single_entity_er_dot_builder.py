# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ErTable:
    name: str
    fields: List[str] = field(default_factory=list)
    field_comments: dict[str, str] = field(default_factory=dict)


FIELD_CN_MAP: dict[str, str] = {
    "user_id": "用户编号",
    "username": "用户名",
    "password": "密码",
    "email": "邮箱",
    "phone": "手机号",
    "avatar_url": "头像地址",
    "role_id": "角色编号",
    "status": "状态",
    "last_login_at": "最后登录时间",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "role_name": "角色名称",
    "role_code": "角色编码",
    "permissions": "权限",
    "description": "描述",
    "is_default": "是否默认",
    "sort_order": "排序",
    "kb_id": "知识库编号",
    "name": "名称",
    "owner_id": "拥有者编号",
    "embedding_model": "嵌入模型",
    "chunk_size": "分块大小",
    "chunk_overlap": "分块重叠",
    "doc_id": "文档编号",
    "uploader_id": "上传者编号",
    "filename": "文件名",
    "file_type": "文件类型",
    "file_size": "文件大小",
    "storage_path": "存储路径",
    "parse_status": "解析状态",
    "segment_count": "分段数量",
    "error_message": "错误信息",
    "segment_id": "分段编号",
    "seq_index": "序号",
    "content": "内容",
    "char_count": "字符数",
    "word_count": "词数",
    "vector_db_id": "向量库编号",
    "vector_id": "向量编号",
    "dimension": "维度",
    "model_name": "模型名称",
    "index_status": "索引状态",
    "conversation_id": "会话编号",
    "message_id": "消息编号",
    "key_id": "密钥编号",
    "config_id": "配置编号",
    "node_id": "节点编号",
    "node_type": "节点类型",
    "node_name": "节点名称",
    "source_text": "源文本",
    "conversation_title": "会话标题",
    "user_message": "用户消息",
    "assistant_message": "助手消息",
    "token_count": "令牌数",
    "model": "模型",
    "api_key": "API密钥",
    "api_endpoint": "API端点",
    "action": "操作",
    "target": "目标",
    "ip_address": "IP地址",
    "user_agent": "用户代理",
    "config_key": "配置键",
    "config_value": "配置值",
}


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
                continue
            if in_field_table and current_table and cells:
                field_name = _clean_cell(cells[0])
                skip_names = {"字段名", "类型", "长度", "允许空", "主键", "说明", "备注"}
                if field_name and field_name not in skip_names:
                    table = tables.setdefault(current_table, ErTable(current_table))
                    if field_name not in table.fields:
                        table.fields.append(field_name)
                    if len(cells) >= 2:
                        comment = _clean_cell(cells[-1])
                        if comment and comment not in skip_names:
                            table.field_comments[field_name] = comment
                    continue

        _parse_markdown_table_line(line, tables)
        _parse_text_table_line(line, tables)

    return tables


def _field_display_name(field_name: str, table: ErTable) -> str:
    return field_name


def _focus_table_from_hint(focus_hint: str, tables: dict[str, ErTable]) -> str | None:
    normalized_hint = _normalize_match_text(focus_hint)
    if not normalized_hint:
        return None

    matched = []
    for table_name in tables:
        if any(alias and alias in normalized_hint for alias in _table_aliases(table_name)):
            matched.append(table_name)

    if len(matched) == 1:
        return matched[0]
    return None


def _ring_positions(count: int, radius: float = 1.8) -> list[tuple[float, float]]:
    if count == 0:
        return []

    if count <= 4:
        positions = [(0.0, radius), (radius, 0.0), (0.0, -radius), (-radius, 0.0)]
        return positions[:count]

    inner_count = min(count, 8)
    result = []
    for i in range(inner_count):
        angle = 2 * math.pi * i / inner_count - math.pi / 2
        x = round(radius * math.cos(angle), 2)
        y = round(radius * math.sin(angle), 2)
        result.append((x, y))

    if count > inner_count:
        outer_count = count - inner_count
        outer_radius = radius + 0.45
        for i in range(outer_count):
            angle = 2 * math.pi * i / outer_count - math.pi / 2 + math.pi / outer_count
            x = round(outer_radius * math.cos(angle), 2)
            y = round(outer_radius * math.sin(angle), 2)
            result.append((x, y))

    return result[:count]


def extract_single_entity_er_context(
    background_text: str, focus_hint: str = ""
) -> tuple[str, list[str], list[str]]:
    tables = _parse_tables(background_text)
    warnings = []

    target_table_name = _focus_table_from_hint(focus_hint, tables)
    if not target_table_name:
        if not tables:
            warnings.append("未从 background.md 识别到明确的数据表定义。")
        elif len(tables) == 1:
            target_table_name = next(iter(tables))
        else:
            warnings.append(
                "单实体ER图要求只匹配一个目标表，但提示匹配到零个或多个表。请在标题、用途或描述中明确写出唯一目标表名。"
            )

    if not target_table_name:
        return "", [], warnings
    return target_table_name, tables[target_table_name].fields, warnings


def build_single_entity_er_dot(
    background_text: str, title: str = "", focus_hint: str = ""
) -> tuple[str, list[str]]:
    target_table_name, fields, warnings = extract_single_entity_er_context(background_text, focus_hint)

    if not target_table_name:
        return "\n".join([
            "graph ER {",
            "  graph [layout=neato, bgcolor=white];",
            '  node [fontname="Microsoft YaHei", shape=box];',
            '  "ER图" [shape=box, style=rounded];',
            "}",
        ]) + "\n", warnings

    table = ErTable(target_table_name, fields)
    table_id = _dot_id(target_table_name)
    positions = _ring_positions(len(table.fields))

    lines = [
        'graph ER {',
        '  graph [layout=neato, overlap=true, splines=true, bgcolor=white, margin=0, pad=0, nodesep=0.15, sep=0.08];',
        '  node [fontname="Microsoft YaHei", color=black, fontsize=10, margin="0.04,0.02"];',
        '  edge [fontname="Microsoft YaHei", color=black, fontsize=9];',
        "",
        f'  {table_id} [shape=rectangle, pos="0,0!"];',
    ]

    for i, field_name in enumerate(table.fields):
        display_name = _field_display_name(field_name, table)
        field_id = _dot_id(display_name)
        x, y = positions[i] if i < len(positions) else (i, 0)
        lines.append(f'  {field_id} [shape=ellipse, pos="{x},{y}!"];')

    lines.append("")
    for field_name in table.fields:
        display_name = _field_display_name(field_name, table)
        lines.append(f'  {table_id} -- {_dot_id(display_name)};')

    lines.append("}")
    return "\n".join(lines) + "\n", warnings
