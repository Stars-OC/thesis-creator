# -*- coding: utf-8 -*-
"""LLM 图表生成器的本地兜底实现。"""

from typing import Dict


class LLMChartGenerator:
    CHART_PROMPTS: Dict[str, str] = {
        "架构图": "请生成 Mermaid 架构图，使用 graph LR 表示左到右布局，分层展示系统结构。",
        "流程图": "请生成 Mermaid 流程图，方向不要固定为单一方向，可根据内容选择 LR、TB、BT、RL，避免节点过于密集。",
        "E-R图": "请生成 Mermaid E-R 图，突出实体、字段和关系。",
        "用例图": "请生成 Mermaid 用例图，展示参与者与用例之间的关系。",
        "时序图": "请生成 Mermaid sequenceDiagram，展示参与者交互顺序。",
        "功能模块图": "请生成 Mermaid 模块结构图，展示功能模块划分。",
    }

    def generate(self, chart_type: str, description: str, context: str, chart_id: str, chart_name: str) -> str:
        return HybridChartGenerator()._generate_default(chart_type, chart_id, chart_name, description or context)


class HybridChartGenerator:
    def generate(self, chart_type: str, description: str, context: str, chart_id: str, chart_name: str) -> str:
        return self._generate_default(chart_type, chart_id, chart_name, description or context)

    def _generate_default(self, chart_type: str, chart_id: str, chart_name: str, description: str) -> str:
        if chart_type == "架构图":
            return self._architecture(chart_id, chart_name)
        if chart_type == "流程图":
            return self._flowchart(chart_id, chart_name)
        if chart_type == "用例图":
            return self._usecase(chart_id, chart_name)
        if chart_type == "时序图":
            return self._sequence(chart_id, chart_name)
        if chart_type == "E-R图":
            return self._er(chart_id, chart_name)
        return self._module(chart_id, chart_name)

    def _architecture(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
graph LR
    A[用户界面] --> B[业务服务]
    B --> C[数据访问]
    C --> D[(数据库)]
```'''

    def _flowchart(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
flowchart TB
    A([开始]) --> B[接收请求]
    B --> C{{校验是否通过}}
    C -->|是| D[处理业务]
    C -->|否| E[返回错误]
    D --> F([结束])
    E --> F
```'''

    def _usecase(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
graph TB
    User((用户)) --> UC1((登录))
    User --> UC2((查询数据))
    Admin((管理员)) --> UC3((审核))
```'''

    def _sequence(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
sequenceDiagram
    participant U as 用户
    participant S as 系统
    U->>S: 发起请求
    S-->>U: 返回结果
```'''

    def _er(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
erDiagram
    USER ||--o{{ ORDER : creates
    USER {{
        bigint id PK
        string username
    }}
    ORDER {{
        bigint id PK
        bigint user_id FK
    }}
```'''

    def _module(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
graph TB
    A[核心模块] --> B[用户管理]
    A --> C[业务处理]
    A --> D[系统配置]
```'''
