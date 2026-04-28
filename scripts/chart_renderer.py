# -*- coding: utf-8 -*-
"""
图表渲染工具 - 将 Mermaid、DOT、PlantUML 代码渲染为 PNG 图片

功能：
1. 解析 Markdown 中的 Mermaid、DOT、PlantUML 代码块
2. 自动渲染为 PNG 图片
3. 支持多种渲染方式：
   - Graphviz + Python graphviz（DOT）
   - Mermaid CLI（推荐）
   - Playwright + Mermaid（备选）
   - 在线 API（fallback）
4. 图片保存到本地目录

依赖安装：
    DOT 渲染：
        pip install graphviz
        并安装 Graphviz 可执行程序（dot）

    Mermaid 渲染：
        npm install -g @mermaid-js/mermaid-cli
        或
        pip install playwright && playwright install chromium

使用方法：
    python chart_renderer.py --input workspace/final/ER图_erd烟测.md --output workspace/final/images/ --method auto
    python chart_renderer.py --input workspace/final/ER图_dot测试_由易到难.md --output workspace/final/images/ --method auto --update --report
"""

import os
import re
import json
import base64
import zlib
import subprocess
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote
import hashlib

# 导入日志模块
try:
    from logger import get_logger, init_logger
except ImportError:
    # 如果直接运行，使用简单日志
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger():
        """get_logger"""
        return logging.getLogger()
    def init_logger():
        """init_logger"""
        return get_logger()


MAX_MERMAID_HEIGHT_PX = 800
GRAPHVIZ_BIN_CANDIDATES = [
    Path(r"D:/Program Files (x86)/Graphviz/bin"),
    Path(r"C:/Program Files/Graphviz/bin"),
    Path(r"C:/Program Files (x86)/Graphviz/bin"),
]


