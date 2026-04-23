# -*- coding: utf-8 -*-
"""
参考文献验证工具

功能：
1. 解析论文中的参考文献
2. 检查格式是否符合 GB/T 7714 标准
3. 检测可疑作者名（占位符）
4. 检查 DOI 有效性（可选）
5. 分析文献时间分布
6. 生成验证报告

使用方法：
    python reference_validator.py input.md --output reports/
"""

import re
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import time

# 导入日志模块
try:
    from logger import get_logger, init_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger():
        return logging.getLogger()
    def init_logger():
        return get_logger()

# 导入在线验证模块
try:
    from reference_searcher import SemanticScholarSearcher, verify_doi
except ImportError:
    SemanticScholarSearcher = None
    verify_doi = None

# 导入多源验证模块（新增）
try:
    from reference_engine import CrossRefSearcher
    CROSSREF_AVAILABLE = True
except ImportError:
    CROSSREF_AVAILABLE = False


@dataclass
class Reference:
    """参考文献数据结构"""
    index: int
    raw_text: str
    ref_type: str  # 期刊[J], 会议[C], 图书[M], 学位论文[D], 标准[S], 报告[R]
    authors: List[str]
    title: str
    journal: Optional[str]
    year: Optional[int]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    publisher: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    is_valid: bool = True
    issues: List[str] = None
    hallucination_risk: bool = False  # 新增：幻觉风险标记
    verified_online: bool = False     # 新增：已在线验证标记

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class ReferenceValidator:
    """参考文献验证器"""

    # GB/T 7714 参考文献类型标识
    REF_TYPES = {
        'M': '图书',
        'J': '期刊',
        'C': '会议论文',
        'D': '学位论文',
        'P': '专利',
        'S': '标准',
        'R': '报告',
        'N': '报纸',
        'Z': '其他'
    }

    # 可疑作者名模式
    SUSPICIOUS_AUTHORS = [
        r'^张三$', r'^李四$', r'^王五$', r'^赵六$', r'^小明',
        r'^作者$', r'^佚名$', r'^未知$', r'^XXX$', r'^xxx$',
        r'^测试', r'^示例', r'^范本', r'^模板',
    ]

    # GB/T 7714 格式正则表达式（简化版）
    GB_PATTERN = re.compile(
        r'\[(\d+)\]\s*'  # 序号
        r'(.+?)\s*'      # 作者
        r'\[([JCMCDPSRNZ])\]\s*'  # 文献类型
        r'(.+?)[，,.]\s*'  # 标题
        r'(.+?)'         # 出版信息
        r'(?:[:：]\s*(\d+-\d+))?\s*'  # 页码
        r'(?:\.?\s*(?:DOI[:：]?\s*)?([10]\.\d{4,}/[^\s]+))?\s*'  # DOI
        r'\.?',
        re.IGNORECASE
    )

    # 更灵活的解析模式
    FLEXIBLE_PATTERN = re.compile(
        r'\[(\d+)\]\s*(.+?)(?:\[([JCMCDPSRNZ])\]|\.|，|,)\s*(.+?)(?:\.|，|,)\s*(.+?)(?:\.|$)',
        re.DOTALL
    )

    # 年份提取模式
    YEAR_PATTERN = re.compile(r'[，,.\s](\d{4})[，,.\s]')

    def __init__(self, output_dir: str = "reports", enable_online_validation: bool = True):
        """
        初始化验证器

        Args:
            output_dir: 输出目录
            enable_online_validation: 是否启用在线验证（需网络连接）
        """
        self.logger = get_logger()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_online_validation = enable_online_validation

        # 优先初始化 CrossRef 搜索器（无限流问题，完全免费）
        if enable_online_validation and CROSSREF_AVAILABLE:
            self.crossref_searcher = CrossRefSearcher()
        else:
            self.crossref_searcher = None

        # Semantic Scholar 作为备用（可能触发429限流）
        if enable_online_validation and SemanticScholarSearcher is not None:
            self.searcher = SemanticScholarSearcher()
        else:
            self.searcher = None

        self.references: List[Reference] = []
        self.stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'suspicious_authors': 0,
            'format_issues': 0,
            'missing_info': 0,
            'hallucination_risk': 0,  # 新增：幻觉风险统计
            'online_verified': 0      # 新增：在线验证通过统计
        }

    def parse_references(self, content: str) -> List[Reference]:
        """
        解析文档中的参考文献

        Args:
            content: 文档内容

        Returns:
            参考文献列表
        """
        self.logger.info("开始解析参考文献...")

        # 查找参考文献部分
        ref_section = self._extract_reference_section(content)
        if not ref_section:
            self.logger.warning("未找到参考文献部分")
            return []

        # 按行分割并解析
        lines = ref_section.strip().split('\n')
        current_ref = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测是否为新文献（以 [数字] 开头）
            if re.match(r'^\[\d+\]', line):
                if current_ref:
                    ref = self._parse_single_reference(current_ref)
                    if ref:
                        self.references.append(ref)
                current_ref = line
            else:
                current_ref += " " + line

        # 处理最后一条
        if current_ref:
            ref = self._parse_single_reference(current_ref)
            if ref:
                self.references.append(ref)

        self.stats['total'] = len(self.references)
        self.logger.info(f"共解析到 {len(self.references)} 条参考文献")
        return self.references

    def _extract_reference_section(self, content: str) -> Optional[str]:
        """提取参考文献部分"""
        patterns = [
            r'##\s*参考文献\s*\n([\s\S]+?)(?=\n##|\Z)',
            r'#\s*参考文献\s*\n([\s\S]+?)(?=\n#|\Z)',
            r'\*\*参考文献\*\*\s*\n([\s\S]+?)(?=\n\*\*|\Z)',
            r'参考文献[：:]\s*\n([\s\S]+?)(?=\n\n#|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None

    def _parse_single_reference(self, text: str) -> Optional[Reference]:
        """解析单条参考文献"""
        text = text.strip()

        # 提取序号
        index_match = re.match(r'\[(\d+)\]', text)
        if not index_match:
            return None

        index = int(index_match.group(1))

        # 提取文献类型
        type_match = re.search(r'\[([JCMCDPSRNZ])\]', text)
        ref_type = type_match.group(1) if type_match else 'Z'

        # 提取作者（在第一个标题分隔符之前）
        author_text = text[index_match.end():]
        if type_match:
            author_text = author_text[:author_text.find('[' + ref_type + ']')]

        authors = self._extract_authors(author_text)

        # 提取标题
        title = self._extract_title(text, ref_type)

        # 提取年份
        year_match = self.YEAR_PATTERN.search(text)
        year = int(year_match.group(1)) if year_match else None

        # 提取期刊名
        journal = self._extract_journal(text, ref_type)

        # 提取 DOI
        doi_match = re.search(r'DOI[:：]?\s*([10]\.\d{4,}/[^\s.,]+)', text, re.IGNORECASE)
        doi = doi_match.group(1) if doi_match else None

        # 提取 URL
        url_match = re.search(r'https?://[^\s]+', text)
        url = url_match.group(0) if url_match else None

        return Reference(
            index=index,
            raw_text=text,
            ref_type=ref_type,
            authors=authors,
            title=title,
            journal=journal,
            year=year,
            volume=None,
            issue=None,
            pages=None,
            publisher=None,
            doi=doi,
            url=url
        )

    def _extract_authors(self, author_text: str) -> List[str]:
        """提取作者列表"""
        # 清理文本
        author_text = author_text.strip('.,;，。；')

        # 按分隔符分割
        separators = [',', '，', ';', '；', '、', ' and ', ' AND ']
        authors = [author_text]

        for sep in separators:
            new_authors = []
            for author in authors:
                new_authors.extend(author.split(sep))
            authors = new_authors

        # 清理和过滤
        authors = [a.strip() for a in authors if a.strip()]
        return authors

    def _extract_title(self, text: str, ref_type: str) -> str:
        """提取标题"""
        # 在文献类型标识之后，下一分隔符之前
        type_pos = text.find('[' + ref_type + ']')
        if type_pos == -1:
            return ""

        after_type = text[type_pos + 4:].strip()

        # 标题通常在第一个句号或逗号之前
        title_end_chars = ['.', '。', '，', ',']
        for char in title_end_chars:
            pos = after_type.find(char)
            if pos > 0:
                after_type = after_type[:pos]
                break

        return after_type.strip()

    def _extract_journal(self, text: str, ref_type: str) -> Optional[str]:
        """提取期刊名"""
        if ref_type != 'J':
            return None

        # 期刊名通常在标题之后
        parts = text.split('.,')
        if len(parts) >= 3:
            return parts[2].strip()

        return None

    def _validate_url_content(self, ref: Reference) -> List[str]:
        """
        第二阶段：验证网页链接内容是否符合文献内容

        Args:
            ref: 参考文献对象

        Returns:
            验证发现的问题列表
        """
        issues = []

        if not ref.url:
            return issues

        # 只验证网络文献 [EB/OL] 类型
        if ref.ref_type != 'EB':
            return issues

        try:
            self.logger.info(f"验证 URL 内容: {ref.url}")

            # 发送请求获取网页内容
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(ref.url, headers=headers, timeout=10, allow_redirects=True)

            if response.status_code == 404:
                issues.append(f"网页不存在 (404): {ref.url}")
                ref.hallucination_risk = True
            elif response.status_code >= 400:
                issues.append(f"网页访问失败 ({response.status_code}): {ref.url}")
            elif response.status_code == 200:
                # 检查标题是否在网页内容中出现
                content = response.text.lower()
                if ref.title:
                    title_lower = ref.title.lower()
                    # 提取标题关键词
                    title_keywords = [w for w in title_lower.split() if len(w) > 3]

                    # 检查关键词是否出现在网页中
                    matched_keywords = sum(1 for kw in title_keywords if kw in content)
                    if title_keywords and matched_keywords < len(title_keywords) * 0.3:
                        issues.append(f"网页内容与标题不匹配: '{ref.title}'")
                        ref.hallucination_risk = True
                    else:
                        ref.verified_online = True
                        self.logger.info(f"URL 内容验证通过")

        except requests.exceptions.Timeout:
            issues.append(f"网页访问超时: {ref.url}")
        except requests.exceptions.ConnectionError:
            issues.append(f"网页连接失败: {ref.url}")
        except Exception as e:
            issues.append(f"URL 验证异常: {str(e)}")

        return issues

    def _validate_online(self, ref: Reference) -> List[str]:
        """
        在线验证文献真实性

        优先使用 CrossRef（无限流问题），其次使用 OpenAlex，最后才用 Semantic Scholar

        Args:
            ref: 参考文献对象

        Returns:
            验证发现的问题列表
        """
        issues = []

        # 优先使用 CrossRef（无 API 限流）
        if self.crossref_searcher is None:
            return issues

        # 1. DOI 验证（如果有 DOI）- 优先 CrossRef
        if ref.doi:
            self.logger.info(f"CrossRef 验证 DOI: {ref.doi}")
            crossref_valid, crossref_result = self.crossref_searcher.verify_doi(ref.doi)

            if crossref_valid and crossref_result:
                ref.verified_online = True
                # 验证标题是否匹配
                if ref.title and crossref_result.title:
                    if not self._titles_similar(ref.title, crossref_result.title):
                        issues.append(
                            f"标题不匹配: 原文 '{ref.title}' vs 实际 '{crossref_result.title}'"
                        )
                # 检查 DOI 链接可达性（判断 4xx 错误）
                reachable, status_code = self.crossref_searcher.check_doi_reachable(ref.doi)
                if not reachable:
                    # 404 或其他 4xx/5xx 错误
                    if status_code == 404:
                        issues.append(f"DOI 不存在 (404): https://doi.org/{ref.doi}")
                    elif status_code > 0:
                        issues.append(f"DOI 链接不可达 ({status_code}): https://doi.org/{ref.doi}")
                    else:
                        issues.append(f"DOI 链接无法访问: https://doi.org/{ref.doi}")
                    ref.hallucination_risk = True
                else:
                    self.logger.info(f"DOI 验证通过: {ref.doi}")
            else:
                # CrossRef 验证失败，标记为幻觉风险
                issues.append(f"DOI 无效或不存在: {ref.doi}")
                ref.hallucination_risk = True

        # 2. 标题搜索验证（无 DOI 时）- 使用 CrossRef 搜索
        elif ref.title and len(ref.title) >= 5:
            keywords = self._extract_keywords(ref.title)
            self.logger.info(f"CrossRef 标题搜索验证: {keywords}")

            try:
                # 使用 CrossRef 搜索（无 API Key 限流问题）
                results = self.crossref_searcher.search(keywords, year_range=(2020, 2025), limit=5)

                if not results:
                    issues.append("标题搜索无结果，疑似虚构文献")
                    ref.hallucination_risk = True
                else:
                    # 检查是否有相似标题
                    similar_found = any(
                        self._titles_similar(ref.title, r.title)
                        for r in results if r.title
                    )
                    if not similar_found:
                        issues.append("未找到相似标题，疑似虚构文献")
                        ref.hallucination_risk = True
                    else:
                        ref.verified_online = True
                        self.logger.info(f"标题验证通过")
            except Exception as e:
                self.logger.warning(f"CrossRef 搜索失败: {e}")
                # CrossRef 失败时，尝试 Semantic Scholar 作为备用
                if self.searcher is not None:
                    try:
                        results = self.searcher.search(keywords, limit=5)
                        if results:
                            similar_found = any(
                                self._titles_similar(ref.title, r.title)
                                for r in results if r.title
                            )
                            if similar_found:
                                ref.verified_online = True
                                self.logger.info(f"Semantic Scholar 备用验证通过")
                    except Exception as e2:
                        self.logger.warning(f"Semantic Scholar 搜索也失败: {e2}")

        return issues

    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.6) -> bool:
        """
        判断两个标题是否相似

        Args:
            title1: 第一个标题
            title2: 第二个标题
            threshold: 相似度阈值

        Returns:
            是否相似
        """
        if not title1 or not title2:
            return False

        # 清理标题
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()

        # 完全相同
        if t1 == t2:
            return True

        # 计算词重叠率
        words1 = set(t1.split())
        words2 = set(t2.split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        similarity = len(intersection) / len(union)

        return similarity >= threshold

    def _extract_keywords(self, title: str) -> str:
        """
        从标题中提取关键词用于搜索

        Args:
            title: 文献标题

        Returns:
            搜索关键词
        """
        # 移除常见停用词
        stopwords = {'a', 'an', 'the', 'of', 'and', 'in', 'on', 'for', 'to', 'with',
                    '的', '了', '在', '是', '和', '与', '对', '于', '等', '及',
                    '研究', '分析', '设计', '实现', '基于', '应用'}

        words = title.split()

        # 过滤停用词和短词
        keywords = [
            w for w in words
            if w.lower() not in stopwords and len(w) >= 2
        ]

        # 限制关键词数量
        if len(keywords) > 6:
            keywords = keywords[:6]

        return ' '.join(keywords)

    def validate_all(self) -> Dict:
        """
        验证所有参考文献

        Returns:
            验证统计信息
        """
        self.logger.info("开始验证参考文献...")

        for ref in self.references:
            self._validate_single(ref)

        # 计算统计信息
        self.stats['valid'] = sum(1 for r in self.references if r.is_valid)
        self.stats['invalid'] = self.stats['total'] - self.stats['valid']
        self.stats['suspicious_authors'] = sum(
            1 for r in self.references if any(
                re.match(p, a, re.IGNORECASE) for a in r.authors for p in self.SUSPICIOUS_AUTHORS
            )
        )

        # 新增：幻觉风险统计
        self.stats['hallucination_risk'] = sum(
            1 for r in self.references if r.hallucination_risk
        )
        self.stats['online_verified'] = sum(
            1 for r in self.references if r.verified_online
        )

        self.logger.quality_check(
            "参考文献验证",
            self.stats['invalid'] == 0,
            f"有效: {self.stats['valid']}/{self.stats['total']}, "
            f"幻觉风险: {self.stats['hallucination_risk']}"
        )

        return self.stats

    def _validate_single(self, ref: Reference):
        """
        验证单条参考文献（三阶段验证）

        验证优先级：
        1. 第一阶段：基础检查（排除明显问题）- 格式、占位符作者等
        2. 第二阶段：URL 内容验证（对网络文献 [EB/OL]）
        3. 第三阶段：API 验证（仅对不确定的文献）
        """
        issues = []

        # ========== 第一阶段：基础检查（排除明显问题）==========
        # 检查作者
        for author in ref.authors:
            for pattern in self.SUSPICIOUS_AUTHORS:
                if re.match(pattern, author, re.IGNORECASE):
                    issues.append(f"可疑作者名: {author}")
                    ref.hallucination_risk = True  # 可疑作者直接标记幻觉风险
                    break

        # 检查必填字段
        if not ref.title:
            issues.append("缺少标题")

        if ref.ref_type in ['J', 'C'] and not ref.journal:
            issues.append("缺少期刊/会议名称")

        if not ref.year:
            issues.append("缺少年份")
        elif ref.year > datetime.now().year:
            issues.append(f"年份异常: {ref.year}")
        elif ref.year < 1990:
            issues.append(f"年份过早: {ref.year}")

        # 检查格式
        if not re.match(r'^\[?\d+\]?', ref.raw_text):
            issues.append("序号格式不规范")

        # 检查标题长度
        if ref.title and len(ref.title) < 5:
            issues.append(f"标题过短: {ref.title}")

        # 第一阶段发现严重问题，标记幻觉风险，不再进行后续验证
        if ref.hallucination_risk:
            self.logger.warning(f"[{ref.index}] 第一阶段检出明显问题，跳过后续验证")
            ref.issues = issues
            ref.is_valid = False
            return

        # ========== 第二阶段：URL 内容验证（网络文献）==========
        if self.enable_online_validation and ref.ref_type == 'EB' and ref.url:
            url_issues = self._validate_url_content(ref)
            issues.extend(url_issues)

            # URL 验证失败，标记幻觉风险
            if ref.hallucination_risk:
                self.logger.warning(f"[{ref.index}] URL 内容不匹配，跳过 API 验证")
                ref.issues = issues
                ref.is_valid = False
                return

        # ========== 第三阶段：API 验证（仅对不确定的文献）==========
        # 仅对期刊[J]、会议[C]类型且有 DOI 或标题的文献进行 API 验证
        if self.enable_online_validation and ref.ref_type in ['J', 'C']:
            # 有 DOI 或标题长度足够的才进行 API 验证
            if ref.doi or (ref.title and len(ref.title) >= 10):
                online_issues = self._validate_online(ref)
                issues.extend(online_issues)

                # 标记幻觉风险
                if any('虚构' in i or '无效' in i or '不匹配' in i for i in online_issues):
                    ref.hallucination_risk = True

        ref.issues = issues
        ref.is_valid = len(issues) == 0

        if issues:
            self.logger.warning(f"[{ref.index}] 发现问题: {', '.join(issues)}")

    def analyze_year_distribution(self) -> Dict[int, int]:
        """分析年份分布"""
        distribution = {}

        for ref in self.references:
            if ref.year:
                distribution[ref.year] = distribution.get(ref.year, 0) + 1

        return dict(sorted(distribution.items()))

    def check_recent_ratio(self, years: int = 3) -> Tuple[int, float]:
        """
        检查近年文献占比

        Args:
            years: 近几年的定义

        Returns:
            (数量, 占比)
        """
        current_year = datetime.now().year
        recent_threshold = current_year - years

        recent_count = sum(
            1 for r in self.references
            if r.year and r.year >= recent_threshold
        )

        ratio = recent_count / len(self.references) if self.references else 0
        return recent_count, ratio

    def generate_report(self) -> str:
        """生成验证报告"""
        self.logger.info("生成验证报告...")

        report_lines = [
            "# 参考文献验证报告",
            "",
            f"> 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 一、总体统计",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 参考文献总数 | {self.stats['total']} |",
            f"| 有效文献 | {self.stats['valid']} |",
            f"| 存在问题的文献 | {self.stats['invalid']} |",
            f"| 可疑作者名 | {self.stats['suspicious_authors']} |",
            f"| [WARN] 幻觉风险文献 | {self.stats['hallucination_risk']} |",
            f"| [OK] 在线验证通过 | {self.stats['online_verified']} |",
            "",
        ]

        # 年份分布
        distribution = self.analyze_year_distribution()
        if distribution:
            report_lines.extend([
                "## 二、年份分布",
                "",
                "| 年份 | 数量 |",
                "|------|------|"
            ])
            for year, count in distribution.items():
                report_lines.append(f"| {year} | {count} |")

            # 近年占比
            recent_count, recent_ratio = self.check_recent_ratio(3)
            report_lines.extend([
                "",
                f"**近3年文献**: {recent_count} 篇 ({recent_ratio:.1%})",
                ""
            ])

            if recent_ratio < 0.3:
                report_lines.append("> [WARN] 近3年文献占比低于30%，建议补充最新文献")
            report_lines.append("")

        # 文献类型分布
        type_dist = {}
        for ref in self.references:
            type_name = self.REF_TYPES.get(ref.ref_type, '其他')
            type_dist[type_name] = type_dist.get(type_name, 0) + 1

        if type_dist:
            report_lines.extend([
                "## 三、文献类型分布",
                "",
                "| 类型 | 数量 |",
                "|------|------|"
            ])
            for type_name, count in sorted(type_dist.items(), key=lambda x: -x[1]):
                report_lines.append(f"| {type_name} | {count} |")
            report_lines.append("")

        # 问题文献列表
        problem_refs = [r for r in self.references if not r.is_valid]
        if problem_refs:
            report_lines.extend([
                "## 四、问题文献清单",
                ""
            ])
            for ref in problem_refs:
                report_lines.append(f"### [{ref.index}] {ref.title[:50]}..." if len(ref.title) > 50 else f"### [{ref.index}] {ref.title}")
                report_lines.append("")
                report_lines.append(f"- **问题**: {', '.join(ref.issues)}")
                report_lines.append(f"- **原文**: {ref.raw_text[:100]}..." if len(ref.raw_text) > 100 else f"- **原文**: {ref.raw_text}")
                report_lines.append("")

        # 可疑作者列表
        suspicious_refs = [
            r for r in self.references
            if any(re.match(p, a, re.IGNORECASE) for a in r.authors for p in self.SUSPICIOUS_AUTHORS)
        ]
        if suspicious_refs:
            report_lines.extend([
                "## 五、可疑作者文献",
                "",
                "以下文献的作者名疑似占位符，建议核实：",
                ""
            ])
            for ref in suspicious_refs:
                suspicious_authors = [
                    a for a in ref.authors
                    if any(re.match(p, a, re.IGNORECASE) for p in self.SUSPICIOUS_AUTHORS)
                ]
                report_lines.append(f"- [{ref.index}] 作者: {', '.join(suspicious_authors)}")
            report_lines.append("")

        # 幻觉风险文献列表（新增）
        hallucination_refs = [r for r in self.references if r.hallucination_risk]
        if hallucination_refs:
            report_lines.extend([
                "## 六、[WARN] 幻觉风险文献",
                "",
                "以下文献经在线验证后发现疑似虚构，建议核实或替换：",
                ""
            ])
            for ref in hallucination_refs:
                # 提取幻觉相关的问题
                hallucination_issues = [
                    i for i in ref.issues
                    if '虚构' in i or '无效' in i or '不匹配' in i or '无结果' in i
                ]
                report_lines.append(f"- [{ref.index}] **{ref.title[:40]}{'...' if len(ref.title) > 40 else ''}**")
                report_lines.append(f"  - 问题: {', '.join(hallucination_issues)}")
                if ref.doi:
                    report_lines.append(f"  - DOI: {ref.doi}")
                report_lines.append("")
            report_lines.append("> [WARN] 建议使用 `reference_searcher.py` 搜索真实文献进行替换")

        # 改进建议
        report_lines.extend([
            "## 七、改进建议",
            ""
        ])

        suggestions = []

        if self.stats['total'] < 15:
            suggestions.append("1. 参考文献数量不足（建议≥15篇）")

        if recent_ratio < 0.3:
            suggestions.append("2. 近年文献占比过低，建议补充2-3篇最新文献")

        if suspicious_refs:
            suggestions.append("3. 存在可疑作者名，建议替换为真实文献")

        if problem_refs:
            suggestions.append("4. 部分文献格式不规范，建议检查 GB/T 7714 格式要求")

        # 新增：幻觉风险建议
        if hallucination_refs:
            suggestions.append("5. [WARN] 存在幻觉风险文献，建议核实 DOI 或搜索真实文献替换")

        if self.enable_online_validation and self.stats['online_verified'] < self.stats['total'] * 0.5:
            suggestions.append("6. 在线验证覆盖率不足，建议为更多文献添加 DOI")

        if suggestions:
            report_lines.extend(suggestions)
        else:
            report_lines.append("[OK] 参考文献整体质量良好，无明显问题。")

        report_lines.extend([
            "",
            "---",
            "",
            "*此报告由 thesis-creator 参考文献验证工具自动生成*"
        ])

        return "\n".join(report_lines)

    def export_report(self, format: str = "md") -> str:
        """导出验证报告"""
        report = self.generate_report()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "md":
            output_file = self.output_dir / f"reference_validation_{timestamp}.md"
            output_file.write_text(report, encoding='utf-8')
        elif format == "json":
            output_file = self.output_dir / f"reference_validation_{timestamp}.json"
            data = {
                "timestamp": datetime.now().isoformat(),
                "stats": self.stats,
                "references": [
                    {
                        "index": r.index,
                        "type": r.ref_type,
                        "authors": r.authors,
                        "title": r.title,
                        "year": r.year,
                        "is_valid": r.is_valid,
                        "issues": r.issues
                    }
                    for r in self.references
                ]
            }
            output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            output_file = self.output_dir / f"reference_validation_{timestamp}.txt"
            output_file.write_text(report, encoding='utf-8')

        self.logger.file_operation("write", str(output_file))
        return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="参考文献验证工具")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出目录（默认: thesis-workspace/workspace/reports）")
    parser.add_argument("-f", "--format", default="md", choices=["md", "json", "txt"], help="输出格式")
    parser.add_argument("--validate-online", action="store_true", default=True,
                        help="启用在线验证（检查 DOI 和标题真实性）")
    parser.add_argument("--offline", action="store_true",
                        help="禁用在线验证（仅检查格式）")

    args = parser.parse_args()

    # 确定是否启用在线验证
    enable_online = args.validate_online and not args.offline

    # 确定输出目录（自动检测 thesis-workspace）
    output_dir = args.output
    if output_dir is None:
        # 尝试检测 thesis-workspace 目录
        cwd = Path.cwd()
        workspace_candidates = [
            cwd / "thesis-workspace" / "workspace" / "reports",
            cwd.parent / "thesis-workspace" / "workspace" / "reports",
            Path(__file__).parent.parent.parent.parent / "thesis-workspace" / "workspace" / "reports",
        ]
        for candidate in workspace_candidates:
            if candidate.parent.parent.exists():
                output_dir = str(candidate)
                break
        if output_dir is None:
            output_dir = "reports"  # fallback

    # 初始化日志（自动检测 thesis-workspace/logs 目录）
    init_logger(session_name="reference_validator")
    logger = get_logger()

    logger.step("参考文献验证", "start")

    # 读取输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"文件不存在: {args.input}")
        return

    content = input_path.read_text(encoding='utf-8')

    # 创建验证器（支持在线验证）
    validator = ReferenceValidator(
        output_dir=output_dir,
        enable_online_validation=enable_online
    )

    # 解析参考文献
    logger.step("解析参考文献", "start")
    refs = validator.parse_references(content)
    logger.step("解析参考文献", "complete")

    # 验证
    logger.step("验证参考文献", "start")
    stats = validator.validate_all()
    logger.step("验证参考文献", "complete")

    # 导出报告
    report_file = validator.export_report(format=args.format)

    print(f"\n[OK] 验证完成！")
    print(f"   参考文献总数: {stats['total']}")
    print(f"   有效文献: {stats['valid']}")
    print(f"   问题文献: {stats['invalid']}")
    print(f"   可疑作者: {stats['suspicious_authors']}")
    if enable_online:
        print(f"   [WARN] 幻觉风险文献: {stats['hallucination_risk']}")
        print(f"   [OK] 在线验证通过: {stats['online_verified']}")
    print(f"\n[文档] 验证报告: {report_file}")

    # 提示幻觉风险
    if stats['hallucination_risk'] > 0:
        print(f"\n[WARN] 发现 {stats['hallucination_risk']} 篇疑似虚构文献，请查看报告详情！")

    logger.step("参考文献验证", "complete")


if __name__ == "__main__":
    main()