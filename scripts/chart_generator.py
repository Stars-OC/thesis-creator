# -*- coding: utf-8 -*-
"""
图表生成器 - 从论文占位符生成 Mermaid 代码

功能：
1. 解析论文中的图表占位符
2. 根据占位符名称与关键词生成对应图表代码
3. 支持架构图、流程图、E-R图、用例图、时序图、功能模块图
4. 支持用户手动提供图片占位符识别
"""

import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

MAX_FLOWCHART_NODES = 10

FLOW_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
    "登录": [
        {"name": "输入账号密码", "type": "io"},
        {"name": "验证输入格式", "type": "decision", "yes_action": "通过", "no_action": "返回错误"},
        {"name": "查询用户信息", "type": "process"},
        {"name": "校验密码", "type": "decision", "yes_action": "正确", "no_action": "拒绝登录"},
        {"name": "生成Token", "type": "process"},
        {"name": "返回登录结果", "type": "process"},
    ],
    "注册": [
        {"name": "填写注册信息", "type": "io"},
        {"name": "校验字段完整性", "type": "decision", "yes_action": "通过", "no_action": "提示补全"},
        {"name": "检查账号唯一性", "type": "decision", "yes_action": "可用", "no_action": "提示重名"},
        {"name": "加密密码", "type": "process"},
        {"name": "保存用户数据", "type": "process"},
        {"name": "返回注册成功", "type": "process"},
    ],
    "订单": [
        {"name": "创建订单请求", "type": "io"},
        {"name": "校验库存", "type": "decision", "yes_action": "充足", "no_action": "缺货"},
        {"name": "锁定库存", "type": "process"},
        {"name": "生成订单记录", "type": "process"},
        {"name": "发起支付", "type": "decision", "yes_action": "成功", "no_action": "取消订单"},
        {"name": "更新订单状态", "type": "process"},
    ],
}

try:
    from logger import get_logger, init_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

    def get_logger():
        return logging.getLogger()

    def init_logger():
        return get_logger()


class ChartPlaceholder:
    def __init__(self, raw_text: str, chart_type: str, chart_id: str, chart_name: str, description: str):
        self.raw_text = raw_text
        self.chart_type = chart_type
        self.chart_id = chart_id
        self.chart_name = chart_name
        self.description = description