class ChartRenderer:
    """图表渲染器"""

    # Mermaid 代码块正则
    MERMAID_PATTERN = re.compile(
        r'```mermaid\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # DOT 代码块正则
    DOT_PATTERN = re.compile(
        r'```dot\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # PlantUML 代码块正则
    PLANTUML_PATTERN = re.compile(
        r'```plantuml\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # 图表编号正则
    CHART_ID_PATTERN = re.compile(r'%%\s*(图\d+-\d+(?:-\d+)?)')
    DOT_CHART_ID_PATTERN = re.compile(r'//\s*(图\d+-\d+(?:-\d+)?)')

    def __init__(self, output_dir: str = "workspace/final/images"):
        """__init__"""
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: List[Dict] = []
        self.rendered_count = 0
        self.failed_count = 0

    def parse_mermaid_blocks(self, content: str) -> List[Dict]:
        """
        解析 Markdown 中的 Mermaid 代码块

        Args:
            content: Markdown 内容

        Returns:
            图表信息列表
        """
        charts = []

        for match in self.MERMAID_PATTERN.finditer(content):
            code = match.group(1).strip()

            # 提取图表编号
            chart_id_match = self.CHART_ID_PATTERN.search(code)
            chart_id = chart_id_match.group(1) if chart_id_match else f"chart_{len(charts) + 1}"

            # 提取图表标题
            lines = code.split('\n')
            title = ""
            for line in lines:
                if line.strip().startswith('%%'):
                    title = line.strip().lstrip('%').strip()
                    break

            charts.append({
                'id': chart_id,
                'type': 'mermaid',
                'code': code,
                'title': title,
                'start': match.start(),
                'end': match.end()
            })

        self.charts = charts
        self.logger.info(f"解析到 {len(charts)} 个 Mermaid 图表")

        return charts

    def parse_dot_blocks(self, content: str) -> List[Dict]:
        """
        解析 Markdown 中的 DOT 代码块

        Args:
            content: Markdown 内容

        Returns:
            图表信息列表
        """
        charts = []

        for match in self.DOT_PATTERN.finditer(content):
            code = match.group(1).strip()

            chart_id_match = self.DOT_CHART_ID_PATTERN.search(code)
            chart_id = chart_id_match.group(1) if chart_id_match else f"dot_{len(charts) + 1}"

            lines = code.split('\n')
            title = ""
            for line in lines:
                if line.strip().startswith('//'):
                    title = line.strip().lstrip('/').strip()
                    break

            charts.append({
                'id': chart_id,
                'type': 'dot',
                'code': code,
                'title': title,
                'start': match.start(),
                'end': match.end()
            })

        self.charts.extend(charts)
        self.logger.info(f"解析到 {len(charts)} 个 DOT 图表")

        return charts

    def parse_plantuml_blocks(self, content: str) -> List[Dict]:
        """
        解析 Markdown 中的 PlantUML 代码块

        Args:
            content: Markdown 内容

        Returns:
            图表信息列表
        """
        charts = []

        for match in self.PLANTUML_PATTERN.finditer(content):
            code = match.group(1).strip()

            chart_id = f"plantuml_{len(charts) + 1}"

            charts.append({
                'id': chart_id,
                'type': 'plantuml',
                'code': code,
                'title': '',
                'start': match.start(),
                'end': match.end()
            })

        # 合并到已有图表列表
        self.charts.extend(charts)
        self.logger.info(f"解析到 {len(charts)} 个 PlantUML 图表")

        return charts

    def render_with_mmdc(self, chart: Dict) -> Optional[Path]:
        """
        使用 mermaid-cli (mmdc) 渲染 Mermaid 图表

        Args:
            chart: 图表信息

        Returns:
            输出文件路径，失败返回 None
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False, encoding='utf-8') as f:
            f.write(chart['code'])
            temp_input = f.name

        # 生成输出文件名
        safe_id = re.sub(r'[^\w\-]', '_', chart['id'])
        output_file = self.output_dir / f"{safe_id}.png"

        try:
            # 调用 mmdc
            result = subprocess.run(
                ['mmdc', '-i', temp_input, '-o', str(output_file), '-b', 'white', '-H', str(MAX_MERMAID_HEIGHT_PX)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and output_file.exists():
                self.logger.info(f"渲染成功: {chart['id']} -> {output_file.name}")
                self.rendered_count += 1
                return output_file
            else:
                self.logger.error(f"渲染失败: {chart['id']}: {result.stderr}")
                self.failed_count += 1
                return None

        except FileNotFoundError:
            self.logger.warning("mmdc 未安装，请运行: npm install -g @mermaid-js/mermaid-cli")
            return None
        except subprocess.TimeoutExpired:
            self.logger.warning(f"渲染超时: {chart['id']}")
            self.failed_count += 1
            return None
        finally:
            # 清理临时文件
            os.unlink(temp_input)

    def render_with_playwright(self, chart: Dict) -> Optional[Path]:
        """
        使用 Playwright 渲染 Mermaid 图表

        Args:
            chart: 图表信息

        Returns:
            输出文件路径，失败返回 None
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.logger.warning("playwright 未安装，请运行: pip install playwright && playwright install")
            return None

        safe_id = re.sub(r'[^\w\-]', '_', chart['id'])
        output_file = self.output_dir / f"{safe_id}.png"

        # HTML 模板
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{ margin: 0; padding: 20px; background: white; }}
        .mermaid {{ display: flex; justify-content: center; }}
    </style>
</head>
<body>
    <div class="mermaid">
{code}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_template.format(code=chart['code']))
            temp_html = f.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f'file://{temp_html}')

                # 等待渲染完成
                page.wait_for_selector('.mermaid svg', timeout=30000)

                # 截图
                svg_element = page.query_selector('.mermaid')
                svg_element.screenshot(path=str(output_file))

                browser.close()

            self.logger.info(f"渲染成功: {chart['id']} -> {output_file.name}")
            self.rendered_count += 1
            return output_file

        except Exception as e:
            self.logger.error(f"渲染失败: {chart['id']}: {e}")
            self.failed_count += 1
            return None
        finally:
            os.unlink(temp_html)

    def render_with_kroki(self, chart: Dict) -> Optional[Path]:
        """
        使用 Kroki API 渲染图表（在线服务，需要网络）

        Args:
            chart: 图表信息

        Returns:
            输出文件路径，失败返回 None
        """
        import urllib.request
        import urllib.error

        safe_id = re.sub(r'[^\w\-]', '_', chart['id'])
        output_file = self.output_dir / f"{safe_id}.png"

        try:
            # Kroki API
            encoded = base64.urlsafe_b64encode(
                zlib.compress(chart['code'].encode('utf-8'), 9)
            ).decode('ascii')

            url = f"https://kroki.io/mermaid/png/{encoded}"

            req = urllib.request.Request(url, headers={'User-Agent': 'thesis-creator/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                # 检查响应状态码
                if response.status != 200:
                    self.logger.error(f"Kroki 返回非 200 状态: {response.status}")
                    self.failed_count += 1
                    return None
                data = response.read()

            # 验证返回数据非空
            if not data:
                self.logger.error(f"Kroki 返回空数据: {chart['id']}")
                self.failed_count += 1
                return None

            with open(output_file, 'wb') as f:
                f.write(data)

            self.logger.info(f"渲染成功: {chart['id']} -> {output_file.name} (Kroki)")
            self.rendered_count += 1
            return output_file

        except urllib.error.HTTPError as e:
            self.logger.error(f"Kroki HTTP 错误: {chart['id']} - 状态码 {e.code}: {e.reason}")
            self.failed_count += 1
            return None
        except urllib.error.URLError as e:
            self.logger.error(f"Kroki 网络错误: {chart['id']} - {e.reason}")
            self.failed_count += 1
            return None
        except TimeoutError:
            self.logger.warning(f"Kroki 请求超时: {chart['id']}")
            self.failed_count += 1
            return None
        except Exception as e:
            self.logger.error(f"Kroki 渲染失败: {chart['id']}: {e}")
            self.failed_count += 1
            return None

    def _ensure_graphviz_on_path(self) -> None:
        current_path = os.environ.get("PATH", "")
        segments = current_path.split(os.pathsep) if current_path else []

        for candidate in GRAPHVIZ_BIN_CANDIDATES:
            if not candidate.exists():
                continue
            candidate_str = str(candidate)
            if candidate_str not in segments:
                os.environ["PATH"] = candidate_str + os.pathsep + current_path if current_path else candidate_str
            return

    def render_with_graphviz(self, chart: Dict) -> Optional[Path]:
        """
        使用 Python graphviz 渲染 DOT 图表

        Args:
            chart: 图表信息

        Returns:
            输出文件路径，失败返回 None
        """
        safe_id = re.sub(r'[^\w\-]', '_', chart['id'])
        output_file = self.output_dir / f"{safe_id}.png"

        try:
            from graphviz import Source
        except ImportError:
            self.logger.warning("graphviz 未安装，请运行: pip install graphviz")
            return None

        try:
            self._ensure_graphviz_on_path()
            source = Source(chart['code'], format='png')
            rendered_path = Path(source.render(filename=safe_id, directory=str(self.output_dir), cleanup=True))
            if rendered_path.exists():
                self.logger.info(f"渲染成功: {chart['id']} -> {rendered_path.name}")
                self.rendered_count += 1
                return rendered_path
            self.logger.error(f"渲染失败: {chart['id']}: 未生成输出文件")
            self.failed_count += 1
            return None
        except Exception as e:
            self.logger.error(f"Graphviz 渲染失败: {chart['id']}: {e}")
            self.failed_count += 1
            return None

    def render_chart(self, chart: Dict, method: str = 'auto') -> Optional[Path]:
        """
        渲染单个图表

        Args:
            chart: 图表信息
            method: 渲染方法 ('mmdc', 'playwright', 'kroki', 'auto')

        Returns:
            输出文件路径
        """
        if chart['type'] == 'dot':
            return self.render_with_graphviz(chart)

        if chart['type'] != 'mermaid':
            self.logger.warning(f"跳过: {chart['id']}: 仅支持 Mermaid/DOT 图表")
            return None

        if method == 'mmdc':
            return self.render_with_mmdc(chart)
        elif method == 'playwright':
            return self.render_with_playwright(chart)
        elif method == 'kroki':
            return self.render_with_kroki(chart)
        else:  # auto
            # 按优先级尝试不同方法
            result = self.render_with_mmdc(chart)
            if result:
                return result

            result = self.render_with_playwright(chart)
            if result:
                return result

            return self.render_with_kroki(chart)

    def render_all(self, content: str, method: str = 'auto') -> Dict[str, Path]:
        """
        渲染所有图表

        Args:
            content: Markdown 内容
            method: 渲染方法

        Returns:
            {图表ID: 输出路径} 字典
        """
        # 解析图表
        self.charts = []
        self.parse_mermaid_blocks(content)
        self.parse_dot_blocks(content)
        self.parse_plantuml_blocks(content)

        if not self.charts:
            self.logger.info("没有找到可渲染的图表")
            return {}

        self.logger.info(f"开始渲染 {len(self.charts)} 个图表...")

        results = {}
        for i, chart in enumerate(self.charts, 1):
            self.logger.info(f"[{i}/{len(self.charts)}] 渲染 {chart['id']}...")
            output_path = self.render_chart(chart, method)
            if output_path:
                results[chart['id']] = output_path

        return results

    def generate_report(self) -> str:
        """生成渲染报告"""
        report = f"""# 图表渲染报告

> 渲染时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 统计

- 总图表数: {len(self.charts)}
- 渲染成功: {self.rendered_count}
- 渲染失败: {self.failed_count}

## 渲染结果

| 图表ID | 状态 | 输出文件 |
|--------|------|----------|
"""

        for chart in self.charts:
            safe_id = re.sub(r'[^\w\-]', '_', chart['id'])
            output_file = f"{safe_id}.png"
            output_path = self.output_dir / output_file

            if not output_path.exists():
                status = "[FAIL]"
                file_label = "-"
            else:
                file_size = output_path.stat().st_size
                if output_path.suffix.lower() == '.png' and file_size <= 1024:
                    status = "[WARN]"
                    file_label = f"{output_file} (<=1KB)"
                else:
                    status = "[OK]"
                    file_label = output_file

            report += f"| {chart['id']} | {status} | {file_label} |\n"

        return report

    def update_markdown(self, content: str, results: Dict[str, Path], markdown_dir: Path) -> str:
        """
        更新 Markdown，将代码块替换为图片引用

        Args:
            content: 原始内容
            results: 渲染结果
            markdown_dir: Markdown 文件所在目录

        Returns:
            更新后的内容
        """
        updated = content

        for chart_id, output_path in results.items():
            # 查找对应的图表代码块
            for chart in self.charts:
                if chart['id'] == chart_id:
                    # 构建图片引用（相对 markdown 文件目录）
                    relative_path = Path(os.path.relpath(output_path, start=markdown_dir)).as_posix()
                    img_ref = f"\n![{chart_id}]({relative_path})\n"

                    # 替换代码块为图片引用
                    old_block = content[chart['start']:chart['end']]
                    updated = updated.replace(old_block, img_ref)
                    break

        return updated


def main():
    """main"""
    parser = argparse.ArgumentParser(description="图表渲染工具")
    parser.add_argument("--input", "-i", required=True, help="输入 Markdown 文件")
    parser.add_argument("--output", "-o", default="workspace/final/images", help="输出目录（默认 workspace/final/images/）")
    parser.add_argument("--method", "-m", default="auto",
                        choices=['auto', 'mmdc', 'playwright', 'kroki'],
                        help="渲染方法")
    parser.add_argument("--report", action="store_true", help="生成渲染报告")
    parser.add_argument("--update", action="store_true", help="更新 Markdown 文件（原位覆盖）")

    args = parser.parse_args()

    # 读取输入文件
    logger = get_logger()
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"文件不存在: {args.input}")
        return

    content = input_path.read_text(encoding='utf-8')

    # 创建渲染器
    renderer = ChartRenderer(output_dir=args.output)

    # 渲染所有图表
    results = renderer.render_all(content, method=args.method)

    # 生成报告
    if args.report:
        report = renderer.generate_report()
        report_path = Path(args.output) / "render_report.md"
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"报告已生成: {report_path}")

    # 更新 Markdown
    if args.update and results:
        updated_content = renderer.update_markdown(content, results, input_path.parent)
        input_path.write_text(updated_content, encoding='utf-8')
        logger.info(f"Markdown 已更新（原位覆盖）: {input_path}")

    logger.info(f"完成: 成功渲染 {renderer.rendered_count}/{len(renderer.charts)} 个图表")


if __name__ == "__main__":
    # 初始化日志（自动检测 thesis-workspace/logs 目录）
    init_logger(session_name="chart_renderer")
    main()
