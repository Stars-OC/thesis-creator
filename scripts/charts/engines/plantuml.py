# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import subprocess
import zlib
from pathlib import Path
import sys
import urllib.request

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from core.terminal_encoding import subprocess_text_kwargs

try:
    from . import graphviz as graphviz_engine
except ImportError:
    import graphviz as graphviz_engine


# ============================================================
# 语法规范化：多 else 链 → switch/case / elseif
# ============================================================

def _normalize_else_chain(code: str) -> str:
    """将 PlantUML 活动图中不兼容的多 else 链转为 switch/case 或 elseif。
    Kroki 不支持连续 else(label) 语法。仅在顶层检测不含嵌套 if 的 else 链。
    """
    lines = code.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if_match = re.match(r"^if\s*\((.+?)\)\s*then\s*\((.+?)\)", line)
        if if_match:
            depth = 0
            else_positions: list[int] = []
            endif_pos = -1
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if re.match(r"^if\b", l):
                    depth += 1
                elif l == "endif":
                    if depth == 0:
                        endif_pos = j
                        break
                    depth -= 1
                elif depth == 0 and re.match(r"^else(?:\s*\(.+?\))?\s*$", l):
                    else_positions.append(j)
                j += 1
            if len(else_positions) >= 2 and endif_pos > 0:
                has_nested_if = False
                for k in range(i + 1, endif_pos):
                    if re.match(r"^if\b", lines[k].strip()):
                        has_nested_if = True
                        break
                if not has_nested_if:
                    condition = if_match.group(1)
                    branches = [if_match.group(2)]
                    for ep in else_positions:
                        m = re.match(r"^else(?:\s*\((.+?)\))?\s*$", lines[ep].strip())
                        branches.append(m.group(1) if m and m.group(1) else "")
                    splits = [i + 1] + [ep + 1 for ep in else_positions] + [endif_pos]
                    ends = else_positions + [endif_pos]
                    actions: list[list[str]] = []
                    for b in range(len(splits) - 1):
                        actions.append(lines[splits[b]:ends[b]])
                    is_switch = condition.endswith("?") and not any(
                        op in condition for op in ["成功", "有效", "匹配", "超限", "通过"]
                    )
                    if is_switch:
                        result.append(f"switch ({condition})")
                        for k, branch in enumerate(branches):
                            result.append(f"case ( {branch} )")
                            result.extend(actions[k])
                        result.append("endswitch")
                    else:
                        for k, branch in enumerate(branches):
                            prefix = "if" if k == 0 else "elseif"
                            result.append(f"{prefix} ({condition}) then ({branch})")
                            result.extend(actions[k])
                        result.append("endif")
                    i = endif_pos + 1
                    continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def _prepare_code(source: Path) -> str:
    """读取源文件并做语法规范化，所有渲染器共用此结果。"""
    return _normalize_else_chain(source.read_text(encoding="utf-8"))


# ============================================================
# PlantUML 原生编码（官方服务器和 Kroki 共用）
# ============================================================

def _plantuml_server_encode(text: str) -> str:
    """PlantUML 标准编码：raw deflate → 自定义 base64。"""
    data = zlib.compress(text.encode("utf-8"))[2:-4]
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    result = []

    for i in range(0, len(data), 3):
        chunk = data[i:i + 3]
        b1 = chunk[0]
        b2 = chunk[1] if len(chunk) > 1 else 0
        b3 = chunk[2] if len(chunk) > 2 else 0
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        result.append(alphabet[c1 & 0x3F])
        result.append(alphabet[c2 & 0x3F])
        if len(chunk) > 1:
            result.append(alphabet[c3 & 0x3F])
        if len(chunk) > 2:
            result.append(alphabet[c4 & 0x3F])

    return "".join(result)


# ============================================================
# 渲染器：本地 CLI
# ============================================================

def _render_local(code: str, output: Path) -> None:
    temp = output.with_suffix(".puml.tmp")
    temp.write_text(code, encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["plantuml", "-tpng", str(temp), "-o", str(output.parent.resolve())],
            capture_output=True,
            timeout=60,
            **subprocess_text_kwargs(),
        )
        generated = temp.with_suffix(".png")
        if generated.exists() and generated != output:
            generated.replace(output)
        if result.returncode != 0 or not output.exists():
            raise RuntimeError(result.stderr or "PlantUML 未生成输出文件")
    finally:
        temp.unlink(missing_ok=True)
        temp.with_suffix(".png").unlink(missing_ok=True)


# ============================================================
# 渲染器：Kroki（PlantUML 原生编码 + Huffman ~1 前缀）
# ============================================================

