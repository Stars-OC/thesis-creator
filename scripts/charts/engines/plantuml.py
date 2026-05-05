# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import subprocess
import zlib
from pathlib import Path
import urllib.request


def _render_local(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["plantuml", "-tpng", str(source), "-o", str(output.parent.resolve())],
        capture_output=True,
        text=True,
        timeout=60,
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


def render(source: Path, output: Path, method: str = "auto") -> None:
    if method == "plantuml":
        _render_local(source, output)
        return
    if method == "kroki":
        _render_kroki(source, output)
        return

    errors = []
    for renderer in (_render_local, _render_kroki):
        try:
            renderer(source, output)
            return
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("; ".join(errors))
