#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
中文同义词替换工具

基于 jieba 分词和 synonyms 库，自动替换文本中的非术语词汇。
支持术语白名单保护，避免专业术语被误替换。

使用方法：
    python synonym_replace.py --input paper.md --output paper_replaced.md
    python synonym_replace.py --input paper.md --ratio 0.4
    python synonym_replace.py --input paper.md --whitelist term_whitelist.txt
"""

import re
import random
from pathlib import Path
from typing import List, Set, Tuple, Optional

import jieba
import synonyms
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class SynonymReplacer:
    """中文同义词替换器"""

    def __init__(
        self,
        whitelist_path: Optional[str] = None,
        replace_ratio: float = 0.3,
        min_word_length: int = 2
    ):
        """
        初始化替换器

        Args:
            whitelist_path: 术语白名单文件路径
            replace_ratio: 替换比例（0-1）
            min_word_length: 最小替换词长度
        """
        self.replace_ratio = replace_ratio
        self.min_word_length = min_word_length
        self.whitelist = self._load_whitelist(whitelist_path)
        self.replace_log: List[Tuple[str, str]] = []

        # 停用词（不替换的常用词）
        self.stopwords = self._get_stopwords()

    def _load_whitelist(self, path: Optional[str]) -> Set[str]:
        """加载术语白名单"""
        whitelist = set()
        if path and Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    term = line.strip()
                    if term and not term.startswith('#'):
                        whitelist.add(term)
            console.print(f"[green]已加载白名单：{len(whitelist)} 个术语[/green]")
        return whitelist

    def _get_stopwords(self) -> Set[str]:
        """获取停用词列表"""
        # 常用停用词
        return {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '那', '这个', '那个', '什么', '怎么', '可以',
            '因为', '所以', '但是', '如果', '虽然', '而且', '或者', '以及', '等等'
        }

    def _is_replaceable(self, word: str) -> bool:
        """判断词汇是否可替换"""
        # 过滤条件
        if len(word) < self.min_word_length:
            return False
        if word in self.whitelist:
            return False
        if word in self.stopwords:
            return False
        if re.match(r'^[\d\W]+$', word):  # 纯数字或标点
            return False
        return True

    def _get_synonyms(self, word: str, top_k: int = 5) -> List[str]:
        """获取同义词列表"""
        try:
            # synonyms 库返回相似度分数
            words, scores = synonyms.nearby(word, top_k)
            # 过滤掉原词和相似度太低的词
            synonyms_list = [
                w for w, s in zip(words, scores)
                if w != word and s > 0.5
            ]
            return synonyms_list
        except Exception:
            return []

    def replace_text(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        对文本进行同义词替换

        Args:
            text: 原始文本

        Returns:
            替换后的文本和替换日志
        """
        self.replace_log = []

        # 使用 jieba 分词
        words = list(jieba.cut(text))

        # 找出可替换的词
        replaceable_indices = []
        for i, word in enumerate(words):
            if self._is_replaceable(word):
                synonyms_list = self._get_synonyms(word)
                if synonyms_list:
                    replaceable_indices.append((i, word, synonyms_list))

        # 按比例随机选择要替换的词
        num_to_replace = max(1, int(len(replaceable_indices) * self.replace_ratio))
        selected = random.sample(
            replaceable_indices,
            min(num_to_replace, len(replaceable_indices))
        )

        # 执行替换
        for idx, word, synonyms_list in selected:
            new_word = random.choice(synonyms_list)
            words[idx] = new_word
            self.replace_log.append((word, new_word))

        # 重组文本
        result = ''.join(words)
        return result, self.replace_log

    def print_report(self):
        """打印替换报告"""
        if not self.replace_log:
            console.print("[yellow]未进行任何替换[/yellow]")
            return

        table = Table(title="同义词替换报告")
        table.add_column("原词", style="red")
        table.add_column("替换为", style="green")

        for old, new in self.replace_log:
            table.add_row(old, new)

        console.print(table)
        console.print(f"\n[bold]总计替换：{len(self.replace_log)} 处[/bold]")


def replace_file(
    input_path: str,
    output_path: Optional[str] = None,
    whitelist_path: Optional[str] = None,
    ratio: float = 0.3
) -> str:
    """
    替换文件中的同义词

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）
        whitelist_path: 白名单文件路径
        ratio: 替换比例

    Returns:
        替换后的文本
    """
    # 读取文件
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    console.print(Panel(f"[bold blue]同义词替换工具[/bold blue]\n输入：{input_path}\n替换比例：{ratio}"))

    # 初始化替换器
    replacer = SynonymReplacer(
        whitelist_path=whitelist_path,
        replace_ratio=ratio
    )

    # 执行替换
    result, log = replacer.replace_text(text)

    # 打印报告
    replacer.print_report()

    # 保存结果
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"\n[green]已保存到：{output_path}[/green]")

    return result


@click.command()
@click.option('--input', '-i', required=True, help='输入文件路径')
@click.option('--output', '-o', default=None, help='输出文件路径')
@click.option('--ratio', '-r', default=0.3, type=float, help='替换比例（0-1，默认 0.3）')
@click.option('--whitelist', '-w', default=None, help='术语白名单文件路径')
@click.option('--format', '-f', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.option('--verbose', '-v', is_flag=True, default=False, help='详细输出模式')
@click.option('--quiet', '-q', is_flag=True, default=False, help='静默模式（仅输出结果）')
def main(input: str, output: Optional[str], ratio: float, whitelist: Optional[str], output_format: str, verbose: bool, quiet: bool):
    """中文同义词替换工具"""
    if output is None:
        # 默认输出路径
        input_path = Path(input)
        output = str(input_path.parent / f"{input_path.stem}_replaced{input_path.suffix}")

    replace_file(input, output, whitelist, ratio)


if __name__ == '__main__':
    main()
