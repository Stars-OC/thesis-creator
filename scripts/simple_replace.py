#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的中文同义词替换工具 - 不依赖synonyms库
"""

import re
import random
from pathlib import Path

# 同义词词典
SYNONYM_DICT = {
    # 常用动词
    "实现": ["完成", "达成", "落实", "构建"],
    "采用": ["使用", "运用", "应用", "选取"],
    "提出": ["给出", "设计", "构建", "开发"],
    "分析": ["剖析", "研究", "探究", "考察"],
    "设计": ["构建", "开发", "规划", "制定"],
    "开发": ["构建", "实现", "设计", "编写"],
    "研究": ["探究", "分析", "考察", "调研"],
    "提高": ["提升", "增强", "改善", "优化"],
    "降低": ["减少", "削减", "缩减", "下降"],
    "增加": ["增添", "加大", "扩展", "提升"],
    "支持": ["支撑", "辅助", "配合", "保障"],
    "处理": ["处置", "应对", "解决", "操作"],
    "获取": ["取得", "获得", "采集", "收集"],
    "存储": ["保存", "存放", "保留", "记录"],
    "展示": ["呈现", "显示", "表现", "呈现"],
    "构建": ["搭建", "建立", "创建", "组建"],
    "集成": ["整合", "融合", "组合", "结合"],
    "优化": ["改进", "完善", "改良", "提升"],

    # 常用形容词
    "重要": ["关键", "核心", "主要", "要紧"],
    "显著": ["明显", "突出", "可观", "引人注目"],
    "有效": ["有力", "高效", "可行", "实用"],
    "准确": ["精确", "精准", "正确", "无误"],
    "快速": ["迅速", "高效", "快捷", "高速"],
    "稳定": ["可靠", "稳固", "平稳", "健壮"],
    "灵活": ["机动", "弹性", "便捷", "自如"],
    "强大": ["强劲", "有力", "完备", "完善"],

    # 常用名词
    "问题": ["难题", "困境", "挑战", "议题"],
    "方法": ["方式", "途径", "手段", "路径"],
    "结果": ["成果", "产出", "结论", "成效"],
    "影响": ["作用", "效应", "冲击", "波及"],
    "发展": ["进步", "演进", "成长", "推进"],
    "技术": ["科技", "工艺", "技能", "手段"],
    "系统": ["平台", "体系", "架构", "框架"],
    "功能": ["能力", "特性", "效用", "功用"],
    "数据": ["资料", "信息", "素材", "材料"],
    "用户": ["使用者", "客户", "终端用户", "访问者"],
    "需求": ["要求", "需要", "诉求", "期望"],
    "性能": ["效能", "表现", "能力", "效率"],

    # 常用短语
    "具有重要意义": ["意义重大", "作用显著", "价值突出", "地位关键"],
    "随着技术的发展": ["在技术进步的推动下", "伴随技术革新", "技术演进过程中"],
    "对...进行了研究": ["针对...开展了探究", "围绕...实施了调研"],
    "取得了显著成效": ["收获了可观成果", "达成了预期目标", "获得了良好效果"],
    "在一定程度上": ["某种意义上", "就部分而言", "从某种程度上"],
    "由此可见": ["这意味着", "这说明", "不难看出", "据此可知"],
    "与此同时": ["同期", "同一时间", "在此期间", "同时"],
    "起到了重要作用": ["发挥了关键效能", "具有举足轻重的地位", "承担了核心职责"],
    "从...角度来看": ["基于...视角", "站在...立场", "就...而言"],
    "在...背景下": ["基于...的环境", "处于...形势下", "面对...局势"],

    # 过渡词替换
    "此外": ["同时", "与之相伴", "另外"],
    "值得注意的是": ["需要关注的是", "值得关注的是", "应当说明的是"],
    "综上所述": ["总体而言", "概括来说", "总的来看"],
    "不可否认": ["必须承认", "诚然", "毋庸置疑"],
    "由此可见": ["这说明", "这意味着", "不难看出"],

    # 学术用语
    "本文": ["本研究", "本论文", "笔者"],
    "本研究": ["本文", "本论文", "笔者"],
    "研究表明": ["研究显示", "研究发现", "调研结果揭示"],
    "实践证明": ["实践表明", "事实证明", "实例显示"],
    "综上所述": ["总体而言", "概括来说", "总结以上"],
}

# 术语白名单 - 不替换的专业术语
TERM_WHITELIST = {
    "SpringBoot", "Spring", "Java", "React", "TypeScript", "JavaScript",
    "PostgreSQL", "MySQL", "Redis", "MongoDB", "Elasticsearch", "Neo4j", "MinIO",
    "BERT", "GPT", "LLM", "RAG", "API", "RESTful", "JSON", "XML", "SQL",
    "JWT", "RBAC", "OAuth", "HTTP", "HTTPS", "TCP", "IP",
    "Docker", "Kubernetes", "Linux", "Windows", "Ubuntu",
    "Maven", "Gradle", "npm", "yarn",
    "JMeter", "Postman", "Git", "GitHub",
    "AI", "人工智能", "大语言模型", "知识图谱", "向量检索", "语义检索",
    "检索增强生成", "文本向量化", "深度学习", "机器学习",
    "微服务", "分布式", "缓存", "数据库", "中间件",
    "前端", "后端", "全栈", "框架", "架构",
}


def load_whitelist(path: str) -> set:
    """加载术语白名单"""
    whitelist = set(TERM_WHITELIST)
    if path and Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                term = line.strip()
                if term and not term.startswith('#'):
                    whitelist.add(term)
    return whitelist


def is_protected(word: str, whitelist: set) -> bool:
    """检查词汇是否受保护"""
    # 检查是否在白名单中
    if word in whitelist:
        return True
    # 检查是否包含英文
    if re.search(r'[a-zA-Z]', word):
        return True
    # 检查是否是数字
    if word.isdigit():
        return True
    return False


def replace_synonyms(text: str, whitelist: set, ratio: float = 0.3) -> tuple:
    """执行同义词替换"""
    replacements = []
    result = text

    # 按长度排序，优先替换长短语
    sorted_synonyms = sorted(SYNONYM_DICT.items(), key=lambda x: len(x[0]), reverse=True)

    for original, synonyms_list in sorted_synonyms:
        if original in whitelist:
            continue

        # 查找所有匹配
        pattern = re.compile(re.escape(original))
        matches = list(pattern.finditer(result))

        if not matches:
            continue

        # 随机选择部分进行替换
        num_to_replace = max(1, int(len(matches) * ratio))
        selected_matches = random.sample(matches, min(num_to_replace, len(matches)))

        # 从后向前替换，避免位置偏移
        for match in reversed(selected_matches):
            replacement = random.choice(synonyms_list)
            result = result[:match.start()] + replacement + result[match.end():]
            replacements.append((original, replacement))

    return result, replacements


def process_file(input_path: str, output_path: str, whitelist_path: str = None, ratio: float = 0.3):
    """处理文件"""
    # 加载白名单
    whitelist = load_whitelist(whitelist_path)

    # 读取文件
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"原文长度: {len(text)} 字符")

    # 执行替换
    result, replacements = replace_synonyms(text, whitelist, ratio)

    # 保存结果
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"替换数量: {len(replacements)} 处")
    print(f"结果已保存到: {output_path}")

    # 显示部分替换记录
    if replacements:
        print("\n替换示例 (前20条):")
        for old, new in replacements[:20]:
            print(f"  {old} -> {new}")

    return result, replacements


if __name__ == '__main__':
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "workspace/final/论文终稿.md"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "workspace/reduced/论文降重版.md"
    whitelist_file = sys.argv[3] if len(sys.argv) > 3 else "scripts/term_whitelist.txt"
    ratio = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35

    process_file(input_file, output_file, whitelist_file, ratio)