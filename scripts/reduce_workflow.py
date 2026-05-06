#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文降重自动化流程脚本

整合以下流程：
1. 同义词替换
2. 生成大模型审核 Prompt
3. AIGC 检测
4. 输出报告

使用方法：
    python scripts/reduce_workflow.py --input workspace/final/论文终稿.md --output workspace/reduced/
"""

import os
import re
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional

try:
    from aigc.detect import AIGCDetector
except ImportError:
    AIGCDetector = None

CHAPTER_STRATEGIES = {
    "abstract": {
        "label": "摘要",
        "goal": "保持摘要三段逻辑和学术规范，做轻量去模板化处理。",
        "preferred": [
            "压缩模板化过渡词",
            "轻度句长波动",
            "精简冗余“的”字",
            "保持术语、目标、方法和结果表达稳定",
        ],
        "avoid": [
            "设问句",
            "过强主观表达",
            "明显微瑕疵模拟",
            "大幅重组摘要结构",
        ],
        "risk_note": "摘要篇幅短且结构固定，过度改写会先伤害学术性。",
    },
    "intro_review": {
        "label": "绪论/文献综述",
        "goal": "降低综述段落的模板味，同时保留综述体与引用规范。",
        "preferred": [
            "减少套话和排比",
            "有限的语气波动",
            "重点文献详述、次要文献略写",
            "适度变化引用句式",
        ],
        "avoid": [
            "强口语化",
            "过多成语",
            "脱离引用依据的主观判断",
            "整章大改",
        ],
        "risk_note": "绪论天然模板感较强，应优先修模板词，不要破坏综述体。",
    },
    "technical_foundation": {
        "label": "技术基础/关键技术",
        "goal": "保留术语准确性，用具体机制解释取代百科式空话。",
        "preferred": [
            "补入术语对应机制",
            "穿插长短句",
            "减少万能解释句",
            "保留技术名词一致性",
        ],
        "avoid": [
            "术语漂移过大",
            "成语化表达",
            "夸张结论",
            "无依据扩写",
        ],
        "risk_note": "该类章节依赖术语密度，错误替换术语会直接伤害可信度。",
    },
    "system_design": {
        "label": "系统设计",
        "goal": "让设计描述更像作者亲写，突出模块、表结构和架构细节。",
        "preferred": [
            "注入模块名和分层信息",
            "补入表名、字段或关系说明",
            "弱化空泛设计意义句",
            "适度句长波动",
        ],
        "avoid": [
            "泛泛而谈的优势总结",
            "过多成语",
            "口语式设问",
            "脱离设计事实的发挥",
        ],
        "risk_note": "系统设计章最适合补作者专属细节，优先写清结构而非堆修辞。",
    },
    "system_implementation": {
        "label": "系统实现",
        "goal": "突出实现路径、接口、流程与代码关联，减少教科书腔。",
        "preferred": [
            "注入接口路径或调用链",
            "补入关键实现步骤",
            "保留必要技术术语",
            "对高风险段落做局部重写",
        ],
        "avoid": [
            "整章同一节奏排比",
            "夸大“完整闭环”类表达",
            "无事实依据的性能评价",
            "口语化点评",
        ],
        "risk_note": "实现章更适合用细节破 AI 味，不适合靠花哨表达降分。",
    },
    "testing_analysis": {
        "label": "系统测试/实验分析",
        "goal": "优先保留实验条件、测试数据和结果解释，降低均匀叙述。",
        "preferred": [
            "写清测试条件或实验环境",
            "先给结果再解释原因",
            "保留数据与指标",
            "加入边界条件或局限说明",
        ],
        "avoid": [
            "删除数字证据",
            "把结果段改成空泛评价",
            "过强成语化",
            "统一句长",
        ],
        "risk_note": "测试分析章天然更像真人写作，关键是不要把数据改丢。",
    },
    "conclusion_outlook": {
        "label": "总结与展望",
        "goal": "弱化模板化总结口吻，保持结论克制，不追求激进降 AI。",
        "preferred": [
            "删除套话和重复结论",
            "适度段落合并",
            "保留局限与后续工作",
            "减少工整排比",
        ],
        "avoid": [
            "过强去 AI 操作",
            "大幅加入主观感叹",
            "设问句",
            "强行制造微瑕疵",
        ],
        "risk_note": "总结与展望本身就接近模板文体，过度改写通常得不偿失。",
    },
    "acknowledgement": {
        "label": "致谢",
        "goal": "保持真诚朴实，避免模板化感谢套话。",
        "preferred": [
            "压缩客套空话",
            "保留感谢对象顺序",
            "句式自然即可",
        ],
        "avoid": [
            "技术化表达",
            "设问句",
            "过度主观抒情",
            "机械排比",
        ],
        "risk_note": "致谢不是技术章节，重点是真诚与自然，不是激进降 AI。",
    },
    "generic": {
        "label": "通用章节",
        "goal": "在不破坏学术表达的前提下做通用去模板化处理。",
        "preferred": [
            "删除模板词",
            "适度句长波动",
            "保护术语",
            "优先局部修正高风险表达",
        ],
        "avoid": [
            "整章重写",
            "无依据扩写",
            "口语化",
            "过度成语化",
        ],
        "risk_note": "无法明确识别章节时，使用最保守的通用策略。",
    },
}

CHAPTER_TYPE_HINTS = [
    ("abstract", ["# 摘要", "摘要", "abstract"]),
    ("acknowledgement", ["致谢"]),
    ("conclusion_outlook", ["总结与展望", "结论与展望", "总结", "展望"]),
    ("system_design", ["系统设计", "概要设计", "详细设计", "架构设计", "数据库设计"]),
    ("system_implementation", ["系统实现", "功能实现", "模块实现", "实现过程"]),
    ("testing_analysis", ["系统测试", "测试分析", "实验分析", "性能测试", "测试结果"]),
    ("technical_foundation", ["关键技术", "技术基础", "理论基础", "相关技术"]),
    ("intro_review", ["绪论", "研究现状", "文献综述", "国内外研究现状"]),
]

CHAPTER_NUMBER_FALLBACKS = {
    "chapter_4": "system_design",
    "chapter-4": "system_design",
    "chapter_5": "system_implementation",
    "chapter-5": "system_implementation",
    "chapter_6": "testing_analysis",
    "chapter-6": "testing_analysis",
    "chapter_7": "conclusion_outlook",
    "chapter-7": "conclusion_outlook",
}

ENHANCED_SYNONYM_DICT = {
    # 高频名词
    "系统": ["平台", "体系", "架构", "框架", "整体", "应用平台"],
    "文档": ["资料", "文件", "素材", "文献", "文本材料"],
    "实现": ["完成", "达成", "落实", "构建", "实施", "开展"],
    "支持": ["支撑", "辅助", "配合", "保障", "提供服务"],
    "管理": ["管控", "治理", "运营", "统筹", "维护", "监管"],
    "功能": ["能力", "特性", "效用", "功用", "服务能力"],
    "技术": ["科技", "工艺", "技能", "手段", "方法"],
    "存储": ["保存", "存放", "保留", "记录", "持久化"],
    "通过": ["经由", "借助", "依靠", "利用", "采取", "运用"],
    "用户": ["使用者", "客户", "终端用户", "访问者", "操作人员"],
    "测试": ["检验", "验证", "考核", "测试验证", "实验", "评测"],
    "设计": ["构建", "开发", "规划", "制定", "架构设计"],
    "采用": ["使用", "运用", "应用", "选取", "采纳", "引入"],
    "问题": ["难题", "困境", "挑战", "议题", "课题", "疑问"],
    "包括": ["包含", "涵盖", "涉及", "囊括", "覆盖", "纳入"],
    "结果": ["成果", "产出", "结论", "成效", "效果"],
    "内容": ["信息内容", "文本内容", "资料内容", "数据内容"],
    "响应": ["回应", "反馈", "返回结果", "输出结果"],
    "进行": ["开展", "实施", "执行", "着手", "推进"],
    "服务": ["服务模块", "功能服务", "后台服务", "服务组件"],
    "企业": ["公司", "组织", "机构", "商业机构"],
    "生成": ["产生", "创建", "输出", "生成输出", "自动生成"],
    "能力": ["本领", "功能", "实力", "服务能力", "处理能力"],
    "处理": ["处置", "应对", "解决", "操作", "数据处理"],
    "需求": ["要求", "需要", "诉求", "期望", "业务需求"],
    "模块": ["组件", "功能模块", "服务模块", "子系统"],
    "应用": ["运用", "使用", "实践", "实际应用", "应用场景"],
    "提供": ["供给", "给予", "交付", "提供支持", "提供服务"],

    # 高频动词
    "提高": ["提升", "增强", "改善", "优化", "改进", "增进"],
    "降低": ["减少", "削减", "缩减", "下降", "减轻"],
    "增加": ["增添", "加大", "扩展", "提升"],
    "获取": ["取得", "获得", "采集", "收集", "提取"],
    "展示": ["呈现", "显示", "表现", "可视化展示"],
    "构建": ["搭建", "建立", "创建", "组建"],
    "集成": ["整合", "融合", "组合", "结合"],
    "优化": ["改进", "完善", "改良", "提升", "调优"],
    "分析": ["剖析", "研究", "探究", "考察", "解析"],
    "研究": ["探究", "分析", "考察", "调研", "深入研究"],
    "开发": ["构建", "实现", "设计", "编写", "开发实现"],

    # 高频形容词
    "重要": ["关键", "核心", "主要", "要紧", "至关重要"],
    "显著": ["明显", "突出", "可观", "引人注目"],
    "有效": ["有力", "高效", "可行", "实用"],
    "准确": ["精确", "精准", "正确", "无误"],
    "快速": ["迅速", "高效", "快捷", "高速"],
    "稳定": ["可靠", "稳固", "平稳", "健壮"],
    "灵活": ["机动", "弹性", "便捷", "自如"],
    "强大": ["强劲", "有力", "完备", "完善"],

    # 过渡词替换
    "此外": ["同时", "与之相伴", "另外"],
    "值得注意的是": ["需要关注的是", "值得关注的是", "应当说明的是"],
    "综上所述": ["总体而言", "概括来说", "总的来看"],
    "不可否认": ["必须承认", "诚然", "毋庸置疑"],

    # 学术用语
    "本文": ["本研究", "本论文", "笔者"],
    "本研究": ["本文", "本论文", "笔者"],
    "研究表明": ["研究显示", "研究发现", "调研结果揭示"],
}

# 默认术语白名单
DEFAULT_WHITELIST = {
    "检索", "向量", "知识库", "模型", "语义", "问答", "数据库", "接口",
    "语言", "量化", "架构", "框架", "组件", "模块", "服务", "缓存",
    "存储", "索引", "查询", "请求", "响应", "并发", "分布式",
    "深度学习", "机器学习", "神经网络", "自然语言处理", "文本挖掘",
    "特征工程", "训练", "推理", "预测", "分类", "聚类", "回归",
    "前端", "后端", "全栈", "微服务", "容器", "部署", "测试", "调试",
    "系统", "平台", "功能", "性能", "安全", "可靠", "可用", "扩展",
    "SpringBoot", "Spring", "PostgreSQL", "MySQL", "Redis", "MongoDB",
    "Elasticsearch", "Neo4j", "MinIO", "Docker", "Kubernetes",
    "BERT", "GPT", "LLM", "RAG", "API", "RESTful", "JSON", "SQL",
    "JWT", "RBAC", "OAuth", "HTTP", "HTTPS", "TCP", "IP",
}


def detect_chapter_type(input_path: str, text: str) -> str:
    """根据文件名、标题和关键词识别章节类型"""
    path_name = Path(input_path).name.lower()
    input_name = Path(input_path).name
    text_head = text[:1200]

    if "摘要" in input_name or path_name == "abstract.md":
        return "abstract"
    if "致谢" in input_name:
        return "acknowledgement"

    for chapter_type, hints in CHAPTER_TYPE_HINTS:
        for hint in hints:
            if hint.lower() in text_head.lower() or hint in input_name:
                return chapter_type

    for key, chapter_type in CHAPTER_NUMBER_FALLBACKS.items():
        if key in path_name:
            return chapter_type

    return "generic"


def get_chapter_strategy(chapter_type: str) -> Dict[str, object]:
    """返回章节策略定义"""
    return CHAPTER_STRATEGIES.get(chapter_type, CHAPTER_STRATEGIES["generic"])


CLAUSE_MARKER_PATTERN = re.compile(r"[（(]\s*\d+\s*[）)]")


def normalize_clause_marker(marker: str) -> str:
    number = re.search(r"\d+", marker)
    return f"（{number.group(0)}）" if number else marker


def extract_clause_markers(text: str) -> List[str]:
    markers = []
    for match in CLAUSE_MARKER_PATTERN.finditer(text):
        marker = normalize_clause_marker(match.group(0))
        if marker not in markers:
            markers.append(marker)
    return markers


def build_clause_preservation_summary(original_text: str, processed_text: str) -> Dict[str, object]:
    before = extract_clause_markers(original_text)
    after = extract_clause_markers(processed_text)
    missing = [marker for marker in before if marker not in after]
    kept = [marker for marker in before if marker in after]
    status = "通过" if not missing else "未通过"
    return {
        "status": status,
        "total_before": len(before),
        "total_after": len(after),
        "kept": kept,
        "missing": missing,
    }


def _metric_score(result: Dict[str, object], key: str) -> float:
    value = result.get(key, {})
    if isinstance(value, dict):
        return float(value.get("score", 0) or 0)
    return 0.0


def _score_delta(before: float, after: float) -> float:
    return round(after - before, 1)


def _format_paragraphs(paragraphs: object) -> str:
    if not paragraphs:
        return "无"
    return "、".join(f"第 {item} 段" for item in paragraphs)


def _format_markers(markers: List[str]) -> str:
    return "、".join(markers) if markers else "无"


def build_aigc_comparison_report(
    before_result: Dict[str, object],
    after_result: Dict[str, object],
    clause_summary: Dict[str, object],
    input_path: str,
    output_path: str,
) -> str:
    before_overall = float(before_result.get("overall_score", 0) or 0)
    after_overall = float(after_result.get("overall_score", 0) or 0)

    rows = [
        ("整体 AIGC 检测率", before_overall, after_overall),
        ("句长波动风险", _metric_score(before_result, "burstiness"), _metric_score(after_result, "burstiness")),
        ("词汇多样性风险", _metric_score(before_result, "vocabulary"), _metric_score(after_result, "vocabulary")),
        ("过渡词风险", _metric_score(before_result, "transition"), _metric_score(after_result, "transition")),
        ("结构模式风险", _metric_score(before_result, "structure"), _metric_score(after_result, "structure")),
    ]

    report = f'''# AIGC 降低前后量化对比报告

## 1. 基本信息

- 输入文件：`{input_path}`
- 改写后文件：`{output_path}`
- 检测时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 2. 总体对比

| 指标 | 改写前 | 改写后 | 变化 |
|---|---:|---:|---:|
'''
    for label, before, after in rows:
        report += f"| {label} | {before:.1f} | {after:.1f} | {_score_delta(before, after):+.1f} |\n"

    before_high_risk = before_result.get("high_risk_paragraphs", [])
    after_high_risk = after_result.get("high_risk_paragraphs", [])
    template_check = after_result.get("rewrite_self_check", {}).get("template_words", {})
    clause_status = clause_summary.get("status", "需人工确认")
    clause_total_before = clause_summary.get("total_before", 0)
    clause_total_after = clause_summary.get("total_after", 0)
    clause_kept = clause_summary.get("kept", [])
    clause_missing = clause_summary.get("missing", [])

    report += f'''
## 3. 高风险段落变化

- 改写前：{_format_paragraphs(before_high_risk)}
- 改写后：{_format_paragraphs(after_high_risk)}
- 仍需处理：{_format_paragraphs(after_high_risk)}

## 4. 条款保留检查

- 检查状态：{clause_status}
- 原文条款数：{clause_total_before}
- 改写后条款数：{clause_total_after}
- 已保留条款：{_format_markers(clause_kept)}
- 缺失条款：{_format_markers(clause_missing)}

## 5. 处理完成自检

| 检查项 | 状态 | 说明 |
|---|---|---|
| 语义与术语未改变 | 需人工确认 | 本地脚本无法判断语义是否完全一致 |
| 条款编号与顺序保留 | {clause_status} | 缺失条款：{_format_markers(clause_missing)} |
| 模板词已压缩 | {"通过" if template_check.get("status") == "pass" else "需人工确认"} | {template_check.get("detail", "未获取模板词检查结果")} |
| 显性转接词减少 | 需人工确认 | 需人工核对“因此、同时、此外、从而”等是否已压缩 |
| 原句骨架已重组 | 需人工确认 | 需人工核对是否避免只做同义替换 |
| 长短句有变化 | 需人工确认 | 参考句长波动风险变化 |
| 场景或系统细节充足 | 需人工确认 | 需人工核对是否补入真实功能、权限、流程、日志或参数等细节 |
| 未新增虚构信息 | 需人工确认 | 需要人工核对是否加入原文没有的功能、接口、表、指标或文献 |
| 学术语体稳定 | 需人工确认 | 需要人工核对是否未口语化、宣传化或过度成语化 |
| 量化报告已生成 | 通过 | 已生成本报告 |

## 6. 结论

本报告基于本地 AIGC 辅助检测结果生成，只用于定位模板化表达、句式均匀和条款保留问题，不代表任何第三方检测工具结论。最终文本仍需人工审校。
'''
    return report


def detect_aigc_for_report(text: str) -> Dict[str, object]:
    if AIGCDetector is None:
        return {"overall_score": 0, "error": "AIGCDetector 不可用"}
    detector = AIGCDetector(mode="lite")
    return detector.detect(text)


class PaperReducer:
    """论文降重处理器"""

    def __init__(self, whitelist: Set[str] = None, ratio: float = 0.5):
        """__init__"""
        self.whitelist = whitelist or DEFAULT_WHITELIST
        self.ratio = ratio
        self.replacements = []
        self.replacement_stats = {}

    def replace_text(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """执行同义词替换"""
        result = text
        self.replacements = []
        self.replacement_stats = {}
        placeholder_replacements = {}

        # 按长度排序，优先替换长短语
        sorted_synonyms = sorted(ENHANCED_SYNONYM_DICT.items(), key=lambda x: len(x[0]), reverse=True)

        for original, synonyms_list in sorted_synonyms:
            if original in self.whitelist:
                continue

            pattern = re.compile(re.escape(original))
            matches = list(pattern.finditer(result))

            if not matches:
                continue

            num_to_replace = max(1, int(len(matches) * self.ratio))
            selected_matches = random.sample(matches, min(num_to_replace, len(matches)))

            for match_index, match in enumerate(reversed(selected_matches)):
                replacement = random.choice(synonyms_list)
                placeholder = f"__REPLACE_{len(self.replacements) + match_index}__"
                result = result[:match.start()] + placeholder + result[match.end():]
                placeholder_replacements[placeholder] = replacement
                self.replacements.append((original, replacement))

                # 统计
                if original not in self.replacement_stats:
                    self.replacement_stats[original] = {"count": 0, "replacements": []}
                self.replacement_stats[original]["count"] += 1
                self.replacement_stats[original]["replacements"].append(replacement)

        for placeholder, replacement in placeholder_replacements.items():
            result = result.replace(placeholder, replacement)

        return result, self.replacements

    def generate_review_prompt(
        self,
        original_text: str,
        replaced_text: str,
        output_path: str,
        chapter_type: str,
        strategy: Dict[str, object],
    ) -> str:
        """生成大模型审核 Prompt"""

        chapter_label = strategy["label"]
        preferred = strategy["preferred"]
        avoid = strategy["avoid"]

        prompt = f'''你是一位资深的学术论文编辑，请对以下同义词替换后的论文进行审核和优化。

## 任务背景

我使用自动化工具对论文进行了初步同义词替换，目的是发现机械替换、术语漂移和表达不自然的问题。请以学术表达质量和语义准确性为目标，审核替换结果是否合理。

## 软件工程方向毕业论文风格要求

- 在保证语义不变的前提下进行重写，而不是简单同义替换
- 避免大量使用“系统应……从而……”这类标准答案式句式
- 控制句式多样性，使文本符合软件工程方向毕业论文的客观表述习惯
- 适当保留自然表达，避免过度压缩造成表达生硬
- 删除口语化、评价性或解释性表达，改为客观陈述
- 不引入额外技术术语或扩展内容
- 保持论文表达严谨，不使用过度口语化或夸张化表述

## AIGC 降低核心流程

处理前必须先给出简短计划：
1. 段落类型判断：需求分析、系统设计、系统实现、系统测试、摘要或其他。
2. 原文结构识别：是否包含（1）（2）（3）（4）等条款编号。
3. 高风险点判断：模板句、重复主语、句长均匀、显性转接词、原句骨架残留。
4. 本轮处理策略：场景化重写、结构重组、细节注入、语言去模板化的具体动作。
5. 预期输出：改写文本、清单自检；有脚本输入时再补量化对比报告。

处理时必须遵守：
- 按“场景化重写 → 结构重组 → 细节注入 → 语言去模板化”的顺序处理，不先做机械同义替换。
- 原文存在条款编号时，保留原编号、标题和顺序。
- 不删除、不合并原功能项，除非用户明确要求。
- 100% 疑似条款优先局部深改，不牵连整章。
- 减少“系统提供、系统支持、管理员可以、从而、确保”等模板链条。
- 减少“因此、同时、此外、从而”等显性转接词，用句间语义承接、场景推进或对象切换替代。
- 不新增原文没有的接口、数据库表、实验指标、参考文献或系统能力。

## 章节识别

- 识别章节类型：{chapter_type}
- 章节标签：{chapter_label}
- 本章目标：{strategy["goal"]}
- 风险提示：{strategy["risk_note"]}

### 本章优先策略
'''
        for item in preferred:
            prompt += f'- {item}\n'

        prompt += '\n### 本章禁用策略\n'
        for item in avoid:
            prompt += f'- {item}\n'

        prompt += f'''

## 替换统计

- 总替换数：{len(self.replacements)} 处
- 涉及词汇：{len(self.replacement_stats)} 个不同词汇

### 替换分布（前20个高频词）

'''
        # 添加替换统计
        sorted_stats = sorted(self.replacement_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        for word, stats in sorted_stats[:20]:
            prompt += f'- "{word}" 被替换 {stats["count"]} 次，替换为：{", ".join(set(stats["replacements"][:5]))}\n'

        prompt += f'''
## 术语白名单（以下术语不应被替换）

```
{", ".join(sorted(self.whitelist))}
```

## 审核要求

### 1. 术语保护检查
- 检查白名单中的术语是否被误替换
- 如发现误替换，请标注并建议恢复

### 2. 表达自然性检查
- 替换后的表达是否符合学术规范？
- 是否存在生硬或不自然的表达？
- 是否违反本章禁用策略？

### 3. 语义一致性检查
- 核心观点是否保持不变？
- 论述逻辑是否通顺？
- 是否因为机械替换削弱了本章应保留的学术表达？

### 4. 改写范围控制
- 优先标记高风险表达、模板化过渡词和明显不自然句子
- 优先局部修正，不要整章重写
- 摘要、总结与展望、致谢等高保守章节，必须避免激进改写

## 输出格式

请输出以下内容：

### AIGC 降低处理计划

### 改写后文本

### 处理完成自检

| 检查项 | 状态 | 说明 |
|---|---|---|
| 语义与术语未改变 | 通过/需人工确认/未通过 | ... |
| 条款编号与顺序保留 | 通过/不适用/未通过 | ... |
| 模板词已压缩 | 通过/需人工确认/未通过 | ... |
| 显性转接词减少 | 通过/需人工确认/未通过 | ... |
| 原句骨架已重组 | 通过/需人工确认/未通过 | ... |
| 长短句有变化 | 通过/需人工确认/未通过 | ... |
| 场景或系统细节充足 | 通过/需人工确认/未通过 | ... |
| 未新增虚构信息 | 通过/需人工确认/未通过 | ... |
| 学术语体稳定 | 通过/需人工确认/未通过 | ... |
| 量化报告已生成 | 通过/不适用/未通过 | ... |

### 问题报告

| 序号 | 位置/原文 | 问题类型 | 具体问题 | 修改建议 |
|------|----------|---------|---------|---------|
| 1 | ... | 术语误替换 | ... | ... |

### 统计信息

- 术语误替换数量：X 处
- 表达优化建议：X 处
- 其他问题：X 处

---

**注意**：由于论文篇幅较长，请重点关注替换频率最高的词汇，并优先处理本章高风险表达而非整章重写。
'''

        # 保存 Prompt
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

        return prompt


def run_workflow(input_path: str, output_dir: str, ratio: float = 0.5, whitelist_path: str = None):
    """运行完整降重流程"""

    # 创建输出目录
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_stem = Path(input_path).stem
    safe_input_stem = re.sub(r'[^\w\-一-鿿]+', '_', input_stem).strip('_') or 'input'

    # 时间戳（精确到微秒，避免批量调用时同秒覆盖）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_token = f"{safe_input_stem}_{timestamp}"

    # 加载白名单
    whitelist = set(DEFAULT_WHITELIST)
    if whitelist_path and Path(whitelist_path).exists():
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            for line in f:
                term = line.strip()
                if term and not term.startswith('#'):
                    whitelist.add(term)

    # 读取原文
    with open(input_path, 'r', encoding='utf-8') as f:
        original_text = f.read()

    chapter_type = detect_chapter_type(input_path, original_text)
    strategy = get_chapter_strategy(chapter_type)

    print(f"原始论文长度: {len(original_text)} 字符")
    print(f"替换比例: {ratio * 100}%")
    print(f"术语白名单: {len(whitelist)} 个")
    print(f"章节类型: {strategy['label']} ({chapter_type})")

    # 执行替换
    reducer = PaperReducer(whitelist=whitelist, ratio=ratio)
    replaced_text, replacements = reducer.replace_text(original_text)

    print(f"替换数量: {len(replacements)} 处")

    # 保存替换后论文
    output_paper = output_dir / f"论文降重版_{output_token}.md"
    with open(output_paper, 'w', encoding='utf-8') as f:
        f.write(replaced_text)
    print(f"替换后论文: {output_paper}")

    # 生成审核 Prompt
    prompt_path = output_dir / f"审核Prompt_{output_token}.md"
    reducer.generate_review_prompt(
        original_text,
        replaced_text,
        str(prompt_path),
        chapter_type,
        strategy,
    )
    print(f"审核 Prompt: {prompt_path}")

    # 保存替换记录
    record_path = output_dir / f"替换记录_{output_token}.json"
    record_data = {
        "timestamp": timestamp,
        "input_file": input_path,
        "output_file": str(output_paper),
        "chapter_type": chapter_type,
        "chapter_label": strategy["label"],
        "chapter_goal": strategy["goal"],
        "total_replacements": len(replacements),
        "replacement_stats": {k: v["count"] for k, v in reducer.replacement_stats.items()},
        "replacements": [{"original": o, "replacement": r} for o, r in replacements[:100]]
    }
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False, indent=2)
    print(f"替换记录: {record_path}")

    before_aigc = detect_aigc_for_report(original_text)
    after_aigc = detect_aigc_for_report(replaced_text)
    clause_summary = build_clause_preservation_summary(original_text, replaced_text)

    comparison_report_path = output_dir / f"AIGC降低量化对比_{output_token}.md"
    comparison_report = build_aigc_comparison_report(
        before_aigc,
        after_aigc,
        clause_summary,
        input_path,
        str(output_paper),
    )
    with open(comparison_report_path, "w", encoding="utf-8") as f:
        f.write(comparison_report)

    print("\nAIGC 降低量化摘要:")
    print(f"  改写前整体分数: {before_aigc.get('overall_score', 0)}")
    print(f"  改写后整体分数: {after_aigc.get('overall_score', 0)}")
    print(f"  条款保留检查: {clause_summary['status']}")
    print(f"  对比报告: {comparison_report_path}")

    # 生成报告
    report_path = output_dir / f"降重报告_{output_token}.md"
    report = f'''# 论文降重报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 基本信息

| 项目 | 值 |
|------|-----|
| 原始文件 | {input_path} |
| 输出文件 | {output_paper} |
| 原文字数 | {len(original_text)} |
| 替换比例 | {ratio * 100}% |
| 替换数量 | {len(replacements)} 处 |
| 涉及词汇 | {len(reducer.replacement_stats)} 个 |
| 章节类型 | {chapter_type} |
| 章节标签 | {strategy['label']} |

## 本章策略

- **目标**：{strategy['goal']}
- **风险提示**：{strategy['risk_note']}

### 优先策略
'''
    for item in strategy["preferred"]:
        report += f'- {item}\n'

    report += '\n### 禁用策略\n'
    for item in strategy["avoid"]:
        report += f'- {item}\n'

    report += '''

## 替换分布

| 原词 | 替换次数 | 替换为 |
|------|---------|--------|
'''
    sorted_stats = sorted(reducer.replacement_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    for word, stats in sorted_stats[:20]:
        unique_replacements = list(set(stats["replacements"]))[:3]
        report += f'| {word} | {stats["count"]} | {", ".join(unique_replacements)} |\n'

    report += f'''
## 后续步骤

1. **大模型审核**: 使用生成的 Prompt 让大模型审核替换结果
   - Prompt 文件: `{prompt_path}`
   - 审核时应优先处理高风险表达，不建议整章重写

2. **人工检查**: 重点检查以下内容
   - 专业术语是否被误替换
   - 表达是否通顺自然
   - 核心观点是否保持不变
   - 是否违反本章禁用策略

3. **AIGC 检测**: 先用通用检测脚本定位高风险段落，再按需补做技术论文检测
   ```bash
   python scripts/aigc/detect.py --input {output_paper}
   python scripts/aigc/technical_detect.py --input {output_paper}
   ```

## 文件清单

| 文件 | 路径 |
|------|------|
| 降重后论文 | {output_paper} |
| 审核Prompt | {prompt_path} |
| 替换记录 | {record_path} |
| AIGC量化对比报告 | {comparison_report_path} |
| 本报告 | {report_path} |
'''

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"降重报告: {report_path}")

    return {
        "output_paper": str(output_paper),
        "prompt_path": str(prompt_path),
        "record_path": str(record_path),
        "report_path": str(report_path),
        "comparison_report_path": str(comparison_report_path),
        "total_replacements": len(replacements),
        "chapter_type": chapter_type,
        "chapter_label": strategy["label"],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='论文降重自动化流程')
    parser.add_argument('--input', '-i', required=True, help='输入文件路径')
    parser.add_argument('--output', '-o', default='workspace/reduced/', help='输出目录')
    parser.add_argument('--ratio', '-r', type=float, default=0.5, help='替换比例（0-1）')
    parser.add_argument('--whitelist', '-w', default='scripts/aigc/term_whitelist.txt', help='术语白名单文件')

    args = parser.parse_args()

    result = run_workflow(args.input, args.output, args.ratio, args.whitelist)

    print("\n" + "=" * 50)
    print("降重流程完成！")
    print("=" * 50)
    print(f"输出文件: {result['output_paper']}")
    print(f"审核Prompt: {result['prompt_path']}")
    print(f"替换数量: {result['total_replacements']} 处")
