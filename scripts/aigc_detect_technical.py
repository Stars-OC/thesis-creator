#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术论文专用 AIGC 检测工具

针对技术论文特点优化的检测算法：
1. 引入术语白名单，排除必要重复
2. 调整 TTR 阈值（技术论文 TTR > 0.20 视为正常）
3. 提供技术论文专用评分模式

使用方法：
    python aigc_detect_technical.py --input paper.md
    python aigc_detect_technical.py --input paper.md --whitelist term_whitelist.txt
"""

import re
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter

import jieba
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


# AI 高频过渡词列表
AI_TRANSITION_WORDS = [
    '首先', '其次', '最后', '此外', '另外', '同时', '综上所述',
    '由此可见', '值得注意的是', '需要指出的是', '不可否认',
    '总而言之', '概括来说', '简而言之', '换句话说', '显然',
    '由此可见', '不难看出', '必须承认', '诚然', '无疑',
    '毫无疑问', '不言而喻', '众所周知', '事实上', '实际上'
]

# AI 高频动词/短语
AI_HIGH_FREQ_PHRASES = [
    '旨在', '致力于', '表现为', '体现为', '涉及到', '具有重要意义',
    '发挥了重要作用', '起到了关键作用', '在很大程度上', '在一定程度上'
]

# 默认技术术语白名单
DEFAULT_TECH_WHITELIST = {
    # 计算机科学
    '检索', '向量', '知识库', '模型', '语义', '问答', '数据库', '接口',
    '语言', '量化', '算法', '架构', '框架', '组件', '模块', '服务',
    '缓存', '存储', '索引', '查询', '请求', '响应', '并发', '分布式',

    # AI/ML
    '深度学习', '机器学习', '神经网络', '自然语言处理', '文本挖掘',
    '特征工程', '训练', '推理', '预测', '分类', '聚类', '回归',

    # 软件工程
    '前端', '后端', '全栈', '微服务', '容器', '部署', '测试', '调试',

    # 通用技术
    '系统', '平台', '功能', '性能', '安全', '可靠', '可用', '扩展',
}


@dataclass
class DimensionScore:
    """维度分数"""
    score: float
    detail: str


class TechnicalPaperAIGCDetector:
    """技术论文专用 AIGC 检测器"""

    def __init__(
        self,
        whitelist_path: Optional[str] = None,
        mode: str = 'technical'  # 'technical' 或 'general'
    ):
        """
        初始化检测器

        Args:
            whitelist_path: 术语白名单文件路径
            mode: 检测模式
                - 'technical': 技术论文模式，TTR 阈值调整
                - 'general': 通用模式，使用标准阈值
        """
        self.mode = mode
        self.whitelist = self._load_whitelist(whitelist_path)

    def _load_whitelist(self, path: Optional[str]) -> Set[str]:
        """加载术语白名单"""
        whitelist = set(DEFAULT_TECH_WHITELIST)
        if path and Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    term = line.strip()
                    if term and not term.startswith('#'):
                        whitelist.add(term)
        return whitelist

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        pattern = r'[^。！？.!?]+[。！？.!?]?'
        sentences = re.findall(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_paragraphs(self, text: str) -> List[str]:
        """分割段落"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return paragraphs

    def _clean_text(self, text: str) -> str:
        """清理文本（移除 Markdown 语法）"""
        # 移除代码块
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # 移除表格分隔线
        text = re.sub(r'[-|]{3,}', '', text)
        # 移除 Markdown 标题符号
        text = re.sub(r'#+\s*', '', text)
        # 移除链接
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        return text

    def _calculate_burstiness(self, text: str) -> DimensionScore:
        """计算突发性"""
        sentences = self._split_sentences(text)

        if len(sentences) < 3:
            return DimensionScore(0, "句子数量不足，无法计算")

        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        if std_dev < 7:
            score = 50 + (7 - std_dev) * 5
            detail = f"句长方差 {std_dev:.1f}，低于人类典型值 10+，疑似 AI"
        elif std_dev < 10:
            score = 30 + (10 - std_dev) * 6
            detail = f"句长方差 {std_dev:.1f}，接近人类/AI 边界"
        else:
            score = max(0, 30 - (std_dev - 10) * 3)
            detail = f"句长方差 {std_dev:.1f}，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_vocabulary_diversity(self, text: str) -> DimensionScore:
        """
        计算词汇多样性（TTR）

        针对技术论文优化：
        1. 排除术语白名单中的词汇
        2. 调整阈值
        """
        # 清理文本
        clean_text = self._clean_text(text)

        # 分词
        words = list(jieba.cut(clean_text))

        # 过滤词汇
        meaningful = [
            w for w in words
            if len(w) >= 2
            and w.strip()
            and not w.isdigit()
            and not any(c.isalpha() and ord(c) < 128 for c in w)
            and w not in self.whitelist  # 排除术语白名单
        ]

        if len(meaningful) < 50:
            return DimensionScore(0, "词汇数量不足，无法计算")

        # 计算 TTR
        unique_words = set(meaningful)
        ttr = len(unique_words) / len(meaningful)

        # 根据模式调整阈值
        if self.mode == 'technical':
            # 技术论文模式：TTR > 0.15 视为正常
            if ttr < 0.15:
                score = 50 + (0.15 - ttr) * 300
                detail = f"TTR = {ttr:.3f}（排除术语），低于技术论文典型值 0.15+，疑似 AI"
            elif ttr < 0.20:
                score = 30 + (0.20 - ttr) * 400
                detail = f"TTR = {ttr:.3f}（排除术语），接近技术论文边界"
            else:
                score = max(0, 30 - (ttr - 0.20) * 100)
                detail = f"TTR = {ttr:.3f}（排除术语），符合技术论文特征"
        else:
            # 通用模式：使用标准阈值
            if ttr < 0.45:
                score = 50 + (0.45 - ttr) * 200
                detail = f"TTR = {ttr:.3f}，低于人类典型值 0.50+，疑似 AI"
            elif ttr < 0.50:
                score = 30 + (0.50 - ttr) * 400
                detail = f"TTR = {ttr:.3f}，接近人类/AI 边界"
            else:
                score = max(0, 30 - (ttr - 0.50) * 100)
                detail = f"TTR = {ttr:.3f}，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_transition_density(self, text: str) -> DimensionScore:
        """计算过渡词密度"""
        words = list(jieba.cut(text))
        total_words = len([w for w in words if w.strip()])

        if total_words < 50:
            return DimensionScore(0, "文本过短，无法计算")

        transition_count = 0
        found_words = []

        for word in AI_TRANSITION_WORDS:
            count = text.count(word)
            if count > 0:
                transition_count += count
                found_words.append(f"{word}({count})")

        density = transition_count / total_words * 100

        if density > 3:
            score = 50 + min(40, (density - 3) * 10)
            detail = f"过渡词密度 {density:.2f}%，高于正常：{', '.join(found_words[:5])}"
        elif density > 2:
            score = 30 + (density - 2) * 20
            detail = f"过渡词密度 {density:.2f}%，略高于正常"
        else:
            score = max(0, 30 - density * 5)
            detail = f"过渡词密度 {density:.2f}%，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_structure_pattern(self, text: str) -> DimensionScore:
        """计算句式模式"""
        paragraphs = self._split_paragraphs(text)

        if len(paragraphs) < 3:
            return DimensionScore(0, "段落数量不足，无法计算")

        typical_structure_count = 0

        for para in paragraphs:
            sentences = self._split_sentences(para)
            if len(sentences) >= 3:
                first = sentences[0]
                last = sentences[-1]

                first_words = set(jieba.cut(first))
                last_words = set(jieba.cut(last))
                common = first_words & last_words
                common = {w for w in common if len(w) >= 2}

                if len(common) >= 2:
                    typical_structure_count += 1

        ratio = typical_structure_count / len(paragraphs) * 100

        if ratio > 50:
            score = 50 + min(40, (ratio - 50) * 0.8)
            detail = f"总分总结构占比 {ratio:.1f}%，高于正常"
        elif ratio > 30:
            score = 30 + (ratio - 30)
            detail = f"总分总结构占比 {ratio:.1f}%，接近边界"
        else:
            score = max(0, 30 - ratio * 0.5)
            detail = f"总分总结构占比 {ratio:.1f}%，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def detect(self, text: str) -> Dict:
        """执行 AIGC 检测"""
        results = {
            'mode': self.mode,
            'char_count': len(text.replace('\n', '').replace(' ', '')),
            'whitelist_size': len(self.whitelist)
        }

        # 计算各维度分数
        burstiness = self._calculate_burstiness(text)
        vocabulary = self._calculate_vocabulary_diversity(text)
        transition = self._calculate_transition_density(text)
        structure = self._calculate_structure_pattern(text)

        results['burstiness'] = {'score': burstiness.score, 'detail': burstiness.detail}
        results['vocabulary'] = {'score': vocabulary.score, 'detail': vocabulary.detail}
        results['transition'] = {'score': transition.score, 'detail': transition.detail}
        results['structure'] = {'score': structure.score, 'detail': structure.detail}

        # 计算总分（技术论文模式降低 TTR 权重）
        if self.mode == 'technical':
            weights = {
                'burstiness': 0.35,
                'vocabulary': 0.15,  # 降低 TTR 权重
                'transition': 0.30,
                'structure': 0.20
            }
        else:
            weights = {
                'burstiness': 0.35,
                'vocabulary': 0.25,
                'transition': 0.20,
                'structure': 0.20
            }

        overall = (
            burstiness.score * weights['burstiness'] +
            vocabulary.score * weights['vocabulary'] +
            transition.score * weights['transition'] +
            structure.score * weights['structure']
        )

        results['overall_score'] = round(overall, 1)

        # 生成建议
        if overall > 50:
            results['suggestion'] = f"AIGC 检测率较高（{overall:.1f}%），建议重点改写高风险段落"
        elif overall > 30:
            results['suggestion'] = f"AIGC 检测率中等（{overall:.1f}%），建议适当改写"
        else:
            results['suggestion'] = f"AIGC 检测率较低（{overall:.1f}%），通过检测的可能性较高"

        return results

    def print_report(self, results: Dict):
        """打印检测报告"""
        mode_text = "技术论文模式" if results['mode'] == 'technical' else "通用模式"
        console.print(Panel(
            f"[bold blue]AIGC 检测报告[/bold blue]\n"
            f"模式：{mode_text}\n"
            f"字数：{results['char_count']}\n"
            f"术语白名单：{results['whitelist_size']} 个"
        ))

        # 总分
        overall = results['overall_score']
        if overall > 50:
            color = "red"
            status = "高风险"
        elif overall > 30:
            color = "yellow"
            status = "中等风险"
        else:
            color = "green"
            status = "低风险"

        console.print(f"\n[bold {color}]整体 AIGC 检测率：{overall}% ({status})[/bold {color}]")

        # 各维度分数
        table = Table(title="各维度检测")
        table.add_column("维度", style="cyan")
        table.add_column("分数", style="green")
        table.add_column("说明", style="white")

        dimensions = ['burstiness', 'vocabulary', 'transition', 'structure']
        dimension_names = {
            'burstiness': '突发性',
            'vocabulary': '词汇多样性',
            'transition': '过渡词密度',
            'structure': '句式模式'
        }

        for dim in dimensions:
            if dim in results:
                data = results[dim]
                dim_name = dimension_names.get(dim, dim)
                score_color = "red" if data['score'] > 50 else "yellow" if data['score'] > 30 else "green"
                table.add_row(dim_name, f"[{score_color}]{data['score']}[/{score_color}]", data['detail'])

        console.print(table)
        console.print(f"\n[bold]建议：[/bold]{results['suggestion']}")


def detect_file(
    path: str,
    whitelist_path: Optional[str] = None,
    mode: str = 'technical',
    output_format: str = 'table'
) -> Dict:
    """检测文件"""
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    detector = TechnicalPaperAIGCDetector(whitelist_path=whitelist_path, mode=mode)
    results = detector.detect(text)

    if output_format == 'table':
        detector.print_report(results)
    elif output_format == 'json':
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return results


@click.command()
@click.option('--input', '-i', required=True, help='输入文件路径')
@click.option('--whitelist', '-w', default=None, help='术语白名单文件路径')
@click.option('--mode', '-m', default='technical', type=click.Choice(['technical', 'general']), help='检测模式')
@click.option('--format', '-f', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
def main(input: str, whitelist: Optional[str], mode: str, output_format: str):
    """技术论文专用 AIGC 检测工具"""
    detect_file(input, whitelist, mode, output_format)


if __name__ == '__main__':
    main()