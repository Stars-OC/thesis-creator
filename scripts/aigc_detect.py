#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AIGC 本地检测工具

基于文本统计特征的本地 AIGC 检测工具，提供快速预估。
支持双模式：
- 方案 A（默认）：轻量版，4 维度统计检测（~50 MB）
- 方案 B（可选）：完整版，增加 GPT-2 困惑度（~2.5 GB）

使用方法：
    python aigc_detect.py --input paper.md
    python aigc_detect.py --text "待检测的文本内容..."
    python aigc_detect.py --dir workspace/reduced/
    python aigc_detect.py --input paper.md --mode full
"""

import re
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
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
    '由此可见', '不难看出', '必须承认', '诚然', '无疑',
    '毫无疑问', '不言而喻', '众所周知', '事实上', '实际上'
]

# AI 高频动词/短语
AI_HIGH_FREQ_PHRASES = [
    '旨在', '致力于', '表现为', '体现为', '涉及到', '具有重要意义',
    '发挥了重要作用', '起到了关键作用', '在很大程度上', '在一定程度上'
]


@dataclass
class DimensionScore:
    """维度分数"""
    score: float
    detail: str


class AIGCDetector:
    """AIGC 检测器"""

    def __init__(self, mode: str = 'lite'):
        """
        初始化检测器

        Args:
            mode: 'lite'（轻量版）或 'full'（完整版，含困惑度）
        """
        self.mode = mode
        self.perplexity_model = None

        # 尝试加载困惑度模型
        if mode == 'full':
            self._load_perplexity_model()

    def _load_perplexity_model(self):
        """加载困惑度计算模型"""
        try:
            from transformers import GPT2LMHeadModel, GPT2Tokenizer
            console.print("[yellow]正在加载 GPT-2 模型...[/yellow]")

            # 使用中文 GPT-2 模型
            model_name = "uer/gpt2-chinese-cluecorpussmall"
            self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
            self.model = GPT2LMHeadModel.from_pretrained(model_name)
            self.perplexity_available = True

            console.print("[green]GPT-2 模型加载成功[/green]")
        except ImportError:
            console.print("[yellow]未安装 transformers/torch，困惑度检测不可用[/yellow]")
            console.print("[yellow]已自动切换到轻量模式[/yellow]")
            self.mode = 'lite'
            self.perplexity_available = False
        except Exception as e:
            console.print(f"[yellow]模型加载失败：{e}[/yellow]")
            console.print("[yellow]已自动切换到轻量模式[/yellow]")
            self.mode = 'lite'
            self.perplexity_available = False

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        pattern = r'[^。！？.!?]+[。！？.!?]?'
        sentences = re.findall(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_paragraphs(self, text: str) -> List[str]:
        """分割段落"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return paragraphs

    def _calculate_burstiness(self, text: str) -> DimensionScore:
        """
        计算突发性（Burstiness）

        AI 文本句长方差小（均匀），人类文本句长方差大（波动）

        Args:
            text: 输入文本

        Returns:
            维度分数（0-100，越高越像 AI）
        """
        sentences = self._split_sentences(text)

        if len(sentences) < 3:
            return DimensionScore(0, "句子数量不足，无法计算")

        # 计算句长
        lengths = [len(s) for s in sentences]

        # 计算均值和标准差
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        # 人类典型标准差 > 10，AI 典型 < 7
        # 分数计算：标准差越小，分数越高
        if std_dev < 7:
            score = 50 + (7 - std_dev) * 5  # 50-85
            detail = f"句长方差 {std_dev:.1f}，低于人类典型值 10+，疑似 AI"
        elif std_dev < 10:
            score = 30 + (10 - std_dev) * 6  # 30-50
            detail = f"句长方差 {std_dev:.1f}，接近人类/AI 边界"
        else:
            score = max(0, 30 - (std_dev - 10) * 3)  # 0-30
            detail = f"句长方差 {std_dev:.1f}，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_vocabulary_diversity(self, text: str) -> DimensionScore:
        """
        计算词汇多样性（TTR）

        AI 文本词汇重复率高，TTR 偏低

        Args:
            text: 输入文本

        Returns:
            维度分数（0-100，越高越像 AI）
        """
        words = list(jieba.cut(text))
        meaningful_words = [w for w in words if len(w) >= 2 and w.strip()]

        if len(meaningful_words) < 50:
            return DimensionScore(0, "词汇数量不足，无法计算")

        # 计算 TTR
        unique_words = set(meaningful_words)
        ttr = len(unique_words) / len(meaningful_words)

        # 人类典型 TTR > 0.50，AI 典型 < 0.45
        if ttr < 0.45:
            score = 50 + (0.45 - ttr) * 200  # 50-90
            detail = f"TTR = {ttr:.3f}，低于人类典型值 0.50+，疑似 AI"
        elif ttr < 0.50:
            score = 30 + (0.50 - ttr) * 400  # 30-50
            detail = f"TTR = {ttr:.3f}，接近人类/AI 边界"
        else:
            score = max(0, 30 - (ttr - 0.50) * 100)  # 0-30
            detail = f"TTR = {ttr:.3f}，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_transition_density(self, text: str) -> DimensionScore:
        """
        计算过渡词密度

        AI 文本过度使用模板化过渡词

        Args:
            text: 输入文本

        Returns:
            维度分数（0-100，越高越像 AI）
        """
        words = list(jieba.cut(text))
        total_words = len([w for w in words if w.strip()])

        if total_words < 50:
            return DimensionScore(0, "文本过短，无法计算")

        # 统计过渡词出现次数
        transition_count = 0
        found_words = []

        for word in AI_TRANSITION_WORDS:
            count = text.count(word)
            if count > 0:
                transition_count += count
                found_words.append(f"{word}({count})")

        # 计算密度（百分比）
        density = transition_count / total_words * 100

        # 人类典型密度 < 2%，AI 典型 > 3%
        if density > 3:
            score = 50 + min(40, (density - 3) * 10)  # 50-90
            detail = f"过渡词密度 {density:.2f}%，高于人类典型值 2%：{', '.join(found_words[:5])}"
        elif density > 2:
            score = 30 + (density - 2) * 20  # 30-50
            detail = f"过渡词密度 {density:.2f}%，略高于正常"
        else:
            score = max(0, 30 - density * 5)  # 0-30
            detail = f"过渡词密度 {density:.2f}%，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_structure_pattern(self, text: str) -> DimensionScore:
        """
        计算句式模式

        检测「总分总」等 AI 偏好结构

        Args:
            text: 输入文本

        Returns:
            维度分数（0-100，越高越像 AI）
        """
        paragraphs = self._split_paragraphs(text)

        if len(paragraphs) < 3:
            return DimensionScore(0, "段落数量不足，无法计算")

        # 检测总分总结构
        typical_structure_count = 0

        for para in paragraphs:
            sentences = self._split_sentences(para)
            if len(sentences) >= 3:
                # 检查首句是否为总述，末句是否为小结
                first = sentences[0]
                last = sentences[-1]

                # 简单判断：首句和末句是否包含相同关键词
                first_words = set(jieba.cut(first))
                last_words = set(jieba.cut(last))
                common = first_words & last_words

                # 排除单字词
                common = {w for w in common if len(w) >= 2}

                if len(common) >= 2:
                    typical_structure_count += 1

        # 计算比例
        ratio = typical_structure_count / len(paragraphs) * 100

        # AI 典型 > 50%，人类典型 < 30%
        if ratio > 50:
            score = 50 + min(40, (ratio - 50) * 0.8)  # 50-90
            detail = f"总分总结构占比 {ratio:.1f}%，高于正常"
        elif ratio > 30:
            score = 30 + (ratio - 30)  # 30-50
            detail = f"总分总结构占比 {ratio:.1f}%，接近边界"
        else:
            score = max(0, 30 - ratio * 0.5)  # 0-30
            detail = f"总分总结构占比 {ratio:.1f}%，符合人类特征"

        return DimensionScore(round(score, 1), detail)

    def _calculate_perplexity(self, text: str) -> DimensionScore:
        """
        计算困惑度（Perplexity）

        AI 文本困惑度低（可预测），人类文本困惑度高

        Args:
            text: 输入文本

        Returns:
            维度分数（0-100，越高越像 AI）
        """
        if not self.perplexity_available:
            return DimensionScore(0, "困惑度检测不可用")

        try:
            import torch

            # 截断过长文本
            max_length = 512
            if len(text) > max_length * 2:
                text = text[:max_length * 2]

            # 编码
            inputs = self.tokenizer(text, return_tensors='pt')

            # 计算 loss
            with torch.no_grad():
                outputs = self.model(inputs['input_ids'], labels=inputs['input_ids'])
                loss = outputs.loss
                perplexity = torch.exp(loss).item()

            # AI 典型困惑度 < 50，人类 > 100
            if perplexity < 50:
                score = 70 + min(25, (50 - perplexity))  # 70-95
                detail = f"困惑度 {perplexity:.1f}，低于人类典型值 100+，疑似 AI"
            elif perplexity < 100:
                score = 40 + (100 - perplexity) * 0.6  # 40-70
                detail = f"困惑度 {perplexity:.1f}，接近人类/AI 边界"
            else:
                score = max(0, 40 - (perplexity - 100) * 0.2)  # 0-40
                detail = f"困惑度 {perplexity:.1f}，符合人类特征"

            return DimensionScore(round(score, 1), detail)

        except Exception as e:
            return DimensionScore(0, f"困惑度计算失败：{e}")

    def detect(self, text: str) -> Dict:
        """
        执行 AIGC 检测

        Args:
            text: 输入文本

        Returns:
            检测结果字典
        """
        results = {
            'mode': self.mode,
            'char_count': len(text.replace('\n', '').replace(' ', ''))
        }

        # 方案 A：轻量版（4 维度）
        burstiness = self._calculate_burstiness(text)
        vocabulary = self._calculate_vocabulary_diversity(text)
        transition = self._calculate_transition_density(text)
        structure = self._calculate_structure_pattern(text)

        results['burstiness'] = {'score': burstiness.score, 'detail': burstiness.detail}
        results['vocabulary'] = {'score': vocabulary.score, 'detail': vocabulary.detail}
        results['transition'] = {'score': transition.score, 'detail': transition.detail}
        results['structure'] = {'score': structure.score, 'detail': structure.detail}

        if self.mode == 'lite':
            # 轻量版权重
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

        else:
            # 完整版：增加困惑度
            perplexity = self._calculate_perplexity(text)
            results['perplexity'] = {'score': perplexity.score, 'detail': perplexity.detail}

            # 完整版权重
            weights = {
                'perplexity': 0.40,
                'burstiness': 0.25,
                'vocabulary': 0.15,
                'transition': 0.10,
                'structure': 0.10
            }

            overall = (
                perplexity.score * weights['perplexity'] +
                burstiness.score * weights['burstiness'] +
                vocabulary.score * weights['vocabulary'] +
                transition.score * weights['transition'] +
                structure.score * weights['structure']
            )

        results['overall_score'] = round(overall, 1)

        # 识别高风险段落
        results['high_risk_paragraphs'] = self._identify_high_risk_paragraphs(text)

        # 生成建议
        if overall > 50:
            results['suggestion'] = f"AIGC 检测率较高（{overall:.1f}%），建议重点改写第 {results['high_risk_paragraphs']} 段"
        elif overall > 30:
            results['suggestion'] = f"AIGC 检测率中等（{overall:.1f}%），建议适当改写高风险段落"
        else:
            results['suggestion'] = f"AIGC 检测率较低（{overall:.1f}%），通过检测的可能性较高"

        return results

    def _identify_high_risk_paragraphs(self, text: str) -> List[int]:
        """识别高风险段落"""
        paragraphs = self._split_paragraphs(text)
        high_risk = []

        for i, para in enumerate(paragraphs):
            # 检查是否包含大量 AI 特征词
            ai_word_count = 0
            for word in AI_TRANSITION_WORDS + AI_HIGH_FREQ_PHRASES:
                ai_word_count += para.count(word)

            # 如果 AI 特征词密度 > 5%，标记为高风险
            if len(para) > 0 and ai_word_count / len(para) * 100 > 5:
                high_risk.append(i + 1)  # 段落编号从 1 开始

        return high_risk

    def print_report(self, results: Dict):
        """打印检测报告"""
        # 模式说明
        mode_text = "轻量版（4 维度）" if results['mode'] == 'lite' else "完整版（含困惑度）"
        console.print(Panel(f"[bold blue]AIGC 检测报告[/bold blue]\n模式：{mode_text}\n字数：{results['char_count']}"))

        # 总分
        overall = results['overall_score']
        if overall > 50:
            color = "red"
            status = "[WARN] 高风险"
        elif overall > 30:
            color = "yellow"
            status = "[!] 中等风险"
        else:
            color = "green"
            status = "[OK] 低风险"

        console.print(f"\n[bold {color}]整体 AIGC 检测率：{overall}% {status}[/bold {color}]")

        # 各维度分数
        table = Table(title="各维度检测")
        table.add_column("维度", style="cyan")
        table.add_column("分数", style="green")
        table.add_column("说明", style="white")

        dimensions = ['burstiness', 'vocabulary', 'transition', 'structure']
        if results['mode'] == 'full' and 'perplexity' in results:
            dimensions = ['perplexity'] + dimensions

        dimension_names = {
            'perplexity': '困惑度',
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

        # 高风险段落
        if results['high_risk_paragraphs']:
            console.print(f"\n[yellow]高风险段落：第 {results['high_risk_paragraphs']} 段[/yellow]")

        # 建议
        console.print(f"\n[bold]建议：[/bold]{results['suggestion']}")


def detect_file(path: str, mode: str = 'lite', output_format: str = 'table') -> Dict:
    """检测文件"""
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    detector = AIGCDetector(mode=mode)
    results = detector.detect(text)

    if output_format == 'table':
        detector.print_report(results)
    elif output_format == 'json':
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return results


def detect_text(text: str, mode: str = 'lite', output_format: str = 'table') -> Dict:
    """检测文本"""
    detector = AIGCDetector(mode=mode)
    results = detector.detect(text)

    if output_format == 'table':
        detector.print_report(results)
    elif output_format == 'json':
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return results


def detect_directory(dir_path: str, mode: str = 'lite') -> List[Dict]:
    """检测目录下所有 Markdown 文件"""
    results = []
    md_files = list(Path(dir_path).glob('*.md'))

    if not md_files:
        console.print(f"[yellow]目录 {dir_path} 中没有找到 Markdown 文件[/yellow]")
        return results

    detector = AIGCDetector(mode=mode)

    console.print(Panel(f"[bold blue]批量检测：{dir_path}[/bold blue]"))

    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            text = f.read()

        result = detector.detect(text)
        result['file'] = md_file.name
        results.append(result)

        console.print(f"\n[bold]{md_file.name}[/bold]: AIGC 检测率 {result['overall_score']}%")

    return results


@click.command()
@click.option('--input', '-i', default=None, help='输入文件路径')
@click.option('--text', '-t', default=None, help='直接输入文本')
@click.option('--dir', '-d', default=None, help='输入目录路径')
@click.option('--mode', '-m', default='lite', type=click.Choice(['lite', 'full']), help='检测模式')
@click.option('--format', '-f', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.option('--verbose', '-v', is_flag=True, default=False, help='详细输出模式')
@click.option('--quiet', '-q', is_flag=True, default=False, help='静默模式（仅输出结果）')
@click.option('--report', '-r', is_flag=True, default=False, help='输出完整报告')
def main(input: Optional[str], text: Optional[str], dir: Optional[str], mode: str, output_format: str, verbose: bool, quiet: bool, report: bool):
    """AIGC 本地检测工具"""
    if quiet:
        output_format = 'json'

    if input:
        detect_file(input, mode, output_format)
    elif text:
        detect_text(text, mode, output_format)
    elif dir:
        detect_directory(dir_path=dir, mode=mode)
    else:
        console.print("[red]请指定 --input、--text 或 --dir 参数[/red]")


if __name__ == '__main__':
    main()