# -*- coding: utf-8 -*-
"""LLM 图表生成器的本地兜底实现。"""

from typing import Dict


class LLMChartGenerator:
    CHART_PROMPTS: Dict[str, str] = {
        "架构图": "架构图不生成 Mermaid 源码；请保留 source=user 占位，提示用户自行生成或使用 GPT image 生图后补入。",
        "流程图": "请生成 PlantUML activity diagram，所有节点使用中文，判断分支连线明确标注 Y/N，全图只保留一个最终结束节点。",
        "E-R图": "E-R 图由 .thesis-config.yaml 的 er_modeling.graph_type 控制；默认使用 Graphviz DOT Chen 风格，事实源优先 references/prompt/background.md。",
        "用例图": "请生成 PlantUML 用例图，使用标准 UML 用例图规范，actor 使用中文，系统边界使用 rectangle 包裹。",
        "时序图": "请生成 PlantUML sequence 图，展示参与者交互顺序。",
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
        return f"""<!-- image-requirement
id: {chart_id}
title: {chart_name}
source=user
diagram_type=architecture
status=pending_user
description=架构图由用户自行生成；如需 AI 生成，请使用 GPT image 生图后作为用户图片补入。
-->"""

    def _flowchart(self, chart_id: str, chart_name: str) -> str:
        return f'''@startuml
' {chart_id} {chart_name}
skinparam shadowing false
skinparam defaultFontName Microsoft YaHei
start
:接收请求;
if (校验是否通过?) then (Y)
  :处理业务;
else (N)
  :返回错误;
endif
stop
@enduml'''

    def _usecase(self, chart_id: str, chart_name: str) -> str:
        return f'''@startuml
' {chart_id} {chart_name}
left to right direction
skinparam shadowing false
skinparam packageStyle rectangle
skinparam defaultFontName Microsoft YaHei
rectangle "系统" {{
  usecase "登录" as UC1
  usecase "查询数据" as UC2
  usecase "审核" as UC3
}}
actor "用户" as User
actor "管理员" as Admin
User --> UC1
User --> UC2
Admin --> UC3
@enduml'''

    def _sequence(self, chart_id: str, chart_name: str) -> str:
        return f'''@startuml
' {chart_id} {chart_name}
skinparam shadowing false
skinparam defaultFontName Microsoft YaHei
actor 用户 as U
participant 系统 as S
U -> S: 发起请求
S --> U: 返回结果
@enduml'''

    def _er(self, chart_id: str, chart_name: str) -> str:
        return f"""# {chart_id} {chart_name}
# E-R 图由 .thesis-config.yaml 的 er_modeling.graph_type 控制。
# 默认生成 Graphviz DOT Chen 风格：实体矩形、属性椭圆、联系菱形。
# 事实源优先读取 references/prompt/background.md。
# 请通过 scripts/charts/source_writer.py 生成或刷新正式 ER 源码。"""

    def _module(self, chart_id: str, chart_name: str) -> str:
        return f'''```mermaid
%% {chart_id} {chart_name}
graph TB
    A[核心模块] --> B[用户管理]
    A --> C[业务处理]
    A --> D[系统配置]
```'''
