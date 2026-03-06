# -*- coding: utf-8 -*-
"""
图表生成器 - 从论文占位符生成 Mermaid/PlantUML 代码

功能：
1. 解析论文中的图表占位符
2. 根据占位符描述生成对应的图表代码
3. 支持架构图、流程图、E-R图、用例图、时序图
4. 输出 Mermaid 格式（可直接在 Markdown 中渲染）

使用方法：
    python chart_generator.py input.md --output charts/
"""

import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

# 导入日志模块
try:
    from logger import get_logger, init_logger
except ImportError:
    # 如果直接运行，使用简单日志
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger():
        return logging.getLogger()
    def init_logger():
        return get_logger()


class ChartPlaceholder:
    """图表占位符数据结构"""

    def __init__(self, raw_text: str, chart_type: str, chart_id: str, chart_name: str, description: str):
        self.raw_text = raw_text
        self.chart_type = chart_type
        self.chart_id = chart_id
        self.chart_name = chart_name
        self.description = description

    def __repr__(self):
        return f"ChartPlaceholder({self.chart_id}, {self.chart_type})"


class ChartGenerator:
    """图表生成器"""

    # 占位符正则表达式
    PLACEHOLDER_PATTERN = re.compile(
        r'<!--\s*图表占位符[：:]\s*(图\d+-\d+)\s+(.+?)\s*-->\s*'
        r'>\s*📊\s*\*\*\[图表占位符\]\*\*\s*'
        r'(.*?)'
        r'<!--\s*图表占位符结束\s*-->',
        re.DOTALL
    )

    # 简化版占位符正则（用于更灵活的格式）
    SIMPLE_PATTERN = re.compile(
        r'\[图表占位符\][：:]?\s*(\w+图)?[，,]?\s*展示(.+?)(?:\n|$)'
    )

    def __init__(self, output_dir: str = "charts"):
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: List[ChartPlaceholder] = []

    def parse_placeholders(self, content: str) -> List[ChartPlaceholder]:
        """
        解析文档中的图表占位符

        Args:
            content: 文档内容

        Returns:
            占位符列表
        """
        self.logger.info(f"开始解析图表占位符...")

        # 匹配完整格式的占位符
        matches = self.PLACEHOLDER_PATTERN.findall(content)

        for match in matches:
            chart_id = match[0]
            chart_name = match[1]
            details = match[2]

            # 解析图表类型
            chart_type = self._detect_chart_type(chart_name, details)

            placeholder = ChartPlaceholder(
                raw_text=match[0],
                chart_type=chart_type,
                chart_id=chart_id,
                chart_name=chart_name,
                description=details
            )
            self.charts.append(placeholder)
            self.logger.debug(f"发现占位符: {chart_id} - {chart_name} ({chart_type})")

        # 匹配简化格式的占位符
        simple_matches = self.SIMPLE_PATTERN.findall(content)
        for match in simple_matches:
            chart_type_hint = match[0] if match[0] else "流程图"
            description = match[1]

            chart_type = self._normalize_chart_type(chart_type_hint)

            placeholder = ChartPlaceholder(
                raw_text=f"简化占位符",
                chart_type=chart_type,
                chart_id=f"图X-X",
                chart_name=f"自动检测图表",
                description=description
            )
            self.charts.append(placeholder)
            self.logger.debug(f"发现简化占位符: {chart_type} - {description[:50]}...")

        self.logger.info(f"共发现 {len(self.charts)} 个图表占位符")
        return self.charts

    def _detect_chart_type(self, chart_name: str, description: str) -> str:
        """检测图表类型"""
        combined = f"{chart_name} {description}".lower()

        if "架构" in combined:
            return "架构图"
        elif "流程" in combined or "业务" in combined:
            return "流程图"
        elif "e-r" in combined or "实体" in combined or "关系" in combined:
            return "E-R图"
        elif "用例" in combined:
            return "用例图"
        elif "时序" in combined or "交互" in combined:
            return "时序图"
        elif "类图" in combined:
            return "类图"
        elif "截图" in combined:
            return "系统截图"
        else:
            return "流程图"  # 默认

    def _normalize_chart_type(self, type_hint: str) -> str:
        """规范化图表类型"""
        type_map = {
            "架构图": "架构图",
            "流程图": "流程图",
            "业务流程图": "流程图",
            "e-r图": "E-R图",
            "er图": "E-R图",
            "实体关系图": "E-R图",
            "用例图": "用例图",
            "时序图": "时序图",
            "类图": "类图",
        }
        return type_map.get(type_hint.lower(), "流程图")

    def generate_mermaid(self, placeholder: ChartPlaceholder) -> str:
        """
        为占位符生成 Mermaid 代码

        Args:
            placeholder: 图表占位符

        Returns:
            Mermaid 代码
        """
        self.logger.debug(f"生成 Mermaid: {placeholder.chart_id}")

        if placeholder.chart_type == "架构图":
            return self._generate_architecture_diagram(placeholder)
        elif placeholder.chart_type == "流程图":
            return self._generate_flowchart(placeholder)
        elif placeholder.chart_type == "E-R图":
            return self._generate_er_diagram(placeholder)
        elif placeholder.chart_type == "用例图":
            return self._generate_usecase_diagram(placeholder)
        elif placeholder.chart_type == "时序图":
            return self._generate_sequence_diagram(placeholder)
        elif placeholder.chart_type == "类图":
            return self._generate_class_diagram(placeholder)
        else:
            return self._generate_flowchart(placeholder)  # 默认流程图

    def _generate_architecture_diagram(self, placeholder: ChartPlaceholder) -> str:
        """生成架构图 Mermaid 代码"""
        # 从描述中提取层次信息
        desc = placeholder.description

        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph TB
    subgraph 表现层["表现层 (Presentation Layer)"]
        A1[Web前端]
        A2[移动端]
    end

    subgraph 接口层["接口层 (API Layer)"]
        B1[REST API]
        B2[认证授权]
    end

    subgraph 业务层["业务层 (Business Layer)"]
        C1[用户服务]
        C2[核心业务服务]
        C3[数据处理服务]
    end

    subgraph 数据层["数据层 (Data Layer)"]
        D1[(数据库)]
        D2[(缓存)]
        D3[(文件存储)]
    end

    A1 --> B1
    A2 --> B1
    B1 --> B2
    B2 --> C1
    B2 --> C2
    B2 --> C3
    C1 --> D1
    C2 --> D1
    C2 --> D2
    C3 --> D3
