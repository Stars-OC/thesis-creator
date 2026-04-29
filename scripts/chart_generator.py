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
import argparse
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

try:
    from llm_chart_generator import HybridChartGenerator
except ImportError:
    HybridChartGenerator = None

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


@dataclass
class TableField:
    name: str
    data_type: str = ""
    length: str = ""
    nullable: str = ""
    is_primary: bool = False
    description: str = ""


@dataclass
class TableSchema:
    name: str
    display_name: str
    fields: List[TableField] = field(default_factory=list)
    related_tables: List[str] = field(default_factory=list)
    business_description: str = ""


def resolve_config_candidates(input_path: Optional[str] = None, explicit_config: Optional[str] = None) -> List[Path]:
    candidates: List[Path] = []
    seen = set()

    def add_candidate(path: Path):
        normalized = str(path.resolve()) if path.exists() else str(path)
        if normalized not in seen:
            seen.add(normalized)
            candidates.append(path)

    if explicit_config:
        add_candidate(Path(explicit_config))

    if input_path:
        input_file = Path(input_path)
        search_roots = [input_file.parent]
        search_roots.extend(input_file.parents)
        for root in search_roots:
            add_candidate(root / "thesis-workspace" / ".thesis-config.yaml")
            add_candidate(root / ".thesis-config.yaml")

    add_candidate(Path.cwd() / "thesis-workspace" / ".thesis-config.yaml")
    add_candidate(Path.cwd() / ".thesis-config.yaml")
    add_candidate(Path(__file__).resolve().parents[3] / "thesis-workspace" / ".thesis-config.yaml")
    return candidates


def _load_config_section(section_name: str, default: Dict[str, Any], config_path: Optional[str] = None, input_path: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Path]]:
    config = dict(default)
    for candidate in resolve_config_candidates(input_path=input_path, explicit_config=config_path):
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                section = data.get(section_name, {})
                if isinstance(section, dict):
                    config.update({k: v for k, v in section.items() if v is not None})
                    return config, candidate
        except Exception:
            continue
    return config, None


def _load_er_modeling_config(config_path: Optional[str] = None, input_path: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Path]]:
    default = {
        "enabled": True,
        "graph_type": "dot",
        "diagram_scope": "single",
        "strict_single_table": True,
        "line_style": "straight",
        "interactive_confirmation": False,
        "allow_optional_extensions": True,
    }
    return _load_config_section("er_modeling", default, config_path=config_path, input_path=input_path)


