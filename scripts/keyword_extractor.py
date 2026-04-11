# -*- coding: utf-8 -*-
"""
关键词提取器 - 从论文上下文提取图表生成所需的关键信息

功能：
1. 提取实体名称（系统名、模块名、角色名）
2. 提取流程步骤序列
3. 提取实体关系描述
4. 提取技术栈关键词

使用方法：
    from keyword_extractor import KeywordExtractor
    extractor = KeywordExtractor()
    entities = extractor.extract_entities(context_text)
    steps = extractor.extract_flow_steps(description)
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter

# 导入日志模块
try:
    from logger import get_logger
except ImportError:
    import logging
    def get_logger():
        return logging.getLogger()


class KeywordExtractor:
    """关键词提取器"""

    # 系统名称模式
    SYSTEM_PATTERNS = [
        r'([\w\u4e00-\u9fa5]+系统)',
        r'([\w\u4e00-\u9fa5]+平台)',
        r'([\w\u4e00-\u9fa5]+应用)',
        r'([\w\u4e00-\u9fa5]+服务)',
        r'([\w\u4e00-\u9fa5]+模块)',
    ]

    # 技术栈关键词
    TECH_KEYWORDS = {
        '前端': ['Vue', 'React', 'Angular', 'HTML', 'CSS', 'JavaScript', 'TypeScript', 'jQuery', 'Bootstrap', 'Element', 'Ant Design'],
        '后端': ['Spring', 'Spring Boot', 'Django', 'Flask', 'Express', 'Node.js', 'Java', 'Python', 'PHP', 'Go', '.NET', 'ASP.NET'],
        '数据库': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'SQLite', 'Elasticsearch'],
        '中间件': ['Kafka', 'RabbitMQ', 'Nginx', 'Tomcat', 'Docker', 'Kubernetes'],
        'API': ['REST', 'RESTful', 'GraphQL', 'SOAP', 'WebSocket', 'HTTP', 'JSON', 'XML'],
    }

    # 角色关键词
    ROLE_KEYWORDS = ['用户', '管理员', '访客', '会员', '系统管理员', '普通用户', '超级管理员', '运营', '客服']

    # 动作关键词（用于流程提取）
    ACTION_KEYWORDS = ['登录', '注册', '提交', '查询', '删除', '修改', '添加', '创建', '审核', '批准', '拒绝', '发送', '接收', '处理', '验证', '检查']

    def __init__(self):
        self.logger = get_logger()

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取实体名称

        Args:
            text: 待提取文本

        Returns:
            实体字典 {实体类型: 实体列表}
        """
        entities = {
            'systems': [],
            'modules': [],
            'roles': [],
            'tech_stack': [],
        }

        # 提取系统名称
        for pattern in self.SYSTEM_PATTERNS:
            matches = re.findall(pattern, text)
            entities['systems'].extend(matches)

        # 去重
        entities['systems'] = list(set(entities['systems']))

        # 提取角色
        for role in self.ROLE_KEYWORDS:
            if role in text:
                entities['roles'].append(role)

        # 提取技术栈
        for category, keywords in self.TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text.lower() or kw in text:
                    entities['tech_stack'].append(kw)

        entities['tech_stack'] = list(set(entities['tech_stack']))

        self.logger.debug(f"提取实体: 系统 {len(entities['systems'])} 个, 角色 {len(entities['roles'])} 个")

        return entities

    def extract_flow_steps(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取流程步骤

        Args:
            text: 流程描述文本

        Returns:
            步骤列表 [{name, type, node_id, next_node}]
        """
        steps = []

        # 模式 1：数字序号步骤 "1. xxx" 或 "1、xxx"
        numbered_pattern = r'[（(]?\d+[）)、.．]\s*(.+?)(?=[（(]?\d+[）)、.．]|$)'
        numbered_matches = re.findall(numbered_pattern, text)

        if numbered_matches:
            for i, match in enumerate(numbered_matches):
                step_text = match.strip()
                if step_text:
                    step_type = self._determine_step_type(step_text)
                    node_id = chr(66 + i)  # B, C, D...
                    next_node = chr(67 + i) if i < len(numbered_matches) - 1 else 'Z'
                    steps.append({
                        'name': step_text,
                        'type': step_type,
                        'node_id': node_id,
                        'next_node': next_node,
                    })
            self.logger.debug(f"数字序号提取: {len(steps)} 个步骤")
            return steps

        # 模式 2：中文序号步骤 "第一步：xxx"
        chinese_pattern = r'(第[一二三四五六七八九十]+步[：:]\s*|首先[，,]?\s*|然后[，,]?\s*|接着[，,]?\s*|最后[，,]?\s*)(.+?)(?=第[一二三四五六七八九十]+步[：:]|首先|然后|接着|最后|$)'
        chinese_matches = re.findall(chinese_pattern, text)

        if chinese_matches:
            for i, (prefix, content) in enumerate(chinese_matches):
                step_text = content.strip()
                if step_text:
                    step_type = self._determine_step_type(step_text)
                    node_id = chr(66 + i)
                    next_node = chr(67 + i) if i < len(chinese_matches) - 1 else 'Z'
                    steps.append({
                        'name': step_text,
                        'type': step_type,
                        'node_id': node_id,
                        'next_node': next_node,
                    })
            self.logger.debug(f"中文序号提取: {len(steps)} 个步骤")
            return steps

        # 模式 3：箭头分隔 "A -> B -> C"
        arrow_pattern = r'([^-→]+)\s*[-→]+\s*'
        arrow_matches = re.findall(arrow_pattern, text)

        if arrow_matches:
            for i, match in enumerate(arrow_matches):
                step_text = match.strip()
                if step_text:
                    node_id = chr(66 + i)
                    next_node = chr(67 + i) if i < len(arrow_matches) else 'Z'
                    steps.append({
                        'name': step_text,
                        'type': 'process',
                        'node_id': node_id,
                        'next_node': next_node,
                    })

            # 添加最后一个节点
            last_match = re.search(r'[-→]+\s*([^-→]+)$', text)
            if last_match:
                steps.append({
                    'name': last_match.group(1).strip(),
                    'type': 'process',
                    'node_id': chr(66 + len(steps)),
                    'next_node': 'Z',
                })

            self.logger.debug(f"箭头分隔提取: {len(steps)} 个步骤")
            return steps

        # 模式 4：列表格式 "- 步骤描述"
        list_pattern = r'[-*•]\s*(.+?)(?=\n|$)'
        list_matches = re.findall(list_pattern, text)

        if list_matches:
            for i, match in enumerate(list_matches):
                step_text = match.strip()
                if step_text and len(step_text) > 2:
                    step_type = self._determine_step_type(step_text)
                    node_id = chr(66 + i)
                    next_node = chr(67 + i) if i < len(list_matches) - 1 else 'Z'
                    steps.append({
                        'name': step_text,
                        'type': step_type,
                        'node_id': node_id,
                        'next_node': next_node,
                    })
            self.logger.debug(f"列表格式提取: {len(steps)} 个步骤")
            return steps

        # 模式 5：句子分割（按句号）
        if not steps:
            sentences = re.split(r'[。；]', text)
            for i, sentence in enumerate(sentences[:5]):  # 最多5个步骤
                sentence = sentence.strip()
                if sentence and len(sentence) > 3:
                    step_type = self._determine_step_type(sentence)
                    node_id = chr(66 + i)
                    next_node = chr(67 + i) if i < len(sentences[:5]) - 1 else 'Z'
                    steps.append({
                        'name': sentence[:50],  # 截断长句子
                        'type': step_type,
                        'node_id': node_id,
                        'next_node': next_node,
                    })

        return steps

    def _determine_step_type(self, step_text: str) -> str:
        """
        判断步骤类型

        Args:
            step_text: 步骤描述

        Returns:
            步骤类型 ('process', 'decision', 'io')
        """
        # 决策节点关键词
        decision_keywords = ['判断', '检查', '验证', '确认', '是否', '判断是否', '检测']
        for kw in decision_keywords:
            if kw in step_text:
                return 'decision'

        # 输入输出节点关键词
        io_keywords = ['输入', '输出', '接收', '发送', '读取', '写入', '获取', '返回']
        for kw in io_keywords:
            if kw in step_text:
                return 'io'

        return 'process'

    def extract_relations(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取实体关系

        Args:
            text: 关系描述文本

        Returns:
            关系列表 [{from_entity, relation, to_entity}]
        """
        relations = []

        # 关系动词模式
        relation_patterns = [
            r'([\w\u4e00-\u9fa5]+)\s*(调用|依赖|关联|连接|访问|管理|控制|监控|包含|属于|对应)\s*([\w\u4e00-\u9fa5]+)',
            r'([\w\u4e00-\u9fa5]+)\s*->\s*([\w\u4e00-\u9fa5]+)',
            r'([\w\u4e00-\u9fa5]+)\s*(发送|传递|传输|转发)\s*(数据|信息|消息|请求)\s*(给|至)\s*([\w\u4e00-\u9fa5]+)',
        ]

        for pattern in relation_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 3:
                    relations.append({
                        'from_entity': match[0],
                        'relation': match[1] if len(match) > 2 else '关联',
                        'to_entity': match[-1],
                    })

        return relations

    def extract_api_sequence(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取 API 调用序列

        Args:
            text: API 调用描述

        Returns:
            消息序列 [{from, to, type, content}]
        """
        messages = []

        # 参与者映射
        participants = self._identify_participants(text)

        # API 调用模式
        api_patterns = [
            r'([\w\u4e00-\u9fa5]+)\s*(向|给)\s*([\w\u4e00-\u9fa5]+)\s*(发送|提交|请求)\s*([\w\u4e00-\u9fa5]+)',
            r'([\w\u4e00-\u9fa5]+)\s*(接收|响应|返回)\s*([\w\u4e00-\u9fa5]+)',
            r'([\w\u4e00-\u9fa5]+)\s*(调用)\s*([\w\u4e00-\u9fa5]+)\s*(API|接口)',
        ]

        for pattern in api_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 根据匹配结果构建消息
                if '发送' in match or '请求' in match or '提交' in match:
                    messages.append({
                        'from': match[0],
                        'to': match[2],
                        'type': 'sync',
                        'content': match[-1] if len(match) > 3 else '请求',
                    })
                elif '返回' in match or '响应' in match:
                    messages.append({
                        'from': match[2] if len(match) > 2 else match[-1],
                        'to': match[0],
                        'type': 'return',
                        'content': match[-1] if len(match) > 2 else '响应',
                    })

        return messages

    def _identify_participants(self, text: str) -> List[Dict[str, str]]:
        """
        识别时序图参与者

        Args:
            text: 描述文本

        Returns:
            参与者列表 [{id, name, type}]
        """
        participants = []

        # 常见参与者映射
        participant_keywords = {
            '用户': {'id': 'U', 'type': 'actor'},
            '前端': {'id': 'F', 'type': 'participant'},
            '客户端': {'id': 'C', 'type': 'participant'},
            '后端': {'id': 'B', 'type': 'participant'},
            '服务器': {'id': 'S', 'type': 'participant'},
            'API': {'id': 'A', 'type': 'participant'},
            '数据库': {'id': 'D', 'type': 'participant'},
            '缓存': {'id': 'R', 'type': 'participant'},
        }

        # 提取实体作为参与者
        entities = self.extract_entities(text)

        # 添加角色作为参与者
        for role in entities['roles']:
            if role in participant_keywords:
                participants.append({
                    'id': participant_keywords[role]['id'],
                    'name': role,
                    'type': participant_keywords[role]['type'],
                })

        # 添加系统作为参与者
        for system in entities['systems'][:3]:
            participants.append({
                'id': chr(65 + len(participants)),
                'name': system,
                'type': 'participant',
            })

        return participants

    def summarize_for_chart(self, text: str, chart_type: str) -> Dict[str, Any]:
        """
        根据图表类型提取关键信息摘要

        Args:
            text: 论文上下文文本
            chart_type: 图表类型

        Returns:
            提取的关键信息字典
        """
        summary = {}

        if chart_type in ['架构图', 'architecture']:
            summary = {
                'entities': self.extract_entities(text),
                'relations': self.extract_relations(text),
                'tech_stack': self.extract_entities(text)['tech_stack'],
            }

        elif chart_type in ['流程图', 'flowchart']:
            summary = {
                'steps': self.extract_flow_steps(text),
                'roles': self.extract_entities(text)['roles'],
            }

        elif chart_type in ['E-R图', 'er_diagram']:
            summary = {
                'entities': self.extract_entities(text),
                'relations': self.extract_relations(text),
            }

        elif chart_type in ['时序图', 'sequence']:
            summary = {
                'participants': self._identify_participants(text),
                'messages': self.extract_api_sequence(text),
            }

        elif chart_type in ['用例图', 'usecase']:
            summary = {
                'roles': self.extract_entities(text)['roles'],
                'actions': [kw for kw in self.ACTION_KEYWORDS if kw in text],
            }

        return summary


def main():
    """测试关键词提取器"""
    extractor = KeywordExtractor()

    # 测试实体提取
    test_text = """
    本系统采用Vue.js作为前端框架，Spring Boot作为后端服务框架，
    使用MySQL数据库存储数据。系统包含用户管理模块、订单管理模块和商品管理模块。
    用户和管理员都可以登录系统进行操作。
    """

    print("测试实体提取:")
    entities = extractor.extract_entities(test_text)
    for category, items in entities.items():
        print(f"  {category}: {items}")

    # 测试流程提取
    flow_text = """
    用户登录流程：
    1. 用户输入用户名和密码
    2. 系统验证用户信息
    3. 判断是否验证通过
    4. 返回登录结果
    """

    print("\n测试流程提取:")
    steps = extractor.extract_flow_steps(flow_text)
    for step in steps:
        print(f"  {step['node_id']}: {step['name']} ({step['type']})")

    # 测试关系提取
    relation_text = """
    前端调用后端API获取数据，后端访问数据库查询信息，
    用户模块管理用户信息，订单模块关联商品模块。
    """

    print("\n测试关系提取:")
    relations = extractor.extract_relations(relation_text)
    for rel in relations:
        print(f"  {rel['from_entity']} -> {rel['relation']} -> {rel['to_entity']}")


if __name__ == "__main__":
    main()