```'''

    def _generate_flowchart(self, placeholder: ChartPlaceholder) -> str:
        """生成流程图 Mermaid 代码"""
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
flowchart TD
    A([开始]) --> B[用户请求]
    B --> C{{
检查请求有效性
}}
    C -->|有效| D[处理业务逻辑]
    C -->|无效| E[返回错误信息]
    D --> F[数据持久化]
    F --> G[生成响应]
    G --> H([结束])
    E --> H
```'''

    def _generate_er_diagram(self, placeholder: ChartPlaceholder) -> str:
        """生成 E-R 图 Mermaid 代码"""
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
erDiagram
    USER ||--o{{ ORDER : places
    USER {{
        bigint id PK
        varchar username
        varchar password
        varchar email
        datetime created_at
    }}
    ORDER ||--|{{ ORDER_ITEM : contains
    ORDER {{
        bigint id PK
        bigint user_id FK
        decimal total_amount
        varchar status
        datetime created_at
    }}
    ORDER_ITEM }}|--|| PRODUCT : includes
    ORDER_ITEM {{
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        int quantity
        decimal price
    }}
    PRODUCT {{
        bigint id PK
        varchar name
        decimal price
        int stock
    }}
```'''

    def _generate_usecase_diagram(self, placeholder: ChartPlaceholder) -> str:
        """生成用例图 Mermaid 代码"""
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph LR
    subgraph 系统
        UC1((登录))
        UC2((查看数据))
        UC3((管理数据))
        UC4((导出报告))
    end

    User((用户)) --> UC1
    User --> UC2
    Admin((管理员)) --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC4
```'''

    def _generate_sequence_diagram(self, placeholder: ChartPlaceholder) -> str:
        """生成时序图 Mermaid 代码"""
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as API网关
    participant S as 业务服务
    participant D as 数据库

    U->>F: 发起请求
    F->>A: HTTP请求
    A->>A: 认证校验
    A->>S: 调用服务
    S->>D: 数据查询
    D-->>S: 返回数据
    S-->>A: 业务响应
    A-->>F: HTTP响应
    F-->>U: 展示结果
```'''

    def _generate_class_diagram(self, placeholder: ChartPlaceholder) -> str:
        """生成类图 Mermaid 代码"""
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
classDiagram
    class UserService {{
        +getUser(id) User
        +createUser(user) bool
        +updateUser(user) bool
        +deleteUser(id) bool
    }}
    class User {{
        -id: bigint
        -username: string
        -password: string
        +validate() bool
    }}
    class UserRepository {{
        +findById(id) User
        +save(user) bool
    }}
    UserService --> User : manages
    UserService --> UserRepository : uses
```'''

    def generate_all(self, content: str) -> Dict[str, str]:
        """
        为所有占位符生成图表代码

        Args:
            content: 文档内容

        Returns:
            {图表ID: Mermaid代码} 字典
        """
        self.parse_placeholders(content)

        results = {}
        for chart in self.charts:
            mermaid_code = self.generate_mermaid(chart)
            results[chart.chart_id] = mermaid_code
            self.logger.info(f"✅ 生成图表: {chart.chart_id} ({chart.chart_type})")

        return results

    def replace_placeholders(self, content: str, mermaid_codes: Dict[str, str]) -> str:
        """
        替换文档中的占位符为 Mermaid 代码

        Args:
            content: 原文档内容
            mermaid_codes: 图表代码字典

        Returns:
            替换后的文档
        """
        self.logger.info("开始替换占位符...")

        # 简单替换逻辑：在占位符后插入 Mermaid 代码
        for chart_id, code in mermaid_codes.items():
            # 在占位符结束标记后插入代码
            pattern = re.compile(
                rf'(<!--\s*图表占位符结束\s*-->)',
                re.DOTALL
            )

            def insert_code(match):
                return match.group(1) + "\n\n" + code + "\n"

            content = pattern.sub(insert_code, content, count=1)

        self.logger.info("占位符替换完成")
        return content

    def export_charts(self, mermaid_codes: Dict[str, str], format: str = "md") -> List[str]:
        """
        导出图表到文件

        Args:
            mermaid_codes: 图表代码字典
            format: 输出格式 (md, html, json)

        Returns:
            导出的文件路径列表
        """
        exported_files = []

        if format == "md":
            # 导出到单个 Markdown 文件
            output_file = self.output_dir / f"charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 论文图表 Mermaid 代码\n\n")
                f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                for chart_id, code in mermaid_codes.items():
                    f.write(f"## {chart_id}\n\n")
                    f.write(code)
                    f.write("\n\n---\n\n")

            exported_files.append(str(output_file))
            self.logger.file_operation("write", str(output_file))

        elif format == "json":
            # 导出为 JSON 格式
            output_file = self.output_dir / f"charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            chart_list = []
            for chart in self.charts:
                chart_list.append({
                    "id": chart.chart_id,
                    "name": chart.chart_name,
                    "type": chart.chart_type,
                    "description": chart.description,
                    "mermaid_code": mermaid_codes.get(chart.chart_id, "")
                })

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chart_list, f, ensure_ascii=False, indent=2)

            exported_files.append(str(output_file))
            self.logger.file_operation("write", str(output_file))

        elif format == "html":
            # 导出为可预览的 HTML
            output_file = self.output_dir / f"charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

            html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>论文图表预览</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body style="font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <h1>论文图表预览</h1>
    <p>生成时间: {timestamp}</p>
    <hr>
    {charts}
