# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

GRAPHVIZ_BIN_CANDIDATES = [
    Path(r"D:/Program Files (x86)/Graphviz/bin"),
    Path(r"C:/Program Files/Graphviz/bin"),
    Path(r"C:/Program Files (x86)/Graphviz/bin"),
    Path(r"D:/Program Files/Graphviz/bin"),
]

GRAPHVIZ_LAYOUT_ENGINES = {"dot", "neato", "fdp", "sfdp", "twopi", "circo", "osage", "patchwork"}


def _ensure_graphviz_on_path() -> str | None:
    """确保 Graphviz bin 目录加入 PATH，返回找到的 dot 可执行文件路径（若有）。"""
    current_path = os.environ.get("PATH", "")
    segments = current_path.split(os.pathsep) if current_path else []

    existing = shutil.which("dot")
    if existing:
        return existing

    for candidate in GRAPHVIZ_BIN_CANDIDATES:
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        if candidate_str not in segments:
            os.environ["PATH"] = candidate_str + os.pathsep + current_path if current_path else candidate_str
        dot_path = candidate / ("dot.exe" if os.name == "nt" else "dot")
        if dot_path.exists():
            return str(dot_path)
        return None
    return None


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


def _render_via_subprocess(dot_executable: str, code: str, engine: str, output: Path) -> None:
    """直接调用 dot 可执行文件，使用列表形式传参，安全处理含空格路径。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    # 使用绝对路径并以列表传参，subprocess 会正确处理含空格路径
    engine_bin = Path(dot_executable).parent / (f"{engine}.exe" if os.name == "nt" else engine)
    executable = str(engine_bin) if engine_bin.exists() else dot_executable
    cmd = [executable, "-Tpng", "-o", str(output.resolve())]
    try:
        result = subprocess.run(
            cmd,
            input=code.encode("utf-8"),
            capture_output=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Graphviz 可执行文件不存在: {executable}") from exc

    if result.returncode != 0 or not output.exists():
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        raise RuntimeError(f"Graphviz 渲染失败: {stderr or '未生成输出文件'}")


def render(source: Path, output: Path) -> None:
    code = source.read_text(encoding="utf-8")
    engine = _detect_layout_engine(code)
    dot_executable = _ensure_graphviz_on_path()

    # 优先使用 subprocess 直接调用，避免 graphviz Python 库对含空格路径的处理 bug
    if dot_executable:
        try:
            _render_via_subprocess(dot_executable, code, engine, output)
            return
        except Exception:
            # 失败时回退到 graphviz Python 库
            pass

    try:
        from graphviz import Source
    except ImportError as exc:
        raise RuntimeError("graphviz 未安装，请运行: pip install graphviz") from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = Path(
        Source(code, format="png", engine=engine).render(
            filename=str(output.with_suffix("")),
            directory=str(output.parent),
            cleanup=True,
        )
    )
    if rendered != output and rendered.exists():
        rendered.replace(output)
    if not output.exists():
        raise RuntimeError("Graphviz 未生成输出文件")