def _render_kroki(code: str, output: Path) -> None:
    encoded = _plantuml_server_encode(code)
    # Kroki 要求 Huffman 编码数据加 ~1 前缀
    raw_deflate = zlib.compress(code.encode("utf-8"))[2:-4]
    if len(code.encode("utf-8")) <= len(raw_deflate):
        encoded = "~1" + encoded
    url = f"https://kroki.io/plantuml/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-creator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Kroki 返回空数据")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


# ============================================================
# 渲染器：PlantUML 官方服务器（PlantUML 原生编码，无 Huffman 前缀）
# ============================================================

def _render_official_server(code: str, output: Path) -> None:
    encoded = _plantuml_server_encode(code)
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-creator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("PlantUML 官方服务器返回空数据")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


# ============================================================
# Graphviz 降级渲染器：将 PlantUML 语法转为 DOT
# ============================================================

def _strip_markup(text: str) -> str:
    return re.sub(r"<[^>]+>|<<[^>]+>>", "", text).strip()


def _quote_dot(text: str) -> str:
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def _actor_html_label(text: str) -> str:
    safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
        '<TR><TD>○</TD></TR>'
        '<TR><TD>╱│╲</TD></TR>'
        '<TR><TD>╱ ╲</TD></TR>'
        f'<TR><TD>{safe}</TD></TR>'
        '</TABLE>>'
    )


def _activity_to_dot(code: str) -> str:
    """将 PlantUML 活动图转为 DOT，支持 if/else/elseif/switch/case。"""
    nodes = []
    edges = []
    stack = []
    last = None
    counter = 0
    end_node = None

    def add_node(label: str, shape: str = "box") -> str:
        nonlocal counter
        node_id = f"n{counter}"
        counter += 1
        nodes.append((node_id, _strip_markup(label), shape))
        return node_id

    def get_end_node() -> str:
        nonlocal end_node
        if not end_node:
            end_node = add_node("结束", "oval")
        return end_node

    def append_edge(start: str, end: str, label: str = "") -> None:
        edges.append((start, end, _strip_markup(label)))

    def branch_label(default: str) -> str:
        if not stack:
            return ""
        context = stack[-1]
        label = context["next_label"] or default
        context["next_label"] = ""
        return label

    def register_branch_tail() -> None:
        if stack and last and last != stack[-1]["decision"]:
            stack[-1]["tails"].append(last)

    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("'") or line.startswith("@") or line.startswith("skinparam"):
            continue
        if line == "start":
            node = add_node("开始", "oval")
            if last:
                append_edge(last, node)
            last = node
            continue
        if line == "stop":
            node = get_end_node()
            if last and last != node:
                append_edge(last, node)
            last = node
            continue
        if line.startswith(":") and line.endswith(";"):
            node = add_node(line[1:-1])
            if last:
                append_edge(last, node, branch_label("Y"))
            last = node
            continue
        # if / elseif → 判断菱形
        match = re.match(r"(?:if|elseif)\s*\((.*?)\)\s*then\s*\((.*?)\)", line)
        if match:
            node = add_node(match.group(1), "diamond")
            if last:
                append_edge(last, node)
            stack.append({"decision": node, "tails": [], "next_label": match.group(2) or "Y"})
            last = node
            continue
        # switch → 判断菱形
        match = re.match(r"switch\s*\((.*?)\)", line)
        if match:
            node = add_node(match.group(1), "diamond")
            if last:
                append_edge(last, node)
            stack.append({"decision": node, "tails": [], "next_label": "", "is_switch": True})
            last = node
            continue
        # case → 分支标签
        match = re.match(r"case\s*\(\s*(.*?)\s*\)", line)
        if match and stack:
            stack[-1]["next_label"] = match.group(1)
            last = stack[-1]["decision"]
            continue
        # else（单分支，未规范化场景的兜底）
        match = re.match(r"else(?:\s*\((.*?)\))?", line)
        if match and stack:
            register_branch_tail()
            stack[-1]["next_label"] = match.group(1) or "N"
            last = stack[-1]["decision"]
            continue
        if line == "endif" and stack:
            register_branch_tail()
            context = stack.pop()
            merge = add_node("汇合", "point")
            for tail in context["tails"] or [context["decision"]]:
                append_edge(tail, merge)
            last = merge
            continue
        if line == "endswitch" and stack:
            register_branch_tail()
            context = stack.pop()
            merge = add_node("汇合", "point")
            for tail in context["tails"] or [context["decision"]]:
                append_edge(tail, merge)
            last = merge
            continue

    if last and last != end_node:
        append_edge(last, get_end_node())

    dot_lines = [
        "digraph PlantUMLFallback {",
        "  graph [rankdir=TB, bgcolor=\"white\", nodesep=0.45, ranksep=0.55];",
        "  node [fontname=\"Microsoft YaHei\", fontsize=11, style=\"rounded,filled\", fillcolor=\"#F8FBFF\", color=\"#2F5D8C\"];",
        "  edge [fontname=\"Microsoft YaHei\", fontsize=10, color=\"#555555\"];",
    ]
    for node_id, label, shape in nodes:
        dot_lines.append(f"  {node_id} [label={_quote_dot(label)}, shape={shape}];")
    for start, end, label in edges:
        suffix = f" [label={_quote_dot(label)}]" if label else ""
        dot_lines.append(f"  {start} -> {end}{suffix};")
    dot_lines.append("}")
    return "\n".join(dot_lines)