def _load_diagram_generation_config(config_path: Optional[str] = None, input_path: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Path]]:
    default = {
        "architecture_mode": "llm",
        "flowchart_direction": "AUTO",
    }
    return _load_config_section("diagram_generation", default, config_path=config_path, input_path=input_path)


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
    TABLE_SECTION_PATTERN = re.compile(r'^##\s+(?:数据库表设计|数据表清单)\s*$', re.MULTILINE)
    TABLE_HEADING_PATTERN = re.compile(r'^###\s+(.+?)(?:表结构|数据表)?\s*$', re.MULTILINE)

    def __init__(self, output_dir: str = "workspace/final/images", er_modeling_config: Optional[Dict[str, Any]] = None, diagram_generation_config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None, input_path: Optional[str] = None):
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: List[ChartPlaceholder] = []
        self.user_provided: List[Dict[str, str]] = []
        self.context_text: str = ""
        self.input_path = Path(input_path) if input_path else None
        loaded_config, resolved_config_path = _load_er_modeling_config(config_path, input_path=input_path)
        if er_modeling_config:
            loaded_config.update({k: v for k, v in er_modeling_config.items() if v is not None})
        self.er_modeling_config = loaded_config
        loaded_diagram_config, _ = _load_diagram_generation_config(config_path, input_path=input_path)
        if not diagram_generation_config and not config_path and not input_path:
            loaded_diagram_config["flowchart_direction"] = "AUTO"
        if diagram_generation_config:
            loaded_diagram_config.update({k: v for k, v in diagram_generation_config.items() if v is not None})
        self.diagram_generation_config = loaded_diagram_config
        self.resolved_config_path = resolved_config_path
        self.table_schemas: Dict[str, TableSchema] = {}
        self.background_path = self._resolve_background_path()
        self.last_er_context: Dict[str, Dict[str, Any]] = {}
        self._load_table_schemas()

    def _resolve_background_path(self) -> Optional[Path]:
        search_roots: List[Path] = []
        if self.input_path:
            search_roots.append(self.input_path.parent)
            search_roots.extend(self.input_path.parents)
        search_roots.append(Path.cwd())
        search_roots.append(Path(__file__).resolve().parents[3])

        seen = set()
        for root in search_roots:
            for candidate in [
                root / "thesis-workspace" / "references" / "prompt" / "background.md",
                root / "references" / "prompt" / "background.md",
            ]:
                normalized = str(candidate)
                if normalized in seen:
                    continue
                seen.add(normalized)
                if candidate.exists():
                    return candidate
        return None

    def _load_table_schemas(self):
        if self.background_path and self.background_path.exists():
            text = self.background_path.read_text(encoding="utf-8")
            self.table_schemas = self._parse_table_schemas_from_background(text)

    def _normalize_table_key(self, text: str) -> str:
        return re.sub(r'\s+', '', text).lower()

    def _parse_markdown_table(self, lines: List[str]) -> List[List[str]]:
        rows = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('|'):
                continue
            parts = [part.strip() for part in stripped.strip('|').split('|')]
            rows.append(parts)
        return rows

    def _parse_table_schemas_from_background(self, text: str) -> Dict[str, TableSchema]:
        schemas: Dict[str, TableSchema] = {}
        section_match = self.TABLE_SECTION_PATTERN.search(text)
        if not section_match:
            return schemas

        section_text = text[section_match.end():]
        headings = list(self.TABLE_HEADING_PATTERN.finditer(section_text))
        for idx, heading in enumerate(headings):
            start = heading.end()
            end = headings[idx + 1].start() if idx + 1 < len(headings) else len(section_text)
            block = section_text[start:end]
            table_name = heading.group(1).strip()
            related_tables = []
            relation_match = re.search(r'关联表[：:]\s*(.+)', block)
            if relation_match:
                related_tables = [item.strip() for item in re.split(r'[、,，]', relation_match.group(1)) if item.strip()]

            business_description = ""
            for pattern in [r'业务说明[：:]\s*(.+)', r'用途[：:]\s*(.+)', r'说明[：:]\s*(.+)']:
                business_match = re.search(pattern, block)
                if business_match:
                    candidate = business_match.group(1).strip()
                    if candidate and '|' not in candidate:
                        business_description = candidate
                        break

            table_lines = []
            for line in block.splitlines():
                if line.strip().startswith('|'):
                    table_lines.append(line)
            rows = self._parse_markdown_table(table_lines)
            if len(rows) < 2:
                continue

            header = rows[0]
            data_rows = rows[2:] if len(rows) >= 3 else rows[1:]
            name_idx = next((i for i, col in enumerate(header) if col in {"字段名", "字段", "名称"}), None)
            type_idx = next((i for i, col in enumerate(header) if col in {"类型", "数据类型"}), None)
            length_idx = next((i for i, col in enumerate(header) if col in {"长度", "长度/值域"}), None)
            nullable_idx = next((i for i, col in enumerate(header) if col in {"允许空", "可空"}), None)
            pk_idx = next((i for i, col in enumerate(header) if col in {"主键", "是否主键"}), None)
            desc_idx = next((i for i, col in enumerate(header) if col in {"说明", "字段说明"}), None)
            if name_idx is None:
                continue

            fields: List[TableField] = []
            for row in data_rows:
                if len(row) <= name_idx:
                    continue
                name = row[name_idx].strip()
                if not name or set(name) == {'-'}:
                    continue
                is_primary = False
                if pk_idx is not None and len(row) > pk_idx:
                    is_primary = row[pk_idx].strip() in {"是", "Y", "y", "√", "1", "true", "True"}
                fields.append(TableField(
                    name=name,
                    data_type=row[type_idx].strip() if type_idx is not None and len(row) > type_idx else "",
                    length=row[length_idx].strip() if length_idx is not None and len(row) > length_idx else "",
                    nullable=row[nullable_idx].strip() if nullable_idx is not None and len(row) > nullable_idx else "",
                    is_primary=is_primary,
                    description=row[desc_idx].strip() if desc_idx is not None and len(row) > desc_idx else "",
                ))

            schema = TableSchema(
                name=table_name,
                display_name=table_name,
                fields=fields,
                related_tables=related_tables,
                business_description=business_description,
            )
            schemas[self._normalize_table_key(table_name)] = schema
        return schemas

    def parse_user_provided(self, content: str) -> List[Dict[str, str]]:
        self.user_provided = []
        for match in self.USER_PROVIDED_PATTERN.finditer(content):
            self.user_provided.append({
                "chart_id": match.group(1),
                "chart_name": match.group(2),
                "type": "user_provided",
            })
        return self.user_provided

    def parse_placeholders(self, content: str) -> List[ChartPlaceholder]:
        self.charts = []
        self.logger.info("开始解析图表占位符...")

        matches = self.PLACEHOLDER_PATTERN.findall(content)
        for chart_id, chart_name, details in matches:
            chart_type = self._detect_chart_type(chart_name, details)
            self.charts.append(ChartPlaceholder(
                raw_text=chart_id,
                chart_type=chart_type,
                chart_id=chart_id,
                chart_name=chart_name,
                description=details,
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
                description=description,
            ))

        self.parse_user_provided(content)
        self.logger.info(f"共发现 {len(self.charts)} 个可自动生成图表，占位用户手填图 {len(self.user_provided)} 个")
        return self.charts

    def validate_image_integrity(self, content: str) -> Dict[str, Any]:
        remaining_placeholders = len(re.findall(r'<!--\s*图表占位符[：:]', content))
        image_refs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)

        missing_files = []
        small_files = []
        path_mismatches = []

        for image_ref in image_refs:
            normalized = image_ref.strip().replace('\\', '/')
            image_path = Path(normalized)

            if image_path.name != normalized and not normalized.startswith('images/'):
                path_mismatches.append(normalized)

            candidate = self.output_dir / image_path.name
            if not candidate.exists():
                missing_files.append(normalized)
                continue

            if candidate.suffix.lower() == '.png' and candidate.stat().st_size <= 1024:
                small_files.append(candidate.name)

        return {
            'remaining_placeholders': remaining_placeholders,
            'referenced_images': len(image_refs),
            'missing_files': len(missing_files),
            'small_files': len(small_files),
            'path_mismatches': len(path_mismatches),
            'missing_file_list': missing_files,
            'small_file_list': small_files,
            'path_mismatch_list': path_mismatches,
        }

    def _format_integrity_row(self, passed: bool, label: str, detail: str) -> str:
        status = '通过' if passed else '不通过'
        return f"| {label} | {status} | {detail} |"

    def _build_integrity_section(self, integrity: Dict[str, Any]) -> List[str]:
        return [
            '## 图片完整性验证',
            '',
            '| 检查项 | 结果 | 说明 |',
            '|--------|------|------|',
            self._format_integrity_row(integrity['remaining_placeholders'] == 0, '占位符全部替换', f"{integrity['remaining_placeholders']} 个残留"),
            self._format_integrity_row(integrity['missing_files'] == 0, '图片文件存在', f"{integrity['missing_files']} 个缺失"),
            self._format_integrity_row(integrity['small_files'] == 0, '图片非空', f"{integrity['small_files']} 个文件小于等于 1KB"),
            self._format_integrity_row(integrity['path_mismatches'] == 0, '图片引用一致', f"{integrity['path_mismatches']} 个路径不在 images/ 目录"),
            '',
        ]

    def _detect_chart_type(self, chart_name: str, description: str) -> str:
        combined = f"{chart_name} {description}".lower()

        if "功能模块" in combined or "模块划分" in combined or "系统功能" in combined:
            return "功能模块图"
        if "架构" in combined:
            return "架构图"
        if any(keyword in combined for keyword in ["概念er图", "概念 er 图", "概念 er图", "实体er图", "实体 er 图", "e-r", "er图", "实体关系"]):
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
            "概念er图": "E-R图",
            "概念 er 图": "E-R图",
            "实体er图": "E-R图",
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
                return [dict(step) for step in steps]
        return []

    def _build_single_flowchart(self, steps: List[Dict[str, str]], chart_id: str, chart_name: str) -> str:
        configured_direction = str(self.diagram_generation_config.get("flowchart_direction", "AUTO")).upper().strip()
        if configured_direction == "AUTO":
            chart_numbers = [int(value) for value in re.findall(r'\d+', chart_id)]
            seed = sum(chart_numbers) if chart_numbers else sum(ord(char) for char in chart_name)
            direction_cycle = ["LR", "RL", "TB", "BT"]
            direction = direction_cycle[seed % len(direction_cycle)]
        else:
            direction = configured_direction
        if direction not in {"LR", "RL", "TB", "BT"}:
            direction = "TB"
        lines = [
            "```mermaid",
            f"%% {chart_id} {chart_name}",
            f"%% 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"flowchart {direction}",
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
            match = numbered_line_pattern.match(line)
            if not match:
                continue
            text = match.group(1).strip()
            if not text:
                continue
            step_type = "decision" if any(keyword in text for keyword in ["判断", "检查", "验证", "是否"]) else "process"
            steps.append({"name": text, "type": step_type})
        if steps:
            return steps

        candidate_desc = "\n".join(candidate_lines)
        numbered_pattern = r'[（(]?\d+[）)、.．]\s*(.+?)(?=[（(]?\d+[）)、.．]|$)'
        for match in re.findall(numbered_pattern, candidate_desc):
            text = match.strip()
            if text and not is_non_step_line(text):
                step_type = "decision" if any(keyword in text for keyword in ["判断", "检查", "验证", "是否"]) else "process"
                steps.append({"name": text, "type": step_type})
        if steps:
            return steps

        list_pattern = r'[-*•]\s*(.+?)(?=\n|$)'
        for match in re.findall(list_pattern, candidate_desc):
            text = match.strip()
            if text and len(text) > 2 and not is_non_step_line(text):
                step_type = "decision" if any(keyword in text for keyword in ["判断", "检查", "验证", "是否"]) else "process"
                steps.append({"name": text, "type": step_type})

        return steps

    def _extract_er_core_entity(self, chart_name: str, description: str) -> str:
        name_match = re.search(r'([一-鿿A-Za-z0-9_]+?)概念\s*ER图', chart_name, re.IGNORECASE)
        chart_entity = name_match.group(1).strip() if name_match else ""

        entity_match = re.search(r'实体[：:]\s*([^；;\n]+)', description)
        if entity_match:
            entities = [item.strip() for item in re.split(r'[、,，]', entity_match.group(1)) if item.strip()]
            if chart_entity and chart_entity in entities:
                return chart_entity
            if entities:
                return entities[0]

        if chart_entity:
            return chart_entity

        return "核心实体"

    def _match_schema(self, entity_name: str) -> Optional[TableSchema]:
        key = self._normalize_table_key(entity_name)
        if key in self.table_schemas:
            return self.table_schemas[key]
        for schema_key, schema in self.table_schemas.items():
            if key in schema_key or schema_key in key:
                return schema
        return None

    def _schema_to_attribute_names(self, schema: TableSchema) -> List[str]:
        names = []
        for field in schema.fields:
            if field.description:
                names.append(field.description)
            elif field.is_primary:
                names.append("编号")
            elif field.name.upper().startswith("FK_"):
                names.append(field.name)
            else:
                names.append(field.name)
        return names or self._default_er_attributes(schema.display_name)

    def _build_er_warnings(self, schema: TableSchema, matched_from_background: bool) -> List[str]:
        warnings: List[str] = []
        if not matched_from_background:
            warnings.append("未能从 background.md 精确命中主实体，已使用描述信息兜底生成。")
            return warnings

        if not schema.business_description:
            warnings.append(f"{schema.display_name}缺少表级业务说明，图注将使用通用描述。")

        missing_field_descriptions = [field.name for field in schema.fields if not field.description]
        if missing_field_descriptions:
            preview = "、".join(missing_field_descriptions[:3])
            warnings.append(f"{schema.display_name}存在缺少字段说明的字段：{preview}。")

        english_like_fields = [field.name for field in schema.fields if not field.description and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', field.name)]
        if english_like_fields:
            preview = "、".join(english_like_fields[:3])
            warnings.append(f"{schema.display_name}存在仍需中文语义补充的英文字段：{preview}。")

        return warnings

    def _build_er_caption(self, schema: TableSchema, related_schemas: List[TableSchema], graph_type: str) -> str:
        role_text = schema.business_description.strip() if schema.business_description else f"用于说明{schema.display_name}表在业务流程中的核心职责。"

        primary_fields = [field.description or field.name for field in schema.fields[:3] if field.description or field.name]
        if primary_fields:
            field_text = f"图中重点展示了{schema.display_name}表的关键字段，包括{'、'.join(primary_fields)}，用于支撑该实体的主键标识、基础信息维护与状态管理。"
        else:
            field_text = f"图中重点展示了{schema.display_name}表的关键字段，用于支撑该实体的主键标识、基础信息维护与状态管理。"

        if related_schemas:
            related_text = f"同时该实体还与{'、'.join(item.display_name for item in related_schemas[:2])}等实体存在直接业务关联，用于支撑第4章数据库设计中的关系说明。"
        else:
            related_text = "同时该实体与其他业务实体的关联关系可在后续数据库设计章节中继续展开说明。"

        return f"{schema.display_name}表{role_text}{field_text}{related_text}"

    def _extract_er_entities(self, description: str, core_entity: str) -> List[str]:
        entities = [core_entity]
        for match in re.finditer(r'实体[：:]\s*([^；;\n]+)', description):
            for item in [part.strip() for part in re.split(r'[、,，]', match.group(1)) if part.strip()]:
                if item not in entities:
                    entities.append(item)
        return entities[:3]

    def _extract_er_attributes(self, description: str, entities: List[str]) -> Dict[str, List[str]]:
        attributes: Dict[str, List[str]] = {}
        for entity in entities:
            pattern = rf'{re.escape(entity)}属性[：:]\s*([^；;\n]+)'
            match = re.search(pattern, description)
            if match:
                attributes[entity] = [item.strip() for item in re.split(r'[、,，]', match.group(1)) if item.strip()]

        fk_match = re.search(r'外键[：:]\s*([^。；;\n]+)', description)
        if fk_match and entities:
            fk_fields = re.findall(r'FK_[A-Za-z0-9_]+', fk_match.group(1))
            if fk_fields:
                attributes.setdefault(entities[0], [])
                for field in fk_fields:
                    if field not in attributes[entities[0]]:
                        attributes[entities[0]].append(field)

        return attributes

    def _extract_er_relationship(self, description: str, entities: List[str]) -> Dict[str, str]:
        match = re.search(r'联系[：:]\s*([^\-\n；;]+)-([^\-\n；;]+)-([^（(\n；;]+)', description)
        if match:
            return {
                "left": match.group(1).strip(),
                "name": match.group(2).strip(),
                "right": match.group(3).strip(),
            }

        if len(entities) >= 2:
            return {"left": entities[0], "name": "关联", "right": entities[1]}

        fallback = entities[0] if entities else "核心实体"
        return {"left": fallback, "name": "关联", "right": fallback}

    def _default_er_attributes(self, entity: str) -> List[str]:
        return ["编号", "名称", "状态", "创建时间"]

    def _sanitize_er_field_name(self, field: str) -> str:
        cleaned = field.strip().strip('。；;,.')
        cleaned = re.sub(r'^(PK_|FK_)[A-Za-z0-9_]+$', '编号', cleaned)
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', cleaned):
            english_map = {
                'id': '编号',
                'name': '名称',
                'title': '标题',
                'type': '类型',
                'status': '状态',
                'created_at': '创建时间',
                'updated_at': '更新时间',
            }
            return english_map.get(cleaned.lower(), '字段')
        return cleaned or '字段'

    def _build_conceptual_er_default(self, chart_id: str, chart_name: str, core_entity: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
flowchart LR
    E1[{core_entity}]
    E2[关联实体]
    A1((编号))
    A2((名称))
    A3((状态))
    A4((创建时间))

    A1 --- E1
    A2 --- E1
    E2 --- A3
    E2 --- A4
    E1 ---|关联| E2
```'''

    def _build_conceptual_er_mermaid(
        self,
        chart_id: str,
        chart_name: str,
        entities: List[str],
        attributes: Dict[str, List[str]],
        relationship: Dict[str, str],
    ) -> str:
        lines = [
            "```mermaid",
            f"%% {chart_id} {chart_name}",
            "flowchart LR",
        ]

        entity_ids: Dict[str, str] = {}
        for idx, entity in enumerate(entities, start=1):
            entity_id = f"E{idx}"
            entity_ids[entity] = entity_id
            lines.append(f"    {entity_id}[{entity}]")

        attr_index = 1
        for entity in entities:
            entity_fields = [self._sanitize_er_field_name(raw) for raw in attributes.get(entity, [])]
            if not entity_fields:
                continue

            split_index = max(1, len(entity_fields) // 2)
            top_fields = entity_fields[:split_index]
            bottom_fields = entity_fields[split_index:]

            for field in top_fields:
                attr_id = f"A{attr_index}"
                lines.append(f"    {attr_id}(({field}))")
                lines.append(f"    {attr_id} --- {entity_ids[entity]}")
                attr_index += 1

            for field in bottom_fields:
                attr_id = f"A{attr_index}"
                lines.append(f"    {attr_id}(({field}))")
                lines.append(f"    {entity_ids[entity]} --- {attr_id}")
                attr_index += 1

        left = relationship.get("left", entities[0])
        right = relationship.get("right", entities[-1])
        relation_name = self._sanitize_er_field_name(relationship.get("name", "关联"))

        if left in entity_ids and right in entity_ids:
            lines.append(f"    {entity_ids[left]} ---|{relation_name}| {entity_ids[right]}")
        elif left in entity_ids:
            lines.append(f"    {entity_ids[left]} ---|{relation_name}| E1")

        lines.append("```")
        return "\n".join(lines)

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

    def _generate_with_hybrid(self, placeholder: ChartPlaceholder, warning_message: str) -> Optional[str]:
        if HybridChartGenerator is None:
            return None
        try:
            hybrid = HybridChartGenerator()
            generated = hybrid.generate(
                placeholder.chart_type,
                placeholder.description,
                self.context_text,
                placeholder.chart_id,
                placeholder.chart_name,
            )
            return generated or None
        except Exception as exc:
            self.logger.warning(f"{warning_message}: {exc}")
            return None

    def _generate_architecture_diagram(self, placeholder: ChartPlaceholder) -> str:
        architecture_mode = str(self.diagram_generation_config.get("architecture_mode", "llm")).lower().strip()
        if architecture_mode == "llm":
            generated = self._generate_with_hybrid(placeholder, "架构图模型生成失败，回退默认模板")
            if generated:
                return generated

        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph LR
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

    def _generate_er_diagram(self, placeholder: ChartPlaceholder) -> str:
        core_entity = self._extract_er_core_entity(placeholder.chart_name, placeholder.description)
        graph_type = str(self.er_modeling_config.get("graph_type", "chen")).lower().strip()
        diagram_scope = str(self.er_modeling_config.get("diagram_scope", "single")).lower().strip()

        schema = self._match_schema(core_entity)
        if schema:
            entities = [schema.display_name]
            attributes = {schema.display_name: self._schema_to_attribute_names(schema)}
            related_schemas = []
            for table_name in schema.related_tables[:2]:
                related_schema = self._match_schema(table_name)
                if related_schema:
                    related_schemas.append(related_schema)
                    if diagram_scope == "multi":
                        entities.append(related_schema.display_name)
                        attributes[related_schema.display_name] = self._schema_to_attribute_names(related_schema)[:4]
            relationship = {
                "left": schema.display_name,
                "name": "关联",
                "right": related_schemas[0].display_name if related_schemas else schema.display_name,
            }
            self.last_er_context[placeholder.chart_id] = {
                "schema": schema,
                "related_schemas": related_schemas,
                "graph_type": graph_type,
                "warnings": self._build_er_warnings(schema, matched_from_background=True),
            }
        else:
            entities = self._extract_er_entities(placeholder.description, core_entity)
            attributes = self._extract_er_attributes(placeholder.description, entities)
            relationship = self._extract_er_relationship(placeholder.description, entities)
            single_entity = entities[0] if entities else core_entity
            single_attributes = attributes.get(single_entity, self._default_er_attributes(single_entity))
            self.last_er_context[placeholder.chart_id] = {
                "warnings": self._build_er_warnings(
                    TableSchema(name=single_entity, display_name=single_entity, fields=[]),
                    matched_from_background=False,
                )
            }
            if graph_type in {"erd", "mermaid_erd", "mermaid-erd"}:
                if diagram_scope == "multi" and len(entities) > 1:
                    return self._build_mermaid_erd_multi(
                        placeholder.chart_id,
                        placeholder.chart_name,
                        entities,
                        attributes,
                        relationship,
                    )
                return self._build_mermaid_erd(
                    placeholder.chart_id,
                    placeholder.chart_name,
                    single_entity,
                    single_attributes,
                )

            if graph_type in {"dot", "graphviz", "graphviz_dot", "graphviz-dot"}:
                if diagram_scope == "multi" and len(entities) > 1:
                    return self._build_graphviz_dot_multi(
                        placeholder.chart_id,
                        placeholder.chart_name,
                        entities,
                        attributes,
                        relationship,
                    )
                return self._build_graphviz_dot(
                    placeholder.chart_id,
                    placeholder.chart_name,
                    single_entity,
                    single_attributes,
                )

            if diagram_scope == "multi" and len(entities) > 1:
                return self._build_conceptual_er_mermaid(
                    placeholder.chart_id,
                    placeholder.chart_name,
                    entities,
                    attributes,
                    relationship,
                )

            return self._build_conceptual_er_mermaid(
                placeholder.chart_id,
                placeholder.chart_name,
                [single_entity],
                {single_entity: single_attributes},
                {},
            )

        use_multi = diagram_scope == "multi" and len(entities) > 1
        if graph_type in {"erd", "mermaid_erd", "mermaid-erd"}:
            if use_multi:
                return self._build_mermaid_erd_multi(
                    placeholder.chart_id,
                    placeholder.chart_name,
                    entities,
                    attributes,
                    relationship,
                )
            return self._build_mermaid_erd(
                placeholder.chart_id,
                placeholder.chart_name,
                schema.display_name,
                attributes[schema.display_name],
            )

        if graph_type in {"dot", "graphviz", "graphviz_dot", "graphviz-dot"}:
            if use_multi:
                return self._build_graphviz_dot_multi(
                    placeholder.chart_id,
                    placeholder.chart_name,
                    entities,
                    attributes,
                    relationship,
                )
            return self._build_graphviz_dot(
                placeholder.chart_id,
                placeholder.chart_name,
                schema.display_name,
                attributes[schema.display_name],
            )

        return self._build_conceptual_er_mermaid(
            placeholder.chart_id,
            placeholder.chart_name,
            entities if use_multi else [schema.display_name],
            attributes if use_multi else {schema.display_name: attributes[schema.display_name]},
            relationship if use_multi else {},
        )

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

    def _build_mermaid_erd(self, chart_id: str, chart_name: str, entity: str, fields: List[str]) -> str:
        lines = [
            "```mermaid",
            f"%% {chart_id} {chart_name}",
            "erDiagram",
        ]
        lines.append(f"    {entity} {{")
        for idx, field in enumerate(fields):
            normalized = self._sanitize_er_field_name(field)
            if idx == 0:
                lines.append(f"        string {normalized} PK")
            else:
                lines.append(f"        string {normalized}")
        lines.append("    }")
        lines.append("```")
        return "\n".join(lines)

    def _build_mermaid_erd_multi(
        self,
        chart_id: str,
        chart_name: str,
        entities: List[str],
        attributes: Dict[str, List[str]],
        relationship: Dict[str, str],
    ) -> str:
        lines = [
            "```mermaid",
            f"%% {chart_id} {chart_name}",
            "erDiagram",
        ]
        for entity in entities:
            lines.append(f"    {entity} {{")
            entity_fields = attributes.get(entity, self._default_er_attributes(entity))
            for idx, field in enumerate(entity_fields):
                normalized = self._sanitize_er_field_name(field)
                if idx == 0:
                    lines.append(f"        string {normalized} PK")
                else:
                    lines.append(f"        string {normalized}")
            lines.append("    }")

        left = relationship.get("left", entities[0])
        right = relationship.get("right", entities[-1])
        relation_name = self._sanitize_er_field_name(relationship.get("name", "关联"))
        if left in entities and right in entities and left != right:
            lines.append(f"    {left} ||--o{{ {right} : {relation_name}")
        lines.append("```")
        return "\n".join(lines)

    def _build_graphviz_dot(self, chart_id: str, chart_name: str, entity: str, fields: List[str]) -> str:
        split_index = max(1, len(fields) // 2)
        top = fields[:split_index]
        bottom = fields[split_index:]

        dot_lines = [
            "```dot",
            f"// {chart_id} {chart_name}",
            "digraph ER {",
            "  rankdir=TB;",
            "  splines=line;",
            "  edge [dir=none];",
            '  node [fontname="Microsoft YaHei"];',
            f'  entity [label="{entity}", shape=box];',
            "  { rank=same; entity; }",
        ]

        top_nodes = []
        for idx, field in enumerate(top, start=1):
            name = self._sanitize_er_field_name(field)
            node_name = f"top_attr_{idx}"
            top_nodes.append(node_name)
            dot_lines.append(f'  {node_name} [label="{name}", shape=ellipse];')
            dot_lines.append(f"  {node_name} -> entity;")

        if top_nodes:
            dot_lines.append(f"  {{ rank=same; {'; '.join(top_nodes)}; }}")
            for left, right in zip(top_nodes, top_nodes[1:]):
                dot_lines.append(f"  {left} -> {right} [style=invis, weight=10];")

        bottom_nodes = []
        for idx, field in enumerate(bottom, start=1):
            name = self._sanitize_er_field_name(field)
            node_name = f"bottom_attr_{idx}"
            bottom_nodes.append(node_name)
            dot_lines.append(f'  {node_name} [label="{name}", shape=ellipse];')
            dot_lines.append(f"  entity -> {node_name};")

        if bottom_nodes:
            dot_lines.append(f"  {{ rank=same; {'; '.join(bottom_nodes)}; }}")
            for left, right in zip(bottom_nodes, bottom_nodes[1:]):
                dot_lines.append(f"  {left} -> {right} [style=invis, weight=10];")

        dot_lines.append("}")
        dot_lines.append("```")
        return "\n".join(dot_lines)

    def _build_graphviz_dot_multi(
        self,
        chart_id: str,
        chart_name: str,
        entities: List[str],
        attributes: Dict[str, List[str]],
        relationship: Dict[str, str],
    ) -> str:
        dot_lines = [
            "```dot",
            f"// {chart_id} {chart_name}",
            "digraph ER {",
            "  rankdir=TB;",
            "  splines=line;",
            "  edge [dir=none];",
            '  node [fontname="Microsoft YaHei"];',
        ]

        entity_nodes: List[str] = []
        for entity_index, entity in enumerate(entities, start=1):
            entity_node = f"entity_{entity_index}"
            entity_nodes.append(entity_node)
            dot_lines.append(f'  {entity_node} [label="{entity}", shape=box];')
            fields = attributes.get(entity, self._default_er_attributes(entity))
            split_index = max(1, len(fields) // 2)
            top = fields[:split_index]
            bottom = fields[split_index:]

            top_nodes: List[str] = []
            for idx, field in enumerate(top, start=1):
                node_name = f"{entity_node}_top_attr_{idx}"
                top_nodes.append(node_name)
                dot_lines.append(f'  {node_name} [label="{self._sanitize_er_field_name(field)}", shape=ellipse];')
                dot_lines.append(f"  {node_name} -> {entity_node} [dir=none];")
            if top_nodes:
                dot_lines.append(f"  {{ rank=same; {'; '.join(top_nodes)}; }}")

            bottom_nodes: List[str] = []
            for idx, field in enumerate(bottom, start=1):
                node_name = f"{entity_node}_bottom_attr_{idx}"
                bottom_nodes.append(node_name)
                dot_lines.append(f'  {node_name} [label="{self._sanitize_er_field_name(field)}", shape=ellipse];')
                dot_lines.append(f"  {entity_node} -> {node_name} [dir=none];")
            if bottom_nodes:
                dot_lines.append(f"  {{ rank=same; {'; '.join(bottom_nodes)}; }}")

        if entity_nodes:
            dot_lines.append(f"  {{ rank=same; {'; '.join(entity_nodes)}; }}")

        left = relationship.get("left", entities[0]) if entities else ""
        right = relationship.get("right", entities[-1]) if entities else ""
        relation_name = self._sanitize_er_field_name(relationship.get("name", "关联"))
        entity_map = {entity: node for entity, node in zip(entities, entity_nodes)}
        if left in entity_map and right in entity_map and left != right:
            dot_lines.append(f'  {entity_map[left]} -> {entity_map[right]} [label="{relation_name}"];')

        dot_lines.append("}")
        dot_lines.append("```")
        return "\n".join(dot_lines)

    def _generate_usecase_diagram(self, placeholder: ChartPlaceholder) -> str:
        generated = self._generate_with_hybrid(placeholder, "用例图混合生成失败，回退默认模板")
        if generated:
            return generated

        return f'''```mermaid
%% {placeholder.chart_id} {placeholder.chart_name}
graph TB
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

            replacement = mermaid_code
            if chart.chart_type == "E-R图":
                context = self.last_er_context.get(chart_id, {})
                schema = context.get("schema")
                related_schemas = context.get("related_schemas", [])
                graph_type = context.get("graph_type", str(self.er_modeling_config.get("graph_type", "chen")))
                if schema:
                    replacement = f"{mermaid_code}\n\n图{chart_id[1:]}说明：{self._build_er_caption(schema, related_schemas, graph_type)}"

            block_pattern = re.compile(
                rf'<!--\s*图表占位符[：:]\s*{re.escape(chart_id)}\s+.*?-->\s*'
                rf'>\s*(?:\[统计\]\s*|📊\s*)?\*\*\[图表占位符\]\*\*\s*'
                rf'.*?'
                rf'<!--\s*图表占位符结束\s*-->',
                re.DOTALL,
            )
            content = block_pattern.sub(replacement, content)

        if "图X-X" in mermaid_codes:
            simple_pattern = re.compile(r'\[图表占位符\][：:]?\s*(\w+图)?[，,]?\s*展示(.+?)(?:\n|$)')
            content = simple_pattern.sub(mermaid_codes["图X-X"], content, count=1)

        self.logger.info("占位符替换完成（原位替代）")
        return content

    def generate_report(self, content: str = "") -> str:
        report_lines = [
            "# 图表占位符分析报告",
            "",
            f"> 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"> 生效配置: {self.resolved_config_path or '默认配置'}",
            f"> E-R 模式: {self.er_modeling_config.get('graph_type', 'chen')}",
            "",
            "---",
            "",
            "## 统计信息",
            "",
            f"- 自动图表占位符总数: {len(self.charts)}",
            f"- 用户手填图片占位符总数: {len(self.user_provided)}",
            "",
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

        if content:
            report_lines.append("")
            report_lines.extend(self._build_integrity_section(self.validate_image_integrity(content)))

        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="论文图表生成器")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", default="workspace/final/images", help="输出目录（默认 workspace/final/images/）")
    parser.add_argument("--replace", action="store_true", default=True, help="直接替换原文档中的占位符（原位覆盖，默认开启）")
    parser.add_argument("--no-replace", action="store_true", help="不替换原文档，仅生成分析报告")
    parser.add_argument("--context", help="上下文文件路径（可选，用于辅助提取流程步骤）")
    parser.add_argument("--config", help="配置文件路径（默认自动查找 thesis-workspace/.thesis-config.yaml）")
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

    er_modeling_config, _ = _load_er_modeling_config(args.config, input_path=str(input_path))
    diagram_generation_config, _ = _load_diagram_generation_config(args.config, input_path=str(input_path))
    generator = ChartGenerator(
        output_dir=args.output,
        er_modeling_config=er_modeling_config,
        diagram_generation_config=diagram_generation_config,
        config_path=args.config,
        input_path=str(input_path),
    )
    mermaid_codes = generator.generate_all(content, context=context_text)

    print("\n[OK] 图表生成完成！")
    print(f"   共生成 {len(mermaid_codes)} 个图表")
    print(f"   输出目录: {args.output}")
    print(f"   生效配置: {generator.resolved_config_path or '默认配置'}")
    print(f"   E-R 模式: {generator.er_modeling_config.get('graph_type', 'chen')}")
    if generator.user_provided:
        print(f"   用户手填图片: {len(generator.user_provided)} 个")

    if do_replace and mermaid_codes:
        new_content = generator.replace_placeholders(content, mermaid_codes)
        input_path.write_text(new_content, encoding='utf-8')
        print(f"\n[文档] 已原位更新: {input_path}")

    if args.report:
        report = generator.generate_report(content)
        report_file = Path(args.output) / "chart_report.md"
        report_file.write_text(report, encoding='utf-8')
        print(f"\n[统计] 分析报告: {report_file}")


if __name__ == "__main__":
    main()

