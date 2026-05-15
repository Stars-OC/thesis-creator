# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
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


def _render_local(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["plantuml", "-tpng", str(source), "-o", str(output.parent.resolve())],
        capture_output=True,
        timeout=60,
        **subprocess_text_kwargs(),
    )
    generated = source.with_suffix(".png")
    if generated.exists() and generated != output:
        generated.replace(output)
    if result.returncode != 0 or not output.exists():
        raise RuntimeError(result.stderr or "PlantUML 未生成输出文件")


def _render_kroki(source: Path, output: Path) -> None:
    code = source.read_text(encoding="utf-8")
    encoded = base64.urlsafe_b64encode(zlib.compress(code.encode("utf-8"), 9)).decode("ascii")
    url = f"https://kroki.io/plantuml/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-creator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Kroki 返回空数据")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def _plantuml_server_encode(text: str) -> str:
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


def _render_official_server(source: Path, output: Path) -> None:
    code = source.read_text(encoding="utf-8")
    encoded = _plantuml_server_encode(code)
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-creator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("PlantUML 官方服务器返回空数据")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


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
        match = re.match(r"if\s*\((.*?)\)\s*then\s*\((.*?)\)", line)
        if match:
            node = add_node(match.group(1), "diamond")
            if last:
                append_edge(last, node)
            stack.append({"decision": node, "tails": [], "next_label": match.group(2) or "Y"})
            last = node
            continue
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


def _render_graphviz_fallback(source: Path, output: Path) -> None:
    code = source.read_text(encoding="utf-8")
    if "usecase" in code or "actor" in code:
        dot = _usecase_to_dot(code)
    else:
        dot = _activity_to_dot(code)
    fallback_source = output.with_suffix(".plantuml-fallback.dot")
    fallback_source.write_text(dot, encoding="utf-8")
    graphviz_engine.render(fallback_source, output)
    fallback_source.unlink(missing_ok=True)


def render(source: Path, output: Path, method: str = "auto", allow_fallback: bool = False) -> None:
    if method == "plantuml":
        _render_local(source, output)
        return
    if method == "official_server":
        _render_official_server(source, output)
        return
    if method == "kroki":
        errors = []
        for renderer in (_render_kroki, _render_official_server):
            try:
                renderer(source, output)
                return
            except Exception as exc:
                errors.append(str(exc))
        if allow_fallback:
            try:
                _render_graphviz_fallback(source, output)
                return
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError("; ".join(errors))
    if method == "graphviz":
        if allow_fallback:
            _render_graphviz_fallback(source, output)
            return
        raise RuntimeError("PlantUML 图禁止使用 graphviz 渲染方法")

    errors = []
    for renderer in (_render_local, _render_kroki, _render_official_server):
        try:
            renderer(source, output)
            return
        except Exception as exc:
            errors.append(str(exc))
    if allow_fallback:
        try:
            _render_graphviz_fallback(source, output)
            return
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("; ".join(errors))