def _usecase_to_dot(code: str) -> str:
    actors = {}
    usecases = {}
    edges = []
    in_system = False

    for raw_line in code.splitlines():
        line = raw_line.strip()
        actor_match = re.match(r'actor\s+"([^"]+)"\s+as\s+(\w+)', line)
        if actor_match:
            actors[actor_match.group(2)] = actor_match.group(1)
            continue
        usecase_match = re.match(r'usecase\s+"([^"]+)"\s+as\s+(\w+)', line)
        if usecase_match:
            usecases[usecase_match.group(2)] = usecase_match.group(1)
            continue
        edge_match = re.match(r'(\w+)\s+[-.]+>\s+(\w+)(?:\s*:\s*(.*))?', line)
        if edge_match:
            edges.append(edge_match.groups())
            continue
        if line.startswith('rectangle'):
            in_system = True
        elif in_system and line == '}':
            in_system = False

    dot_lines = [
        "digraph PlantUMLFallback {",
        "  graph [rankdir=LR, bgcolor=\"white\", nodesep=0.6, ranksep=0.9];",
        "  node [fontname=\"Microsoft YaHei\", fontsize=11, color=\"#2F5D8C\"];",
        "  edge [fontname=\"Microsoft YaHei\", fontsize=10, color=\"#555555\"];",
    ]
    for alias, label in actors.items():
        dot_lines.append(
            f"  {alias} [label={_actor_html_label(label)}, shape=none, margin=0, color=\"#2F5D8C\"];")
    for alias, label in usecases.items():
        dot_lines.append(f"  {alias} [label={_quote_dot(label)}, shape=ellipse, style=filled, fillcolor=\"#F8FBFF\"];")
    for start, end, label in edges:
        suffix = f" [label={_quote_dot(_strip_markup(label))}]" if label else ""
        dot_lines.append(f"  {start} -> {end}{suffix};")
    dot_lines.append("}")
    return "\n".join(dot_lines)


def _render_graphviz_fallback(code: str, output: Path) -> None:
    """将规范化后的 PlantUML 代码转为 DOT 再渲染。"""
    if "usecase" in code or "actor" in code:
        dot = _usecase_to_dot(code)
    else:
        dot = _activity_to_dot(code)
    fallback_source = output.with_suffix(".plantuml-fallback.dot")
    fallback_source.write_text(dot, encoding="utf-8")
    graphviz_engine.render(fallback_source, output)
    fallback_source.unlink(missing_ok=True)


# ============================================================
# 渲染入口：统一规范化 → 降级链路
# ============================================================

def render(source: Path, output: Path, method: str = "auto", allow_fallback: bool = False) -> None:
    # 所有渲染器共用同一份规范化代码，确保降级时语法一致
    code = _prepare_code(source)

    if method == "plantuml":
        _render_local(code, output)
        return
    if method == "official_server":
        _render_official_server(code, output)
        return

    if method == "kroki":
        # Kroki → 官方服务器，两者都失败则直接报错
        kroki_err = None
        try:
            _render_kroki(code, output)
            return
        except Exception as exc:
            kroki_err = exc

        try:
            _render_official_server(code, output)
            return
        except Exception as official_err:
            raise RuntimeError(
                f"PlantUML 渲染失败：Kroki({kroki_err}) → 官方服务器({official_err})，"
                f"请检查源码语法或网络连接"
            ) from official_err

    if method == "graphviz":
        if allow_fallback:
            _render_graphviz_fallback(code, output)
            return
        raise RuntimeError("PlantUML 图禁止使用 graphviz 渲染方法")

    # auto: 本地 → Kroki → 官方服务器 → Graphviz
    auto_chain = [_render_local, _render_kroki, _render_official_server]
    if allow_fallback:
        auto_chain.append(_render_graphviz_fallback)

    errors = []
    for renderer in auto_chain:
        try:
            renderer(code, output)
            return
        except Exception as exc:
            errors.append(f"{renderer.__name__}: {exc}")
    raise RuntimeError("; ".join(errors))