# -*- coding: utf-8 -*-
"""
LLM 图表生成兜底接口 - 当模板生成无法满足需求时调用 LLM

功能：
1. 支持多种 LLM 服务（Claude API、本地模型等）
2. 提供图表生成专用 Prompt 模板
3. 实现智能重试和错误处理
4. 支持复杂图表场景的智能生成

使用方法：
    from llm_chart_generator import LLMChartGenerator
    generator = LLMChartGenerator()
    mermaid_code = generator.generate_chart(chart_type, description, context)
"""

import os
import re
import json
from typing import Dict, Optional, Any, List
from datetime import datetime

# 导入日志模块
try:
    from logger import get_logger
except ImportError:
    import logging
    def get_logger():
        return logging.getLogger()


class LLMChartGenerator:
    """LLM 图表生成器"""

    # 图表类型对应的 Prompt 模板
    CHART_PROMPTS = {
        '架构图': """
请根据以下描述生成一个系统架构图的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 graph TB 格式
2. 包含表现层、接口层、业务层、数据层四个子图
3. 每个层级的组件名称要具体，不要使用通用名称
4. 使用中文标注
5. 用箭头表示层级间的调用关系

请只输出 Mermaid 代码，不要其他解释。
""",
        '流程图': """
请根据以下描述生成一个业务流程图的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 flowchart TD 格式
2. 包含开始和结束节点（使用圆角矩形）
3. 决策节点使用菱形 {decision}
4. 处理节点使用矩形 [process]
5. 输入输出节点使用平行四边形 [/io/]
6. 步骤名称要具体，体现实际业务操作
7. 使用中文标注

请只输出 Mermaid 代码，不要其他解释。
""",
        'E-R图': """
请根据以下描述生成一个实体关系图（E-R图）的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 erDiagram 格式
2. 实体使用大写命名
3. 包含实体的主要字段（使用中文注释）
4. 使用 ||--o{ 等关系符号表示实体间的关系
5. 标注 PK（主键）、FK（外键）

请只输出 Mermaid 代码，不要其他解释。
""",
        '时序图': """
请根据以下描述生成一个时序图的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 sequenceDiagram 格式
2. actor 用于表示用户/角色，participant 用于表示系统组件
3. 使用 ->> 表示同步调用，-->> 表示返回
4. 每个消息要有明确的描述
5. 按时间顺序从上到下排列
6. 使用中文标注

请只输出 Mermaid 代码，不要其他解释。
""",
        '用例图': """
请根据以下描述生成一个用例图的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 graph LR 格式
2. 用圆角节点 ((用例)) 表示用例
3. 用圆节点 ((角色)) 表示角色
4. 用箭头表示角色与用例的关系
5. 使用中文标注

请只输出 Mermaid 代码，不要其他解释。
""",
        '类图': """
请根据以下描述生成一个类图的 Mermaid 代码。

图表描述：{description}
上下文信息：{context}

要求：
1. 使用 classDiagram 格式
2. 类名使用 PascalCase 命名
3. 包含类的属性和方法
4. 使用 --|> 表示继承关系
5. 使用 --> 表示关联关系
6. 标注 +public -private

请只输出 Mermaid 代码，不要其他解释。
""",
    }

    def __init__(self, api_key: str = None, model: str = "claude-3-haiku-20240307"):
        self.logger = get_logger()
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_tokens = 2048
        self.temperature = 0.3  # 较低温度保证一致性

        # 检查是否有可用的 LLM 服务
        self._check_availability()

    def _check_availability(self) -> bool:
        """检查 LLM 服务是否可用"""
        if self.api_key:
            self.logger.info("Anthropic API Key 已配置")
            return True

        # 检查是否有其他可用的 LLM 服务
        # 这里可以扩展支持其他服务
        self.logger.warning("未配置 API Key，LLM 生成功能不可用")
        return False

    def generate_chart(
        self,
        chart_type: str,
        description: str,
        context: str = "",
        chart_id: str = "",
        chart_name: str = ""
    ) -> Optional[str]:
        """
        使用 LLM 生成图表 Mermaid 代码

        Args:
            chart_type: 图表类型
            description: 图表描述
            context: 论文上下文
            chart_id: 图表编号
            chart_name: 图表名称

        Returns:
            Mermaid 代码字符串
        """
        # 检查是否可用
        if not self.api_key:
            self.logger.warning("LLM 服务不可用，返回 None")
            return None

        # 获取对应的 Prompt 模板
        prompt_template = self.CHART_PROMPTS.get(chart_type)
        if not prompt_template:
            self.logger.warning(f"未找到 {chart_type} 类型的 Prompt 模板")
            return None

        # 构建 Prompt
        prompt = prompt_template.format(
            description=description,
            context=context[:500] if context else "无"
        )

        # 调用 LLM
        try:
            response = self._call_llm(prompt)

            if response:
                # 提取 Mermaid 代码
                mermaid_code = self._extract_mermaid(response)

                # 添加图表编号和名称注释
                if chart_id or chart_name:
                    header = f"%% {chart_id} {chart_name}\n%% LLM 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    mermaid_code = header + mermaid_code

                return mermaid_code

        except Exception as e:
            self.logger.error(f"LLM 生成失败: {e}")

        return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """
        调用 LLM API

        Args:
            prompt: 输入 Prompt

        Returns:
            LLM 响应文本
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            self.logger.debug(f"LLM 响应长度: {len(response_text)} 字符")

            return response_text

        except ImportError:
            self.logger.warning("anthropic 库未安装，请运行: pip install anthropic")
            return None

        except Exception as e:
            self.logger.error(f"LLM API 调用失败: {e}")
            return None

    def _extract_mermaid(self, response: str) -> str:
        """
        从 LLM 响应中提取 Mermaid 代码

        Args:
            response: LLM 原始响应

        Returns:
            纯净的 Mermaid 代码
        """
        # 尝试提取 ```mermaid ... ``` 代码块
        mermaid_pattern = r'```mermaid\s*\n(.*?)```'
        match = re.search(mermaid_pattern, response, re.DOTALL)

        if match:
            return match.group(1).strip()

        # 如果没有代码块，尝试直接提取 Mermaid 语法
        # 检查是否包含 Mermaid 关键字
        mermaid_keywords = ['graph', 'flowchart', 'erDiagram', 'sequenceDiagram', 'classDiagram']

        for keyword in mermaid_keywords:
            if keyword in response:
                # 提取从关键字开始到结束的内容
                start_idx = response.find(keyword)
                # 尝试找到合理的结束位置
                end_patterns = ['\n\n', '```', '---']
                end_idx = len(response)
                for ep in end_patterns:
                    pos = response.find(ep, start_idx)
                    if pos > start_idx and pos < end_idx:
                        end_idx = pos

                mermaid_content = response[start_idx:end_idx].strip()
                return mermaid_content

        # 如果都不匹配，返回原响应（可能需要人工处理）
        self.logger.warning("未能提取纯 Mermaid 代码，返回原始响应")
        return response.strip()

    def is_complex_scenario(self, description: str, context: str) -> bool:
        """
        判断是否为复杂场景，需要 LLM 生成

        Args:
            description: 图表描述
            context: 上下文

        Returns:
            是否为复杂场景
        """
        complexity_indicators = [
            len(description) > 200,  # 描述很长
            len(context) > 1000,  # 上下文丰富
            '自定义' in description,  # 明确要求自定义
            '特殊' in description,
            '复杂' in description,
            '多层级' in description,
            '交互' in description and '时序' not in description,  # 复杂交互非时序图
        ]

        # 如果满足任一复杂度指标
        if any(complexity_indicators):
            self.logger.info("检测到复杂场景，建议使用 LLM 生成")
            return True

        return False

    def estimate_cost(self, description: str, context: str) -> float:
        """
        估算 LLM 调用成本

        Args:
            description: 图表描述
            context: 上下文

        Returns:
            估算成本（美元）
        """
        # 简单估算：输入 tokens + 输出 tokens
        input_chars = len(description) + len(context[:500]) + 200  # Prompt 模板长度
        output_chars = 500  # 预估输出长度

        # 粗略估算：1 token ≈ 4 chars
        input_tokens = input_chars / 4
        output_tokens = output_chars / 4

        # Claude Haiku 价格参考（2024）
        input_price = 0.25 / 1_000_000  # $0.25 per 1M tokens
        output_price = 1.25 / 1_000_000  # $1.25 per 1M tokens

        cost = (input_tokens * input_price) + (output_tokens * output_price)

        return cost


class HybridChartGenerator:
    """
    混合图表生成器

    优先使用模板库，复杂场景使用 LLM 兜底
    """

    def __init__(self):
        self.logger = get_logger()

        # 初始化组件
        from chart_template_loader import ChartTemplateLoader
        from keyword_extractor import KeywordExtractor

        self.template_loader = ChartTemplateLoader()
        self.keyword_extractor = KeywordExtractor()
        self.llm_generator = LLMChartGenerator()

    def generate(
        self,
        chart_type: str,
        description: str,
        context: str = "",
        chart_id: str = "",
        chart_name: str = ""
    ) -> str:
        """
        智能生成图表

        Args:
            chart_type: 图表类型
            description: 图表描述
            context: 论文上下文
            chart_id: 图表编号
            chart_name: 图表名称

        Returns:
            Mermaid 代码
        """
        # 1. 判断是否为复杂场景
        is_complex = self.llm_generator.is_complex_scenario(description, context)

        if is_complex and self.llm_generator.api_key:
            # 优先使用 LLM 生成
            self.logger.info("复杂场景，使用 LLM 生成")
            mermaid_code = self.llm_generator.generate_chart(
                chart_type, description, context, chart_id, chart_name
            )
            if mermaid_code:
                return mermaid_code

        # 2. 尝试模板生成
        self.logger.info("尝试模板生成")
        template = self.template_loader.find_template(chart_type, description)

        if template:
            # 提取关键词变量
            variables = self.keyword_extractor.summarize_for_chart(description, chart_type)

            # 渲染模板
            mermaid_code = self.template_loader.render_template(
                template, variables, chart_id, chart_name
            )
            if mermaid_code:
                return mermaid_code

        # 3. 使用默认模板（chart_generator.py 中的逻辑）
        self.logger.info("使用默认模板生成")
        return self._generate_default(chart_type, chart_id, chart_name, description)

    def _generate_default(
        self,
        chart_type: str,
        chart_id: str,
        chart_name: str,
        description: str
    ) -> str:
        """生成默认图表（fallback）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if chart_type in ['架构图', 'architecture']:
            return f'''```mermaid
%% {chart_id} {chart_name}
%% 自动生成于 {timestamp}
graph TB
    subgraph 表现层
        A1[前端应用]
        A2[移动端]
    end
    subgraph 接口层
        B1[REST API]
    end
    subgraph 业务层
        C1[业务服务]
    end
    subgraph 数据层
        D1[(数据库)]
    end
    A1 --> B1
    A2 --> B1
    B1 --> C1
    C1 --> D1
```'''

        elif chart_type in ['流程图', 'flowchart']:
            return f'''```mermaid
%% {chart_id} {chart_name}
%% 自动生成于 {timestamp}
flowchart TD
    A([开始]) --> B[处理请求]
    B --> C{判断条件}
    C -->|是| D[继续处理]
    C -->|否| Z([结束])
    D --> Z
```'''

        else:
            return f'''```mermaid
%% {chart_id} {chart_name}
%% 自动生成于 {timestamp}
graph TB
    A[开始]
    B[处理]
    C[结束]
    A --> B --> C
```'''


def main():
    """测试 LLM 图表生成器"""
    generator = LLMChartGenerator()

    # 检查可用性
    print(f"LLM 服务可用: {generator.api_key != ''}")

    # 测试成本估算
    description = "用户登录系统的业务流程，包含输入用户名密码、验证、判断是否通过、返回结果等步骤"
    cost = generator.estimate_cost(description, "")
    print(f"估算成本: ${cost:.6f}")

    # 测试复杂场景判断
    is_complex = generator.is_complex_scenario(description, "")
    print(f"复杂场景: {is_complex}")

    # 测试混合生成器
    print("\n测试混合生成器:")
    hybrid = HybridChartGenerator()
    mermaid = hybrid.generate("流程图", description, "", "图3-1", "用户登录流程图")
    print(mermaid)


if __name__ == "__main__":
    main()