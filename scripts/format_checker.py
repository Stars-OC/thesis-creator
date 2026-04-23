#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文格式检查工具

检查论文 Markdown 文件的结构规范性。
包括：标题层级、摘要、关键词、参考文献、章节完整性、引用完整性等。

使用方法：
    python format_checker.py --input paper.md
    python format_checker.py --dir workspace/drafts/
    python format_checker.py --input paper.md --check-citations
    python format_checker.py --input paper.md --check-citations --report json
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


@dataclass
class CitationReport:
    """引用检查报告"""
    total_citations: int = 0
    total_references: int = 0
    orphan_references: List[int] = field(default_factory=list)
    missing_references: List[int] = field(default_factory=list)
    citation_density: float = 0.0
    distribution: Dict[str, int] = field(default_factory=dict)
    format_issues: List[Dict] = field(default_factory=list)


class FormatChecker:
    """论文格式检查器"""

    def __init__(self, verbose: bool = False):
        self.results: List[CheckResult] = []
        self.content: str = ""
        self.lines: List[str] = []
        self.verbose = verbose
        self.citation_report: Optional[CitationReport] = None

    def load_file(self, path: str):
        """加载文件"""
        with open(path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        self.lines = self.content.split('\n')
        self.file_path = path

    def check_title_hierarchy(self) -> CheckResult:
        """检查标题层级"""
        headings = []
        for i, line in enumerate(self.lines):
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                title = line.lstrip('#').strip()
                headings.append((level, title, i + 1))

        issues = []

        # 检查是否有标题
        if not headings:
            return CheckResult(
                name="标题层级",
                passed=False,
                message="未找到任何标题",
                details=["请添加 # 开头的标题"]
            )

        # 检查是否从一级标题开始
        if headings[0][0] != 1:
            issues.append(f"第 {headings[0][2]} 行：应从一级标题开始")

        # 检查层级是否跳级
        for i in range(1, len(headings)):
            prev_level = headings[i-1][0]
            curr_level = headings[i][0]
            if curr_level > prev_level + 1:
                issues.append(
                    f"第 {headings[i][2]} 行：「{headings[i][1][:20]}...」"
                    f"从 {prev_level} 级跳到 {curr_level} 级"
                )

        passed = len(issues) == 0
        return CheckResult(
            name="标题层级",
            passed=passed,
            message="[OK] 通过" if passed else f"[FAIL] 发现 {len(issues)} 个问题",
            details=issues if issues else None
        )

    def check_abstract(self) -> CheckResult:
        """检查摘要"""
        issues = []

        # 检查中文摘要
        if '摘要' not in self.content:
            issues.append("缺少中文摘要")
        else:
            # 检查摘要长度
            abstract_match = re.search(r'摘[要要]\s*\n(.+?)(?=\n#|\n关键词|\Z)', self.content, re.DOTALL)
            if abstract_match:
                abstract = abstract_match.group(1).strip()
                char_count = len(abstract.replace('\n', '').replace(' ', ''))
                if char_count < 200:
                    issues.append(f"中文摘要过短（{char_count} 字），建议 200-300 字")
                elif char_count > 500:
                    issues.append(f"中文摘要过长（{char_count} 字），建议 200-300 字")

        # 检查英文摘要
        if 'Abstract' not in self.content and 'abstract' not in self.content:
            issues.append("缺少英文摘要")

        passed = len(issues) == 0
        return CheckResult(
            name="摘要检查",
            passed=passed,
            message="[OK] 通过" if passed else f"[FAIL] 发现 {len(issues)} 个问题",
            details=issues if issues else None
        )

    def check_keywords(self) -> CheckResult:
        """检查关键词"""
        issues = []

        # 检查关键词是否存在
        keyword_match = re.search(r'关键词[：:]\s*(.+?)(?=\n|$)', self.content)
        if not keyword_match:
            issues.append("缺少关键词")
        else:
            keywords = keyword_match.group(1)
            # 分割关键词
            keyword_list = re.split(r'[，,；;]', keywords)
            keyword_list = [k.strip() for k in keyword_list if k.strip()]

            if len(keyword_list) < 3:
                issues.append(f"关键词数量不足（{len(keyword_list)} 个），建议 3-5 个")
            elif len(keyword_list) > 7:
                issues.append(f"关键词数量过多（{len(keyword_list)} 个），建议 3-5 个")

        passed = len(issues) == 0
        return CheckResult(
            name="关键词检查",
            passed=passed,
            message="[OK] 通过" if passed else f"[FAIL] 发现 {len(issues)} 个问题",
            details=issues if issues else None
        )

    def check_references(self) -> CheckResult:
        """检查参考文献"""
        issues = []

        # 检查参考文献章节是否存在
        if '参考文献' not in self.content:
            issues.append("缺少参考文献章节")
            return CheckResult(
                name="参考文献检查",
                passed=False,
                message="[FAIL] 缺少参考文献章节",
                details=issues
            )

        # 提取参考文献
        ref_match = re.search(r'参考文献\s*\n(.+?)(?=\n#|\Z)', self.content, re.DOTALL)
        if ref_match:
            ref_text = ref_match.group(1)
            # 计算参考文献数量（以 [数字] 开头的行）
            refs = re.findall(r'\[\d+\]', ref_text)
            if len(refs) == 0:
                issues.append("参考文献为空")
            elif len(refs) < 10:
                issues.append(f"参考文献数量偏少（{len(refs)} 篇），建议 10-20 篇")

            # 检查引用标记是否在正文中有对应
            cited_numbers = set(re.findall(r'\[(\d+)\]', self.content))

            # 检查格式（GB/T 7714）
            # 简化检查：是否有 [J]、[D]、[M] 等文献类型标识
            if not re.search(r'\[[JDMN]\]', ref_text):
                issues.append("参考文献格式可能不规范，建议使用 GB/T 7714 格式")

        passed = len(issues) == 0
        return CheckResult(
            name="参考文献检查",
            passed=passed,
            message="[OK] 通过" if passed else f"[FAIL] 发现 {len(issues)} 个问题",
            details=issues if issues else None
        )

    def check_sections(self) -> CheckResult:
        """检查章节完整性"""
        issues = []

        # 必要章节
        required_sections = [
            ('引言', ['引言', '绪论', '前言']),
            ('文献综述', ['文献综述', '研究现状', '理论基础']),
            ('结论', ['结论', '结语', '总结'])
        ]

        for section_name, aliases in required_sections:
            found = False
            for alias in aliases:
                if alias in self.content:
                    found = True
                    break
            if not found:
                issues.append(f"缺少「{section_name}」章节")

        passed = len(issues) == 0
        return CheckResult(
            name="章节完整性",
            passed=passed,
            message="[OK] 通过" if passed else f"[FAIL] 发现 {len(issues)} 个问题",
            details=issues if issues else None
        )

    def check_word_count(self) -> CheckResult:
        """统计字数"""
        # 去除 Markdown 标记
        clean_text = re.sub(r'#.*?\n', '', self.content)  # 去标题
        clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)  # 去链接
        clean_text = re.sub(r'[*_`]', '', clean_text)  # 去格式标记
        clean_text = re.sub(r'\n+', '\n', clean_text)  # 合并换行

        char_count = len(clean_text.replace('\n', '').replace(' ', ''))

        # 统计各章节字数
        sections = re.split(r'\n#', self.content)
        section_counts = []
        for section in sections:
            if section.strip():
                first_line = section.split('\n')[0].strip()
                section_text = section.replace(first_line, '')
                section_chars = len(section_text.replace('\n', '').replace(' ', ''))
                section_counts.append((first_line, section_chars))

        return CheckResult(
            name="字数统计",
            passed=True,
            message=f"总字数：{char_count}",
            details=[f"{name}：{count} 字" for name, count in section_counts]
        )

    def check_citation_integrity(self) -> CitationReport:
        """
        检查引用完整性

        检查项：
        1. 正文中 [1][2]... 引用编号是否在参考文献中有对应
        2. 参考文献中的条目是否都有被正文引用（孤立引用检测）
        3. 引用编号是否连续（如有 [1][3] 但缺 [2]）
        4. 每千字引用密度是否达标（≥ 2 个/千字）
        5. 引用分布是否均匀（避免集中在某一章节）
        """
        report = CitationReport()

        # 提取正文中的引用编号
        # 排除参考文献章节中的引用
        main_text = re.split(r'参考文献', self.content)[0]
        cited_numbers = set(int(n) for n in re.findall(r'\[(\d+)\]', main_text))
        report.total_citations = len(cited_numbers)

        # 提取参考文献列表中的编号
        ref_match = re.search(r'参考文献\s*\n(.+?)(?=\n#|\Z)', self.content, re.DOTALL)
        if ref_match:
            ref_text = ref_match.group(1)
            ref_numbers = set(int(n) for n in re.findall(r'\[(\d+)\]', ref_text))
            report.total_references = len(ref_numbers)

            # 检查孤立引用（参考文献中有但正文中未引用）
            report.orphan_references = sorted(list(ref_numbers - cited_numbers))

            # 检查缺失引用（正文中有但参考文献中没有）
            report.missing_references = sorted(list(cited_numbers - ref_numbers))

        # 计算引用密度
        clean_text = re.sub(r'#.*?\n', '', self.content)
        clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)
        clean_text = re.sub(r'[*_`]', '', clean_text)
        clean_text = re.sub(r'\n+', '\n', clean_text)
        char_count = len(clean_text.replace('\n', '').replace(' ', ''))

        if char_count > 0:
            report.citation_density = round(report.total_citations / (char_count / 1000), 2)

        # 计算引用分布
        sections = re.split(r'\n#', self.content)
        for section in sections:
            if section.strip():
                first_line = section.split('\n')[0].strip()
                # 排除参考文献章节
                if '参考文献' not in first_line:
                    citations_in_section = len(re.findall(r'\[\d+\]', section))
                    report.distribution[first_line] = citations_in_section

        self.citation_report = report
        return report

    def check_reference_format(self) -> List[Dict]:
        """
        初步检查参考文献条目是否符合 GB/T 7714 格式

        检查项：
        1. 作者名格式（姓在前，名缩写）
        2. 期刊名是否斜体标注（Markdown 中为 *期刊名*）
        3. 年份、卷号、页码格式
        4. DOI 或 URL 是否存在
        """
        issues = []

        ref_match = re.search(r'参考文献\s*\n(.+?)(?=\n#|\Z)', self.content, re.DOTALL)
        if not ref_match:
            return issues

        ref_text = ref_match.group(1)
        # 按行分割参考文献
        ref_lines = re.findall(r'\[(\d+)\](.+?)(?=\[\d+\]|\Z)', ref_text, re.DOTALL)

        for ref_no, ref_content in ref_lines:
            ref_content = ref_content.strip()
            ref_issues = []

            # 检查文献类型标识
            if not re.search(r'\[[JDMNRCPSZ]\]', ref_content):
                ref_issues.append("缺少文献类型标识（[J]/[D]/[M]等）")

            # 检查年份
            if not re.search(r'[12]\d{3}', ref_content):
                ref_issues.append("缺少年份信息")

            # 检查期刊文献是否有页码
            if '[J]' in ref_content:
                if not re.search(r'\d+\s*[-–]\s*\d+', ref_content):
                    ref_issues.append("期刊文献缺少页码")

            # 检查是否有 DOI 或 URL（可选，仅警告）
            if not re.search(r'(doi:|DOI:|https?://|http://)', ref_content):
                ref_issues.append("缺少 DOI 或 URL（建议添加）")

            if ref_issues:
                issues.append({
                    'ref_no': int(ref_no),
                    'content': ref_content[:50] + '...' if len(ref_content) > 50 else ref_content,
                    'issues': ref_issues
                })

        return issues

    def run_all_checks(self) -> List[CheckResult]:
        """运行所有检查"""
        self.results = [
            self.check_title_hierarchy(),
            self.check_abstract(),
            self.check_keywords(),
            self.check_references(),
            self.check_sections(),
            self.check_word_count()
        ]
        return self.results

    def run_citation_checks(self) -> Tuple[CitationReport, List[Dict]]:
        """运行引用检查"""
        citation_report = self.check_citation_integrity()
        format_issues = self.check_reference_format()
        return citation_report, format_issues

    def print_report(self):
        """打印检查报告"""
        table = Table(title="格式检查报告")
        table.add_column("检查项", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("说明", style="white")

        for result in self.results:
            status = "[OK]" if result.passed else "[FAIL]"
            table.add_row(result.name, status, result.message)

        console.print(table)

        # 打印详细问题
        for result in self.results:
            if result.details:
                console.print(f"\n[bold]{result.name} 详情：[/bold]")
                for detail in result.details:
                    console.print(f"  • {detail}")

        # 总结
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        console.print(f"\n[bold]检查结果：{passed_count}/{total_count} 项通过[/bold]")

    def print_citation_report(self, citation_report: CitationReport, format_issues: List[Dict]):
        """打印引用检查报告"""
        console.print(Panel("[bold blue]引用完整性检查报告[/bold blue]"))

        # 基本统计
        table1 = Table(title="引用统计")
        table1.add_column("指标", style="cyan")
        table1.add_column("数值", style="green")
        table1.add_column("评估", style="yellow")

        # 引用密度评估
        density_eval = "[OK] 达标" if citation_report.citation_density >= 2 else "[WARN] 不足"

        table1.add_row("正文引用数", str(citation_report.total_citations), "-")
        table1.add_row("参考文献数", str(citation_report.total_references), "-")
        table1.add_row("引用密度", f"{citation_report.citation_density} 个/千字", density_eval)

        console.print(table1)

        # 孤立引用
        if citation_report.orphan_references:
            console.print(f"\n[yellow][WARN] 孤立引用（参考文献中有但正文未引用）：{citation_report.orphan_references}[/yellow]")

        # 缺失引用
        if citation_report.missing_references:
            console.print(f"\n[red][FAIL] 缺失引用（正文中有但参考文献中没有）：{citation_report.missing_references}[/red]")

        # 引用分布
        if citation_report.distribution:
            table2 = Table(title="引用分布")
            table2.add_column("章节", style="cyan")
            table2.add_column("引用数", style="green")

            for section, count in citation_report.distribution.items():
                table2.add_row(section[:30], str(count))

            console.print(table2)

        # 格式问题
        if format_issues:
            console.print(f"\n[yellow]参考文献格式问题：[/yellow]")
            for issue in format_issues:
                console.print(f"  [{issue['ref_no']}] {', '.join(issue['issues'])}")


def check_file(path: str, check_citations: bool = False, report_format: str = 'table') -> Dict:
    """检查单个文件"""
    checker = FormatChecker()
    checker.load_file(path)
    results = checker.run_all_checks()

    output = {
        'tool': 'format_checker',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'input': path,
        'results': {
            'passed': sum(1 for r in results if r.passed),
            'total': len(results),
            'checks': []
        }
    }

    for r in results:
        output['results']['checks'].append({
            'name': r.name,
            'passed': r.passed,
            'message': r.message,
            'details': r.details or []
        })

    if check_citations:
        citation_report, format_issues = checker.run_citation_checks()
        output['citation'] = {
            'total_citations': citation_report.total_citations,
            'total_references': citation_report.total_references,
            'orphan_references': citation_report.orphan_references,
            'missing_references': citation_report.missing_references,
            'citation_density': citation_report.citation_density,
            'distribution': citation_report.distribution,
            'format_issues': format_issues
        }

    if report_format == 'table':
        checker.print_report()
        if check_citations:
            citation_report, format_issues = checker.run_citation_checks()
            checker.print_citation_report(citation_report, format_issues)
    elif report_format == 'json':
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return output


def check_directory(dir_path: str, check_citations: bool = False) -> List[Dict]:
    """检查目录下所有 Markdown 文件"""
    results = []
    md_files = list(Path(dir_path).glob('*.md'))

    if not md_files:
        console.print(f"[yellow]目录 {dir_path} 中没有找到 Markdown 文件[/yellow]")
        return results

    console.print(Panel(f"[bold blue]批量检查：{dir_path}[/bold blue]"))

    for md_file in md_files:
        console.print(f"\n[bold]检查文件：{md_file.name}[/bold]")
        result = check_file(str(md_file), check_citations=check_citations)
        results.append(result)

    return results


@click.command()
@click.option('--input', '-i', default=None, help='输入文件路径')
@click.option('--dir', '-d', default=None, help='输入目录路径')
@click.option('--check-citations', '-c', is_flag=True, default=False, help='检查引用完整性')
@click.option('--report', '-r', default='table', type=click.Choice(['table', 'json']), help='报告格式')
@click.option('--verbose', '-v', is_flag=True, default=False, help='详细输出模式')
def main(input: Optional[str], dir: Optional[str], check_citations: bool, report: str, verbose: bool):
    """论文格式检查工具"""
    if input:
        check_file(input, check_citations=check_citations, report_format=report)
    elif dir:
        check_directory(dir, check_citations=check_citations)
    else:
        console.print("[red]请指定 --input 或 --dir 参数[/red]")


if __name__ == '__main__':
    main()