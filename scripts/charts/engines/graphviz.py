# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from pathlib import Path

GRAPHVIZ_BIN_CANDIDATES = [
    Path(r"D:/Program Files (x86)/Graphviz/bin"),
    Path(r"C:/Program Files/Graphviz/bin"),
    Path(r"C:/Program Files (x86)/Graphviz/bin"),
]

GRAPHVIZ_LAYOUT_ENGINES = {"dot", "neato", "fdp", "sfdp", "twopi", "circo", "osage", "patchwork"}


def _ensure_graphviz_on_path() -> None:
    current_path = os.environ.get("PATH", "")
    segments = current_path.split(os.pathsep) if current_path else []
    for candidate in GRAPHVIZ_BIN_CANDIDATES:
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        if candidate_str not in segments:
            os.environ["PATH"] = candidate_str + os.pathsep + current_path if current_path else candidate_str
        return


def _normalize_engine(engine: str) -> str:
    engine = engine.lower()
    return engine if engine in GRAPHVIZ_LAYOUT_ENGINES else "dot"


def _detect_layout_engine(code: str) -> str:
    for line in code.splitlines():
        stripped = line.strip()
        graph_attrs = re.match(r"^graph\s*\[(.*)\]", stripped)
        bare_attrs = re.match(r"^\[(.*)\]", stripped)
        attrs = graph_attrs.group(1) if graph_attrs else bare_attrs.group(1) if bare_attrs else ""
        if attrs:
            match = re.search(r"(?:^|,)\s*layout\s*=\s*\"?([A-Za-z0-9_]+)\"?\s*(?:,|$)", attrs)
            if match:
                return _normalize_engine(match.group(1))
        match = re.match(r"^layout\s*=\s*\"?([A-Za-z0-9_]+)\"?\s*;?$", stripped)
        if match:
            return _normalize_engine(match.group(1))
    return "dot"


def render(source: Path, output: Path) -> None:
    try:
        from graphviz import Source
    except ImportError as exc:
        raise RuntimeError("graphviz 未安装，请运行: pip install graphviz") from exc

    _ensure_graphviz_on_path()
    code = source.read_text(encoding="utf-8")
    engine = _detect_layout_engine(code)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = Path(Source(code, format="png", engine=engine).render(filename=output.stem, directory=str(output.parent), cleanup=True))
    if rendered != output and rendered.exists():
        rendered.replace(output)
    if not output.exists():
        raise RuntimeError("Graphviz 未生成输出文件")