</body>
</html>'''

            charts_html = ""
            for chart_id, code in mermaid_codes.items():
                # 提取 mermaid 代码内容
                mermaid_content = code.replace("```mermaid", "").replace("```", "").strip()
                charts_html += f'''
    <h2>{chart_id}</h2>
    <div class="mermaid">
    {mermaid_content}
    </div>
    <hr>
'''

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_template.format(
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    charts=charts_html
                ))

            exported_files.append(str(output_file))
            self.logger.file_operation("write", str(output_file))

        return exported_files

    def generate_report(self) -> str:
        """生成图表占位符分析报告"""
        report_lines = [
            "# 图表占位符分析报告",
            "",
            f"> 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 统计信息",
            "",
            f"- 占位符总数: {len(self.charts)}",
            ""
        ]

        # 按类型统计
        type_counts = {}
        for chart in self.charts:
            type_counts[chart.chart_type] = type_counts.get(chart.chart_type, 0) + 1

        report_lines.append("### 类型分布")
        report_lines.append("")
        report_lines.append("| 图表类型 | 数量 |")
        report_lines.append("|----------|------|")
        for chart_type, count in type_counts.items():
            report_lines.append(f"| {chart_type} | {count} |")

        report_lines.append("")
        report_lines.append("## 占位符清单")
        report_lines.append("")

        for chart in self.charts:
            report_lines.append(f"### {chart.chart_id}: {chart.chart_name}")
            report_lines.append("")
            report_lines.append(f"- **类型**: {chart.chart_type}")
            report_lines.append(f"- **描述**: {chart.description[:100]}..." if len(chart.description) > 100 else f"- **描述**: {chart.description}")
            report_lines.append("")

        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="论文图表生成器")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", default="charts", help="输出目录")
    parser.add_argument("-f", "--format", default="md", choices=["md", "html", "json"], help="输出格式")
    parser.add_argument("--replace", action="store_true", help="直接替换原文档中的占位符")
    parser.add_argument("--report", action="store_true", help="生成分析报告")

    args = parser.parse_args()

    # 初始化日志
    init_logger(log_dir="logs", session_name="chart_generator")

    # 读取输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {args.input}")
        return

    content = input_path.read_text(encoding='utf-8')

    # 创建生成器
    generator = ChartGenerator(output_dir=args.output)

    # 生成图表
    mermaid_codes = generator.generate_all(content)

    # 导出图表
    exported_files = generator.export_charts(mermaid_codes, format=args.format)

    print(f"\n✅ 图表生成完成！")
    print(f"   共生成 {len(mermaid_codes)} 个图表")
    print(f"   输出目录: {args.output}")
    for f in exported_files:
        print(f"   - {f}")

    # 替换原文档
    if args.replace:
        new_content = generator.replace_placeholders(content, mermaid_codes)
        output_file = input_path.stem + "_with_charts" + input_path.suffix
        input_path.parent.joinpath(output_file).write_text(new_content, encoding='utf-8')
        print(f"\n📄 已生成带图表的文档: {output_file}")

    # 生成报告
    if args.report:
        report = generator.generate_report()
        report_file = Path(args.output) / "chart_report.md"
        report_file.write_text(report, encoding='utf-8')
        print(f"\n📊 分析报告: {report_file}")


if __name__ == "__main__":
    main()