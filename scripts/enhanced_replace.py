#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版中文同义词替换工具
针对论文高频词进行优化，提高词汇多样性
"""

import re
import random
from pathlib import Path
from collections import defaultdict

# 增强版同义词词典
ENHANCED_SYNONYM_DICT = {
    # ===== 高频名词（出现30次以上）=====
    "系统": ["平台", "体系", "架构", "框架", "整体", "应用平台", "软件系统"],
    "文档": ["资料", "文件", "素材", "文献", "文本材料", "电子文档"],
    "实现": ["完成", "达成", "落实", "构建", "实施", "开展", "具体实现"],
    "支持": ["支撑", "辅助", "配合", "保障", "提供服务", "提供帮助", "技术支持"],
    "管理": ["管控", "治理", "运营", "统筹", "维护", "监管", "管理功能"],
    "功能": ["能力", "特性", "效用", "功用", "服务能力", "业务功能", "核心功能"],
    "技术": ["科技", "工艺", "技能", "手段", "方法", "技术方案", "技术手段"],
    "存储": ["保存", "存放", "保留", "记录", "持久化", "数据保存", "信息存储"],
    "通过": ["经由", "借助", "依靠", "利用", "采取", "运用", "借助方式"],
    "用户": ["使用者", "客户", "终端用户", "访问者", "操作人员", "系统用户"],
    "测试": ["检验", "验证", "考核", "测试验证", "实验", "评测", "功能测试"],
    "设计": ["构建", "开发", "规划", "制定", "架构设计", "方案设计", "系统设计"],
    "采用": ["使用", "运用", "应用", "选取", "采纳", "引入", "选用"],
    "问题": ["难题", "困境", "挑战", "议题", "课题", "疑问", "技术问题"],
    "基于": ["建立在...基础上", "以...为基础", "依托", "立足于", "基于技术"],
    "包括": ["包含", "涵盖", "涉及", "囊括", "覆盖", "纳入", "主要包括"],
    "架构": ["系统架构", "技术架构", "整体架构", "体系结构", "框架结构", "系统框架"],
    "结果": ["成果", "产出", "结论", "成效", "效果", "运行结果", "处理结果"],
    "内容": ["信息内容", "文本内容", "资料内容", "数据内容", "文档内容"],
    "响应": ["回应", "反馈", "返回结果", "输出结果", "系统响应"],
    "进行": ["开展", "实施", "执行", "着手", "推进", "具体进行"],
    "服务": ["服务模块", "功能服务", "后台服务", "服务组件", "服务功能"],
    "企业": ["公司", "组织", "机构", "商业机构", "企业用户", "企业客户"],
    "生成": ["产生", "创建", "输出", "生成输出", "自动生成", "智能生成"],
    "能力": ["本领", "功能", "实力", "服务能力", "处理能力", "系统能力"],
    "处理": ["处置", "应对", "解决", "操作", "数据处理", "信息处理", "智能处理"],
    "需求": ["要求", "需要", "诉求", "期望", "业务需求", "功能需求", "用户需求"],
    "模块": ["组件", "功能模块", "服务模块", "子系统", "核心模块"],
    "应用": ["运用", "使用", "实践", "实际应用", "应用场景", "应用系统"],
    "提供": ["供给", "给予", "交付", "提供支持", "提供服务", "功能提供"],

    # ===== 高频动词 =====
    "提高": ["提升", "增强", "改善", "优化", "改进", "增进", "有效提升"],
    "降低": ["减少", "削减", "缩减", "下降", "减轻", "有效降低"],
    "增加": ["增添", "加大", "扩展", "提升", "增加", "有效增加"],
    "获取": ["取得", "获得", "采集", "收集", "提取", "抓取", "数据获取"],
    "展示": ["呈现", "显示", "表现", "展示输出", "可视化展示", "结果展示"],
    "构建": ["搭建", "建立", "创建", "组建", "构建实现", "系统构建"],
    "集成": ["整合", "融合", "组合", "结合", "系统集成", "功能集成"],
    "优化": ["改进", "完善", "改良", "提升", "调优", "性能优化"],
    "分析": ["剖析", "研究", "探究", "考察", "解析", "分析处理", "数据分析"],
    "研究": ["探究", "分析", "考察", "调研", "深入研究", "课题研究"],
    "开发": ["构建", "实现", "设计", "编写", "开发实现", "系统开发"],

    # ===== 高频形容词 =====
    "重要": ["关键", "核心", "主要", "要紧", "至关重要", "关键性"],
    "显著": ["明显", "突出", "可观", "引人注目", "显著性", "显著提升"],
    "有效": ["有力", "高效", "可行", "实用", "有效性", "有效实现"],
    "准确": ["精确", "精准", "正确", "无误", "准确性", "高精度"],
    "快速": ["迅速", "高效", "快捷", "高速", "快速响应", "高效快速"],
    "稳定": ["可靠", "稳固", "平稳", "健壮", "稳定性", "高可靠"],
    "灵活": ["机动", "弹性", "便捷", "自如", "灵活性", "高灵活"],
    "强大": ["强劲", "有力", "完备", "完善", "功能强大", "性能强劲"],

    # ===== 高频短语 =====
    "具有重要意义": ["意义重大", "作用显著", "价值突出", "地位关键"],
    "随着技术的发展": ["在技术进步的推动下", "伴随技术革新", "技术演进过程中"],
    "取得了显著成效": ["收获了可观成果", "达成了预期目标", "获得了良好效果"],
    "在一定程度上": ["某种意义上", "就部分而言", "从某种程度上"],
    "由此可见": ["这意味着", "这说明", "不难看出", "据此可知"],
    "与此同时": ["同期", "同一时间", "在此期间", "同时"],
    "起到了重要作用": ["发挥了关键效能", "具有举足轻重的地位", "承担了核心职责"],

    # ===== 过渡词替换 =====
    "此外": ["同时", "与之相伴", "另外", "除此之外"],
    "值得注意的是": ["需要关注的是", "值得关注的是", "应当说明的是"],
    "综上所述": ["总体而言", "概括来说", "总的来看", "总结以上"],
    "不可否认": ["必须承认", "诚然", "毋庸置疑"],

    # ===== 学术用语 =====
    "本文": ["本研究", "本论文", "笔者"],
    "本研究": ["本文", "本论文", "笔者"],
    "研究表明": ["研究显示", "研究发现", "调研结果揭示"],
    "实践证明": ["实践表明", "事实证明", "实例显示"],
}

# 术语白名单 - 不替换的专业术语
TERM_WHITELIST = {
    # 技术术语
    "SpringBoot", "Spring", "Java", "React", "TypeScript", "JavaScript",
    "PostgreSQL", "MySQL", "Redis", "MongoDB", "Elasticsearch", "Neo4j", "MinIO",
    "BERT", "GPT", "LLM", "RAG", "API", "RESTful", "JSON", "XML", "SQL",
    "JWT", "RBAC", "OAuth", "HTTP", "HTTPS", "TCP", "IP",
    "Docker", "Kubernetes", "Linux", "Windows", "Ubuntu",
    "Maven", "Gradle", "npm", "yarn",
    "JMeter", "Postman", "Git", "GitHub",

    # 中文术语（不应替换）
    "检索", "向量", "知识库", "模型", "语义", "问答", "数据库",
    "接口", "语言", "量化", "相似", "上传", "智能",
    "人工智能", "大语言模型", "知识图谱", "向量检索", "语义检索",
    "检索增强生成", "文本向量化", "深度学习", "机器学习",
    "微服务", "分布式", "缓存", "数据库", "中间件",
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
    if word in whitelist:
        return True
    if re.search(r'[a-zA-Z]', word):
        return True
    if word.isdigit():
        return True
    return False


class EnhancedSynonymReplacer:
    """增强版同义词替换器"""

    def __init__(self, whitelist: set, ratio: float = 0.5):
        self.whitelist = whitelist
        self.ratio = ratio
        self.replacement_history = defaultdict(list)  # 记录每个词的替换历史
        self.total_replacements = 0

    def get_unique_replacement(self, original: str, synonyms: list) -> str:
        """获取一个未使用过的同义词（增加多样性）"""
        available = [s for s in synonyms if s not in self.replacement_history[original]]

        if not available:
            # 如果所有同义词都用过了，随机选择一个
            available = synonyms

        chosen = random.choice(available)
        self.replacement_history[original].append(chosen)
        return chosen

    def replace_text(self, text: str) -> tuple:
        """执行同义词替换"""
        result = text
        replacements = []

        # 按长度排序，优先替换长短语
        sorted_synonyms = sorted(ENHANCED_SYNONYM_DICT.items(), key=lambda x: len(x[0]), reverse=True)

        for original, synonyms_list in sorted_synonyms:
            if original in self.whitelist:
                continue

            # 查找所有匹配
            pattern = re.compile(re.escape(original))
            matches = list(pattern.finditer(result))

            if not matches:
                continue

            # 随机选择部分进行替换
            num_to_replace = max(1, int(len(matches) * self.ratio))
            selected_matches = random.sample(matches, min(num_to_replace, len(matches)))

            # 从后向前替换，避免位置偏移
            for match in reversed(selected_matches):
                replacement = self.get_unique_replacement(original, synonyms_list)
                result = result[:match.start()] + replacement + result[match.end():]
                replacements.append((original, replacement))
                self.total_replacements += 1

        return result, replacements

    def get_statistics(self) -> dict:
        """获取替换统计信息"""
        return {
            'total_replacements': self.total_replacements,
            'unique_words_replaced': len(self.replacement_history),
            'replacement_details': dict(self.replacement_history)
        }


def process_file(input_path: str, output_path: str, whitelist_path: str = None, ratio: float = 0.5):
    """处理文件"""
    # 加载白名单
    whitelist = load_whitelist(whitelist_path)

    # 读取文件
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"原文长度: {len(text)} 字符")

    # 执行替换
    replacer = EnhancedSynonymReplacer(whitelist, ratio)
    result, replacements = replacer.replace_text(text)

    # 获取统计信息
    stats = replacer.get_statistics()

    # 保存结果
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"替换数量: {len(replacements)} 处")
    print(f"涉及词汇: {stats['unique_words_replaced']} 个不同词汇")
    print(f"结果已保存到: {output_path}")

    # 显示替换分布
    if replacements:
        print("\n替换分布:")
        word_counts = {}
        for old, new in replacements:
            word_counts[old] = word_counts.get(old, 0) + 1

        sorted_counts = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        for word, count in sorted_counts[:15]:
            print(f"  {word}: {count}次")

    return result, replacements, stats


if __name__ == '__main__':
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else "workspace/final/论文终稿.md"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "workspace/test_enhanced_replaced.md"
    whitelist_file = sys.argv[3] if len(sys.argv) > 3 else "scripts/term_whitelist.txt"
    ratio = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5

    process_file(input_file, output_file, whitelist_file, ratio)