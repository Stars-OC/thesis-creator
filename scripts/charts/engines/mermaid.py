# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import subprocess
import tempfile
import zlib
from pathlib import Path
import urllib.request

try:
    from ...terminal_encoding import subprocess_text_kwargs
except ImportError:
    from terminal_encoding import subprocess_text_kwargs

MAX_MERMAID_HEIGHT_PX = 800


def _render_with_mmdc(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["mmdc", "-i", str(source), "-o", str(output), "-b", "white", "-H", str(MAX_MERMAID_HEIGHT_PX)],
        capture_output=True,
        timeout=60,
        **subprocess_text_kwargs(),
    )
    if result.returncode != 0 or not output.exists():
        raise RuntimeError(result.stderr or "mmdc 未生成输出文件")


def _render_with_kroki(source: Path, output: Path) -> None:
    code = source.read_text(encoding="utf-8")
    encoded = base64.urlsafe_b64encode(zlib.compress(code.encode("utf-8"), 9)).decode("ascii")
    url = f"https://kroki.io/mermaid/png/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "thesis-creator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Kroki 返回空数据")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def _render_with_playwright(source: Path, output: Path) -> None:
    from playwright.sync_api import sync_playwright

    code = source.read_text(encoding="utf-8")
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>body {{ margin: 0; padding: 20px; background: white; }} .mermaid {{ display: flex; justify-content: center; }}</style>
</head>
<body>
    <div class="mermaid">{code}</div>
    <script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
</body>
</html>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as handle:
        handle.write(html)
        temp_html = Path(handle.name)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(temp_html.as_uri())
            page.wait_for_selector(".mermaid svg", timeout=30000)
            element = page.query_selector(".mermaid")
            element.screenshot(path=str(output))
            browser.close()
    finally:
        temp_html.unlink(missing_ok=True)


def render(source: Path, output: Path, method: str = "auto") -> None:
    if method == "mmdc":
        _render_with_mmdc(source, output)
        return
    if method == "playwright":
        _render_with_playwright(source, output)
        return
    if method == "kroki":
        _render_with_kroki(source, output)
        return

    errors = []
    for renderer in (_render_with_mmdc, _render_with_playwright, _render_with_kroki):
        try:
            renderer(source, output)
            return
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("; ".join(errors))
