# -*- coding: utf-8 -*-
"""
图表模板加载器 - 加载和管理图表模板

功能：
1. 从 YAML 文件加载图表模板
2. 根据关键词匹配合适的模板
3. 支持模板变量填充
4. 支持模板继承和扩展

使用方法：
    from chart_template_loader import ChartTemplateLoader
    loader = ChartTemplateLoader()
    template = loader.find_template("架构图", "Web系统前后端分离")
    mermaid_code = loader.render_template(template, variables)
"""

import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

# 导入日志模块
try:
    from logger import get_logger
except ImportError:
    import logging
    def get_logger():
        """get_logger"""
        return logging.getLogger()


class ChartTemplateLoader:
    """图表模板加载器"""

    def __init__(self, template_dir: str = None):
        """__init__"""
        self.logger = get_logger()

        # 默认模板目录
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates" / "charts"
        self.template_dir = Path(template_dir)

        # 加载索引
        self.templates_index: Dict[str, List[Dict]] = {}
        self.loaded_templates: Dict[str, Dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        """加载模板索引文件"""
        index_file = self.template_dir / "_index.yaml"

        if not index_file.exists():
            self.logger.warning(f"模板索引文件不存在: {index_file}")
            return

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = yaml.safe_load(f)

            self.templates_index = index_data.get('templates', {})
            self.logger.info(f"已加载 {len(self.templates_index)} 个模板类型的索引")

        except Exception as e:
            self.logger.error(f"加载模板索引失败: {e}")

    def load_template(self, template_id: str) -> Optional[Dict]:
        """
        加载单个模板文件

        Args:
            template_id: 模板 ID

        Returns:
            模板数据字典
        """
        # 检查缓存
        if template_id in self.loaded_templates:
            return self.loaded_templates[template_id]

        # 查找模板文件
        template_file = None
        for chart_type, templates in self.templates_index.items():
            for template in templates:
                if template['id'] == template_id:
                    template_file = self.template_dir / template['file']
                    break

        if template_file is None or not template_file.exists():
            self.logger.warning(f"模板文件不存在: {template_id}")
            return None

        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)

            # 缓存模板
            self.loaded_templates[template_id] = template_data
            self.logger.debug(f"已加载模板: {template_id}")

            return template_data

        except Exception as e:
            self.logger.error(f"加载模板失败: {template_id} - {e}")
            return None

    def find_template(self, chart_type: str, description: str = "") -> Optional[Dict]:
        """
        根据图表类型和描述查找最匹配的模板

        Args:
            chart_type: 图表类型（架构图、流程图、E-R图等）
            description: 图表描述文本

        Returns:
            最佳匹配的模板数据
        """
        # 规范化图表类型
        chart_type_normalized = self._normalize_chart_type(chart_type)

        # 获取该类型的模板列表
        templates = self.templates_index.get(chart_type_normalized, [])

        if not templates:
            self.logger.warning(f"未找到 {chart_type} 类型的模板")
            return None

        # 关键词匹配得分
        best_match = None
        best_score = 0

        description_lower = description.lower()

        for template_info in templates:
            template_id = template_info['id']
            keywords = template_info.get('keywords', [])

            # 计算匹配得分
            score = sum(1 for kw in keywords if kw.lower() in description_lower)

            if score > best_score:
                best_score = score
                best_match = template_id

        # 如果没有关键词匹配，使用第一个模板
        if best_match is None and templates:
            best_match = templates[0]['id']

        if best_match:
            return self.load_template(best_match)

        return None

    def _normalize_chart_type(self, chart_type: str) -> str:
        """规范化图表类型名称"""
        type_map = {
            "架构图": "architecture",
            "流程图": "flowchart",
            "业务流程图": "flowchart",
            "E-R图": "er_diagram",
            "ER图": "er_diagram",
            "实体关系图": "er_diagram",
            "用例图": "usecase",
            "时序图": "sequence",
            "类图": "class_diagram",
        }

        normalized = type_map.get(chart_type, chart_type)
        return normalized

    def render_template(
        self,
        template: Dict,
        variables: Dict[str, Any],
        chart_id: str = "",
        chart_name: str = ""
    ) -> str:
        """
        使用变量渲染模板生成 Mermaid 代码

        Args:
            template: 模板数据
            variables: 变量值字典
            chart_id: 图表编号
            chart_name: 图表名称

        Returns:
            渲染后的 Mermaid 代码
        """
        mermaid_template = template.get('mermaid_template', '')

        if not mermaid_template:
            self.logger.warning("模板缺少 mermaid_template 字段")
            return ""

        # 准备变量
        render_vars = {
            'chart_id': chart_id,
            'chart_name': chart_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # 合合模板默认变量和用户变量
        template_vars = template.get('variables', [])
        for var_def in template_vars:
            var_name = var_def['name']
            default_value = var_def.get('default', '')
            render_vars[var_name] = variables.get(var_name, default_value)

        # 简单变量替换（非 Jinja2 格式）
        # 将 {{var}} 替换为变量值
        result = mermaid_template
        for var_name, var_value in render_vars.items():
            if isinstance(var_value, list):
                # 列表变量需要特殊处理（暂不支持）
                continue
            result = result.replace('{{' + var_name + '}}', str(var_value))

        return result

    def extract_variables_from_description(
        self,
        template: Dict,
        description: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        从描述文本中提取模板变量值

        Args:
            template: 模板数据
            description: 图表描述
            context: 论文上下文（可选）

        Returns:
            提取的变量字典
        """
        variables = {}

        template_vars = template.get('variables', [])
        for var_def in template_vars:
            var_name = var_def['name']
            extract_rule = var_def.get('extract_rule', '')

            if extract_rule:
                # 使用提取规则提取变量
                extracted = self._extract_by_rule(description, extract_rule)
                if extracted:
                    variables[var_name] = extracted

        return variables

    def _extract_by_rule(self, text: str, rule: str) -> Optional[str]:
        """
        根据规则从文本中提取内容

        Args:
            text: 待提取文本
            rule: 提取规则描述

        Returns:
            提取的内容
        """
        # 简单规则实现
        if "系统名称" in rule:
            # 尝试匹配系统名称模式
            patterns = [
                r'([\w]+系统)',
                r'([\w]+平台)',
                r'([\w]+应用)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)

        if "起始动作" in rule:
            # 提取流程起始动作
            patterns = [
                r'首先[，,]?\s*(.+?)(?=[，,。]|然后|接着)',
                r'用户\s*(.+?)(?=\n|$)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()

        return None

    def list_templates(self) -> Dict[str, List[str]]:
        """列出所有可用模板"""
        result = {}
        for chart_type, templates in self.templates_index.items():
            result[chart_type] = [t['id'] for t in templates]
        return result


def main():
    """测试模板加载器"""
    loader = ChartTemplateLoader()

    print("可用模板:")
    templates = loader.list_templates()
    for chart_type, template_ids in templates.items():
        print(f"  {chart_type}: {template_ids}")

    # 测试模板匹配
    print("\n测试模板匹配:")
    template = loader.find_template("架构图", "Web系统前后端分离架构设计")
    if template:
        print(f"  匹配模板: {template['id']} - {template['name']}")

        # 测试渲染
        variables = {'frontend_name': 'Vue前端', 'backend_name': 'Spring Boot'}
        mermaid = loader.render_template(template, variables, "图2-1", "系统架构图")
        print(f"\n渲染结果:\n{mermaid}")


if __name__ == "__main__":
    main()