class ChartGenerator:
    PLACEHOLDER_PATTERN = re.compile(
        r'<!--\s*图表占位符[：:]\s*(图\d+-\d+)\s+(.+?)\s*-->\s*'
        r'>\s*(?:\[统计\]\s*|📊\s*)?\*\*\[图表占位符\]\*\*\s*'
        r'(.*?)'
        r'<!--\s*图表占位符结束\s*-->',
        re.DOTALL
    )

    SIMPLE_PATTERN = re.compile(r'\[图表占位符\][：:]?\s*(\w+图)?[，,]?\s*展示(.+?)(?:\n|$)')

    USER_PROVIDED_PATTERN = re.compile(r'<!--\s*用户提供图片[：:]\s*(图\d+-\d+)\s+(.+?)\s*-->')

    def __init__(self, output_dir: str = "workspace/final/images"):
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: List[ChartPlaceholder] = []
        self.user_provided: List[Dict[str, str]] = []
        self.context_text: str = ""

    def parse_user_provided(self, content: str) -> List[Dict[str, str]]:
        self.user_provided = []
        for match in self.USER_PROVIDED_PATTERN.finditer(content):
            self.user_provided.append({
                "chart_id": match.group(1),
                "chart_name": match.group(2),
                "type": "user_provided"
            })
        return self.user_provided

    def parse_placeholders(self, content: str) -> List[ChartPlaceholder]:
        self.charts = []
        self.logger.info("开始解析图表占位符...")

        matches = self.PLACEHOLDER_PATTERN.findall(content)
        for match in matches:
            chart_id, chart_name, details = match[0], match[1], match[2]
            chart_type = self._detect_chart_type(chart_name, details)
            self.charts.append(ChartPlaceholder(
                raw_text=match[0],
                chart_type=chart_type,
                chart_id=chart_id,
                chart_name=chart_name,
                description=details
            ))

        simple_matches = self.SIMPLE_PATTERN.findall(content)
        for match in simple_matches:
            chart_type_hint = match[0] if match[0] else "流程图"
            description = match[1]
            chart_type = self._normalize_chart_type(chart_type_hint)
            self.charts.append(ChartPlaceholder(
                raw_text="简化占位符",
                chart_type=chart_type,
                chart_id="图X-X",
                chart_name="自动检测图表",
                description=description
            ))

        self.parse_user_provided(content)
        self.logger.info(f"共发现 {len(self.charts)} 个可自动生成图表，占位用户手填图 {len(self.user_provided)} 个")
        return self.charts

    def _detect_chart_type(self, chart_name: str, description: str) -> str:
        combined = f"{chart_name} {description}".lower()

        if "功能模块" in combined or "模块划分" in combined or "系统功能" in combined:
            return "功能模块图"
        if "架构" in combined:
            return "架构图"
        if "e-r" in combined or "er图" in combined or "实体" in combined:
            return "E-R图"
        if "用例" in combined:
            return "用例图"
        if "时序" in combined or "交互" in combined:
            return "时序图"
        if "类图" in combined:
            return "类图"
        if "流程" in combined or "业务" in combined:
            return "流程图"
        if "截图" in combined:
            return "系统截图"
        return "流程图"

    def _normalize_chart_type(self, type_hint: str) -> str:
        key = type_hint.lower()
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
            "功能模块图": "功能模块图",
            "模块图": "功能模块图",
        }
        return type_map.get(key, "流程图")

    def _template_steps(self, placeholder: ChartPlaceholder) -> List[Dict[str, str]]:
        text = f"{placeholder.chart_name} {placeholder.description} {self.context_text}"
        for key, steps in FLOW_TEMPLATES.items():
            if key in text:
                return [dict(s) for s in steps]
        return []

    def _build_single_flowchart(self, steps: List[Dict[str, str]], chart_id: str, chart_name: str) -> str:
        lines = [
            "```mermaid",
            f"%% {chart_id} {chart_name}",
            f"%% 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "flowchart TD",
            "    A([开始])",
        ]

        for i, step in enumerate(steps):
            node_id = chr(66 + i)
            step_name = step.get("name", f"步骤{i + 1}")
            step_type = step.get("type", "process")
            if step_type == "decision":
                lines.append(f"    {node_id}{{{{{step_name}}}}}")
            elif step_type == "io":
                lines.append(f"    {node_id}[/{step_name}/]")
            else:
                lines.append(f"    {node_id}[{step_name}]")

        lines.append("    Z([结束])")
        lines.append("    A --> B")

        for i, step in enumerate(steps):
            current_node = chr(66 + i)
            next_node = chr(67 + i) if i < len(steps) - 1 else "Z"
            if step.get("type") == "decision":
                yes_action = step.get("yes_action", "是")
                no_action = step.get("no_action", "否")
                lines.append(f"    {current_node} -->|{yes_action}| {next_node}")
                lines.append(f"    {current_node} -->|{no_action}| Z")
            else:
                lines.append(f"    {current_node} --> {next_node}")

        lines.append("```")
        return "\n".join(lines)

    def _split_flowchart(self, placeholder: ChartPlaceholder, steps: List[Dict[str, str]]) -> str:
        chunks = [steps[i:i + MAX_FLOWCHART_NODES] for i in range(0, len(steps), MAX_FLOWCHART_NODES)]
        blocks: List[str] = []
        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            part_id = f"{placeholder.chart_id}-{idx}"
            part_name = f"{placeholder.chart_name}（第{idx}/{total}段）"
            blocks.append(self._build_single_flowchart(chunk, part_id, part_name))
        return "\n\n".join(blocks)

    def generate_mermaid(self, placeholder: ChartPlaceholder) -> str:
        if placeholder.chart_type == "架构图":
            return self._generate_architecture_diagram(placeholder)
        if placeholder.chart_type == "流程图":
            return self._generate_flowchart(placeholder)
        if placeholder.chart_type == "E-R图":
            return self._generate_er_diagram(placeholder)
        if placeholder.chart_type == "用例图":
            return self._generate_usecase_diagram(placeholder)
        if placeholder.chart_type == "时序图":
            return self._generate_sequence_diagram(placeholder)
        if placeholder.chart_type == "类图":
            return self._generate_class_diagram(placeholder)
        if placeholder.chart_type == "功能模块图":
            return self._generate_module_diagram(placeholder)
        return self._generate_flowchart(placeholder)

    def _generate_architecture_diagram(self, placeholder: ChartPlaceholder) -> str:
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph TB
    subgraph 表现层["表现层"]
        A1[Web前端]
        A2[移动端]
    end

    subgraph 接口层["接口层"]
        B1[REST API]
        B2[认证授权]
    end

    subgraph 业务层["业务层"]
        C1[用户服务]
        C2[核心业务服务]
        C3[数据处理服务]
    end

    subgraph 数据层["数据层"]
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
        steps = self._template_steps(placeholder)
        if not steps:
            steps = self._extract_steps_from_description(placeholder.description)

        if not steps and self.context_text:
            steps = self._extract_steps_from_description(f"{placeholder.description}\n{self.context_text}")

        if not steps:
            steps = [
                {"name": "用户请求", "type": "process"},
                {"name": "校验参数", "type": "decision", "yes_action": "通过", "no_action": "返回错误"},
                {"name": "处理业务逻辑", "type": "process"},
                {"name": "保存数据", "type": "process"},
                {"name": "返回响应", "type": "process"},
            ]

        if len(steps) > MAX_FLOWCHART_NODES:
            self.logger.info(f"流程图 {placeholder.chart_id} 节点数 {len(steps)} 超过上限 {MAX_FLOWCHART_NODES}，自动拆分")
            return self._split_flowchart(placeholder, steps)

        return self._build_single_flowchart(steps, placeholder.chart_id, placeholder.chart_name)

    def _extract_steps_from_description(self, description: str) -> List[Dict[str, str]]:
        steps: List[Dict[str, str]] = []

        def clean_line(line: str) -> str:
            cleaned = re.sub(r'^\s*>+\s*', '', line)
            cleaned = re.sub(r'^\s*[-*•]\s*', '', cleaned)
            return cleaned.strip()

        def is_non_step_line(text: str) -> bool:
            if not text:
                return True
            if re.match(r'^\*{0,2}(图表编号|图表名称|图表类型|图表来源|来源|备注|说明)\*{0,2}[：:]', text):
                return True
            if re.match(r'^\*{0,2}(绘图要点|绘制要点|绘图说明|绘制说明)\*{0,2}[：:]', text):
                return True
            if re.search(r'(建议使用|使用.+表示|标注关键|颜色|线条|排版|字号|对齐|留白|美观)', text):
                return True
            return False

        normalized_lines = [clean_line(line) for line in description.splitlines()]
        normalized_lines = [line for line in normalized_lines if line]

        collecting = False
        candidate_lines: List[str] = []
        for line in normalized_lines:
            section_match = re.match(r'^\*{0,2}(内容描述|流程描述|流程步骤|处理流程|关键步骤|主要步骤|实现步骤)\*{0,2}[：:]\s*(.*)$', line)
            stop_match = re.match(r'^\*{0,2}(绘图要点|绘制要点|绘图说明|绘制说明)\*{0,2}[：:]\s*(.*)$', line)

            if stop_match:
                collecting = False
                continue

            if section_match:
                collecting = True
                first_line = section_match.group(2).strip()
                if first_line and not is_non_step_line(first_line):
                    candidate_lines.append(first_line)
                continue

            if collecting and not is_non_step_line(line):
                candidate_lines.append(line)

        if not candidate_lines:
            candidate_lines = [line for line in normalized_lines if not is_non_step_line(line)]

        numbered_line_pattern = re.compile(r'^\s*[（(]?\d+[）)、.．]\s*(.+)$')
        for line in candidate_lines:
            m = numbered_line_pattern.match(line)
            if not m:
                continue
            text = m.group(1).strip()
            if not text:
                continue
            step_type = "decision" if any(k in text for k in ["判断", "检查", "验证", "是否"]) else "process"
            steps.append({"name": text, "type": step_type})
        if steps:
            return steps

        candidate_desc = "\n".join(candidate_lines)
        numbered_pattern = r'[（(]?\d+[）)、.．]\s*(.+?)(?=[（(]?\d+[）)、.．]|$)'
        matches = re.findall(numbered_pattern, candidate_desc)
        if matches:
            for match in matches:
                text = match.strip()
                if text and not is_non_step_line(text):
                    step_type = "decision" if any(k in text for k in ["判断", "检查", "验证", "是否"]) else "process"
                    steps.append({"name": text, "type": step_type})
            return steps

        list_pattern = r'[-*•]\s*(.+?)(?=\n|$)'
        matches = re.findall(list_pattern, candidate_desc)
        if matches:
            for match in matches:
                text = match.strip()
                if text and len(text) > 2 and not is_non_step_line(text):
                    step_type = "decision" if any(k in text for k in ["判断", "检查", "验证", "是否"]) else "process"
                    steps.append({"name": text, "type": step_type})

        return steps

    def _generate_er_diagram(self, placeholder: ChartPlaceholder) -> str:
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
erDiagram
    USER {{
        string 用户名
        string 密码
        string 邮箱
        date 注册日期
    }}
    ORDER {{
        string 订单编号
        date 下单时间
        string 订单状态
        float 总金额
    }}
    PRODUCT {{
        string 商品名称
        float 商品价格
        int 库存数量
    }}
    PAYMENT {{
        string 支付单号
        string 支付方式
        string 支付状态
        date 支付时间
    }}

    USER ||--o{{ ORDER : 下单
    ORDER ||--|{{ PRODUCT : 包含
    ORDER ||--|| PAYMENT : 对应
```'''

    def _generate_module_diagram(self, placeholder: ChartPlaceholder) -> str:
        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph TB
    SYS[系统整体]

    SYS --> M1[用户管理模块]
    SYS --> M2[业务管理模块]
    SYS --> M3[数据分析模块]
    SYS --> M4[系统管理模块]

    M1 --> M11[注册登录]
    M1 --> M12[个人信息]

    M2 --> M21[业务录入]
    M2 --> M22[业务处理]

    M3 --> M31[统计报表]
    M3 --> M32[可视化展示]

    M4 --> M41[权限管理]
    M4 --> M42[日志管理]
```'''

    def _generate_usecase_diagram(self, placeholder: ChartPlaceholder) -> str:
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

    def generate_all(self, content: str, context: str = "") -> Dict[str, str]:
        self.context_text = context
        self.parse_placeholders(content)
        results: Dict[str, str] = {}
        for chart in self.charts:
            results[chart.chart_id] = self.generate_mermaid(chart)
            self.logger.info(f"[OK] 生成图表: {chart.chart_id} ({chart.chart_type})")
        return results

    def replace_placeholders(self, content: str, mermaid_codes: Dict[str, str]) -> str:
        self.logger.info("开始替换占位符（原位替代）...")

        for chart in self.charts:
            chart_id = chart.chart_id
            mermaid_code = mermaid_codes.get(chart_id)
            if not mermaid_code:
                continue

            block_pattern = re.compile(
                rf'<!--\s*图表占位符[：:]\s*{re.escape(chart_id)}\s+.*?-->\s*'
                rf'>\s*(?:\[统计\]\s*|📊\s*)?\*\*\[图表占位符\]\*\*\s*'
                rf'.*?'
                rf'<!--\s*图表占位符结束\s*-->',
                re.DOTALL
            )
            content = block_pattern.sub(mermaid_code, content)

        if "图X-X" in mermaid_codes:
            simple_pattern = re.compile(r'\[图表占位符\][：:]?\s*(\w+图)?[，,]?\s*展示(.+?)(?:\n|$)')
            content = simple_pattern.sub(mermaid_codes["图X-X"], content, count=1)

        self.logger.info("占位符替换完成（原位替代）")
        return content

    def generate_report(self) -> str:
        report_lines = [
            "# 图表占位符分析报告",
            "",
            f"> 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 统计信息",
            "",
            f"- 自动图表占位符总数: {len(self.charts)}",
            f"- 用户手填图片占位符总数: {len(self.user_provided)}",
            ""
        ]

        type_counts: Dict[str, int] = {}
        for chart in self.charts:
            type_counts[chart.chart_type] = type_counts.get(chart.chart_type, 0) + 1

        report_lines.append("### 自动图表类型分布")
        report_lines.append("")
        report_lines.append("| 图表类型 | 数量 |")
        report_lines.append("|----------|------|")
        for chart_type, count in type_counts.items():
            report_lines.append(f"| {chart_type} | {count} |")

        if self.user_provided:
            report_lines.append("")
            report_lines.append("### 用户手填图片清单")
            report_lines.append("")
            for item in self.user_provided:
                report_lines.append(f"- {item['chart_id']}：{item['chart_name']}")

        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="论文图表生成器")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", default="workspace/final/images", help="输出目录（默认 workspace/final/images/）")
    parser.add_argument("--replace", action="store_true", default=True, help="直接替换原文档中的占位符（原位覆盖，默认开启）")
    parser.add_argument("--no-replace", action="store_true", help="不替换原文档，仅生成分析报告")
    parser.add_argument("--context", help="上下文文件路径（可选，用于辅助提取流程步骤）")
    parser.add_argument("--report", action="store_true", help="生成分析报告")

    args = parser.parse_args()
    do_replace = not args.no_replace

    init_logger(session_name="chart_generator")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[FAIL] 文件不存在: {args.input}")
        return

    content = input_path.read_text(encoding='utf-8')
    context_text = ""
    if args.context:
        context_path = Path(args.context)
        if context_path.exists():
            context_text = context_path.read_text(encoding='utf-8')
        else:
            print(f"[WARN] 上下文文件不存在，忽略: {args.context}")

    generator = ChartGenerator(output_dir=args.output)
    mermaid_codes = generator.generate_all(content, context=context_text)

    print("\n[OK] 图表生成完成！")
    print(f"   共生成 {len(mermaid_codes)} 个图表")
    print(f"   输出目录: {args.output}")
    if generator.user_provided:
        print(f"   用户手填图片: {len(generator.user_provided)} 个")

    if do_replace and mermaid_codes:
        new_content = generator.replace_placeholders(content, mermaid_codes)
        input_path.write_text(new_content, encoding='utf-8')
        print(f"\n[文档] 已原位更新: {input_path}")

    if args.report:
        report = generator.generate_report()
        report_file = Path(args.output) / "chart_report.md"
        report_file.write_text(report, encoding='utf-8')
        print(f"\n[统计] 分析报告: {report_file}")


if __name__ == "__main__":
    main()
