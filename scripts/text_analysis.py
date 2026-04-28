#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文本特征分析工具

分析文本的统计特征，帮助用户了解文本「像 AI」的程度。
包括：句长统计、词汇多样性、过渡词密度、段落首词多样度等。

使用方法：
    python text_analysis.py --input paper.md
    python text_analysis.py --compare before.md after.md
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter

import jieba
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

console = Console()


# AI 高频过渡词列表
AI_TRANSITION_WORDS = [
    '首先', '其次', '最后', '此外', '另外', '同时', '综上所述',
    '由此可见', '值得注意的是', '需要指出的是', '不可否认',
    '总而言之', '概括来说', '简而言之', '换句话说', '显然',
    '由此可见', '不难看出', '必须承认', '诚然'
]


class TextAnalyzer:
    """文本特征分析器"""

    def __init__(self):
        """__init__"""
        self.sentences: List[str] = []
        self.words: List[str] = []
        self.paragraphs: List[str] = []

    def load_text(self, text: str):
        """加载文本"""
        self._text = text
        self._analyze()

    def load_file(self, path: str):
        """从文件加载文本"""
        with open(path, 'r', encoding='utf-8') as f:
            self._text = f.read()
        self._analyze()

    def _analyze(self):
        """执行分析"""
        # 分句
        self.sentences = self._split_sentences(self._text)
        # 分词
        self.words = list(jieba.cut(self._text))
        # 分段
        self.paragraphs = [p.strip() for p in self._text.split('\n\n') if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 使用正则分割，保留句号、问号、感叹号
        pattern = r'[^。！？.!?]+[。！？.!?]?'
        sentences = re.findall(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def analyze(self) -> Dict:
        """执行完整分析"""
        results = {}

        # 1. 字数统计
        char_count = len(self._text.replace('\n', '').replace(' ', ''))
        results['char_count'] = char_count

        # 2. 句数统计
        results['sentence_count'] = len(self.sentences)

        # 3. 段落数统计
        results['paragraph_count'] = len(self.paragraphs)

        # 4. 句长分析
        sentence_lengths = [len(s) for s in self.sentences]
        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            # 计算标准差
            variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            std_dev = variance ** 0.5

            results['avg_sentence_length'] = round(avg_length, 1)
            results['sentence_length_std'] = round(std_dev, 1)
            results['min_sentence_length'] = min(sentence_lengths)
            results['max_sentence_length'] = max(sentence_lengths)

        # 5. 词汇多样性（TTR）
        meaningful_words = [w for w in self.words if len(w) >= 2 and w.strip()]
        if meaningful_words:
            unique_words = set(meaningful_words)
            ttr = len(unique_words) / len(meaningful_words)
            results['vocabulary_richness'] = round(ttr, 3)
            results['word_count'] = len(meaningful_words)
            results['unique_word_count'] = len(unique_words)

        # 6. 过渡词密度
        transition_count = 0
        for word in AI_TRANSITION_WORDS:
            transition_count += self._text.count(word)

        total_words = len([w for w in self.words if w.strip()])
        if total_words > 0:
            transition_density = transition_count / total_words * 100
            results['transition_word_density'] = round(transition_density, 2)
            results['transition_word_count'] = transition_count

        # 7. 段落首词多样度
        if self.paragraphs:
            first_words = []
            for p in self.paragraphs:
                # 获取段落第一个词
                words = list(jieba.cut(p))
                for w in words:
                    if w.strip() and len(w) >= 2:
                        first_words.append(w)
                        break

            if first_words:
                unique_first = set(first_words)
                diversity = len(unique_first) / len(first_words) * 100
                results['paragraph_first_word_diversity'] = round(diversity, 1)

        return results

    def compare(self, other: 'TextAnalyzer') -> Dict:
        """与另一文本对比"""
        self_results = self.analyze()
        other_results = other.analyze()

        comparison = {}
        for key in self_results:
            if key in other_results:
                comparison[key] = {
                    'before': self_results[key],
                    'after': other_results[key],
                    'change': other_results[key] - self_results[key]
                }

        return comparison


def print_analysis_report(results: Dict, title: str = "文本分析报告"):
    """打印分析报告"""
    console.print(Panel(f"[bold blue]{title}[/bold blue]"))

    # 基础统计
    table1 = Table(title="基础统计")
    table1.add_column("指标", style="cyan")
    table1.add_column("数值", style="green")
    table1.add_column("人类典型值", style="yellow")

    table1.add_row("总字数", str(results.get('char_count', 'N/A')), '-')
    table1.add_row("句子数", str(results.get('sentence_count', 'N/A')), '-')
    table1.add_row("段落数", str(results.get('paragraph_count', 'N/A')), '-')

    console.print(table1)

    # 句长分析
    table2 = Table(title="句长分析")
    table2.add_column("指标", style="cyan")
    table2.add_column("数值", style="green")
    table2.add_column("人类典型值", style="yellow")
    table2.add_column("评估", style="magenta")

    avg_len = results.get('avg_sentence_length', 0)
    std_dev = results.get('sentence_length_std', 0)

    # 评估句长
    len_eval = "正常" if 15 <= avg_len <= 35 else "[WARN] 异常"
    std_eval = "[OK] 自然" if std_dev > 10 else "[WARN] 偏均匀（AI 特征）"

    table2.add_row("平均句长", f"{avg_len} 字", "15-35 字", len_eval)
    table2.add_row("句长标准差", f"{std_dev}", "> 10", std_eval)
    table2.add_row("最短句", f"{results.get('min_sentence_length', 0)} 字", "-", "-")
    table2.add_row("最长句", f"{results.get('max_sentence_length', 0)} 字", "-", "-")

    console.print(table2)

    # 词汇分析
    table3 = Table(title="词汇分析")
    table3.add_column("指标", style="cyan")
    table3.add_column("数值", style="green")
    table3.add_column("人类典型值", style="yellow")
    table3.add_column("评估", style="magenta")

    ttr = results.get('vocabulary_richness', 0)
    ttr_eval = "[OK] 丰富" if ttr > 0.5 else "[WARN] 偏低（AI 特征）"

    table3.add_row("词汇数", str(results.get('word_count', 0)), "-", "-")
    table3.add_row("不重复词数", str(results.get('unique_word_count', 0)), "-", "-")
    table3.add_row("词汇丰富度(TTR)", f"{ttr}", "> 0.50", ttr_eval)

    console.print(table3)

    # AI 特征分析
    table4 = Table(title="AI 特征分析")
    table4.add_column("指标", style="cyan")
    table4.add_column("数值", style="green")
    table4.add_column("人类典型值", style="yellow")
    table4.add_column("评估", style="magenta")

    trans_density = results.get('transition_word_density', 0)
    trans_eval = "[OK] 自然" if trans_density < 2 else "[WARN] 过高（AI 特征）"

    first_div = results.get('paragraph_first_word_diversity', 0)
    first_eval = "[OK] 多样" if first_div > 70 else "[WARN] 单调（AI 特征）"

    table4.add_row("过渡词密度", f"{trans_density}%", "< 2%", trans_eval)
    table4.add_row("段首词多样度", f"{first_div}%", "> 70%", first_eval)

    console.print(table4)


def print_comparison_report(comparison: Dict):
    """打印对比报告"""
    console.print(Panel("[bold blue]文本对比分析[/bold blue]"))

    table = Table(title="修改前后对比")
    table.add_column("指标", style="cyan")
    table.add_column("修改前", style="red")
    table.add_column("修改后", style="green")
    table.add_column("变化", style="yellow")

    for key, values in comparison.items():
        if isinstance(values, dict) and 'change' in values:
            change_str = f"+{values['change']}" if values['change'] > 0 else str(values['change'])
            table.add_row(
                key,
                str(values['before']),
                str(values['after']),
                change_str
            )

    console.print(table)


@click.command()
@click.option('--input', '-i', required=True, help='输入文件路径')
@click.option('--compare', '-c', default=None, help='对比文件路径')
@click.option('--format', '-f', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.option('--verbose', '-v', is_flag=True, default=False, help='详细输出模式')
@click.option('--quiet', '-q', is_flag=True, default=False, help='静默模式（仅输出结果）')
@click.option('--report', '-r', is_flag=True, default=False, help='输出完整报告')
def main(input: str, compare: Optional[str], output_format: str, verbose: bool, quiet: bool, report: bool):
    """文本特征分析工具"""
    analyzer = TextAnalyzer()
    analyzer.load_file(input)

    if compare:
        other = TextAnalyzer()
        other.load_file(compare)
        comparison = analyzer.compare(other)
        print_comparison_report(comparison)
    else:
        results = analyzer.analyze()
        print_analysis_report(results)


if __name__ == '__main__':
    main()
