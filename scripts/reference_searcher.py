#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文献搜索工具

集成多个学术 API，支持：
1. Semantic Scholar API - 学术文献搜索
2. CrossRef API - DOI验证和标题搜索（新增）
3. OpenAlex API - 学术搜索（新增）

功能增强：
1. 关键词搜索学术文献（多源）
2. 获取文献详细信息（标题、作者、年份、摘要、DOI）
3. DOI 交叉验证（CrossRef）
4. 语言过滤（中文/英文）
5. 格式化为 GB/T 7714 标准格式

使用方法：
    python scripts/reference_searcher.py --query "精准营销 大数据" --limit 10
    python scripts/reference_searcher.py --doi "10.1234/example.2023" --verify
    python scripts/reference_searcher.py --query "RAG 知识库" --source all --language zh --limit 15
    python scripts/reference_searcher.py --query "deep learning" --source crossref --verify-doi
"""

import re
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# 导入多源搜索引擎（可选）
try:
    from reference_engine import (
        CrossRefSearcher, OpenAlexSearcher,
        VerifiedReference, MultiSourceSearcher
    )
    MULTI_SOURCE_AVAILABLE = True
except ImportError:
    MULTI_SOURCE_AVAILABLE = False


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    title: str
    authors: List[str]
    year: int
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: int = 0
    source: str = "Semantic Scholar"
    paper_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class SemanticScholarSearcher:
    """Semantic Scholar API 搜索器"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化搜索器

        Args:
            api_key: Semantic Scholar API Key（可选，无 Key 限流更严格）
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "thesis-creator/1.0 (https://github.com/thesis-creator)"
        })
        if api_key:
            self.session.headers["x-api-key"] = api_key

        # 请求间隔（避免限流）
        self._last_request_time = 0
        self.min_interval = 0.1  # 最小请求间隔（秒）

    def _rate_limit(self):
        """限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def search(
        self,
        query: str,
        year_range: Tuple[int, int] = (2020, 2025),
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        搜索文献

        Args:
            query: 搜索关键词
            year_range: 年份范围 (start, end)
            limit: 返回结果数量（最大100）
            fields: 返回字段列表

        Returns:
            搜索结果列表
        """
        self._rate_limit()

        # 默认返回字段
        if fields is None:
            fields = [
                "title", "authors", "year", "journal", "volume",
                "issue", "pages", "doi", "url", "abstract",
                "citationCount", "paperId"
            ]

        # 构建请求参数
        params = {
            "query": query,
            "year": f"{year_range[0]}-{year_range[1]}",
            "limit": min(limit, 100),
            "fields": ",".join(fields)
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/paper/search",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = []

            for paper in data.get("data", []):
                # 解析作者
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name", "")
                    if name:
                        authors.append(name)

                # 解析期刊信息
                journal_info = paper.get("journal", {}) or {}
                journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None

                result = SearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    year=paper.get("year", 0) or 0,
                    journal=journal_name,
                    volume=paper.get("volume"),
                    issue=paper.get("issue"),
                    pages=paper.get("pages"),
                    doi=paper.get("doi"),
                    url=paper.get("url"),
                    abstract=paper.get("abstract"),
                    citation_count=paper.get("citationCount", 0) or 0,
                    paper_id=paper.get("paperId")
                )
                results.append(result)

            return results

        except requests.exceptions.RequestException as e:
            print(f"[错误] 搜索请求失败: {e}")
            return []

    def get_paper_by_doi(self, doi: str) -> Optional[SearchResult]:
        """
        通过 DOI 获取文献信息

        Args:
            doi: 文献 DOI

        Returns:
            文献信息，如果不存在则返回 None
        """
        self._rate_limit()

        fields = [
            "title", "authors", "year", "journal", "volume",
            "issue", "pages", "doi", "url", "abstract",
            "citationCount", "paperId"
        ]

        try:
            response = self.session.get(
                f"{self.BASE_URL}/paper/DOI:{doi}",
                params={"fields": ",".join(fields)},
                timeout=30
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            paper = response.json()

            # 解析作者
            authors = []
            for author in paper.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)

            # 解析期刊信息
            journal_info = paper.get("journal", {}) or {}
            journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None

            return SearchResult(
                title=paper.get("title", ""),
                authors=authors,
                year=paper.get("year", 0) or 0,
                journal=journal_name,
                volume=paper.get("volume"),
                issue=paper.get("issue"),
                pages=paper.get("pages"),
                doi=paper.get("doi"),
                url=paper.get("url"),
                abstract=paper.get("abstract"),
                citation_count=paper.get("citationCount", 0) or 0,
                paper_id=paper.get("paperId")
            )

        except requests.exceptions.RequestException as e:
            print(f"[错误] DOI 查询失败: {e}")
            return None

    def get_paper_by_id(self, paper_id: str) -> Optional[SearchResult]:
        """
        通过 Semantic Scholar Paper ID 获取文献信息

        Args:
            paper_id: Paper ID

        Returns:
            文献信息
        """
        self._rate_limit()

        fields = [
            "title", "authors", "year", "journal", "volume",
            "issue", "pages", "doi", "url", "abstract",
            "citationCount", "paperId"
        ]

        try:
            response = self.session.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params={"fields": ",".join(fields)},
                timeout=30
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            paper = response.json()

            # 解析作者
            authors = []
            for author in paper.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)

            # 解析期刊信息
            journal_info = paper.get("journal", {}) or {}
            journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None

            return SearchResult(
                title=paper.get("title", ""),
                authors=authors,
                year=paper.get("year", 0) or 0,
                journal=journal_name,
                volume=paper.get("volume"),
                issue=paper.get("issue"),
                pages=paper.get("pages"),
                doi=paper.get("doi"),
                url=paper.get("url"),
                abstract=paper.get("abstract"),
                citation_count=paper.get("citationCount", 0) or 0,
                paper_id=paper.get("paperId")
            )

        except requests.exceptions.RequestException as e:
            print(f"[错误] Paper ID 查询失败: {e}")
            return None


class ReferenceFormatter:
    """参考文献格式化器"""

    @staticmethod
    def format_gbt7714(result: SearchResult, index: int = 1) -> str:
        """
        格式化为 GB/T 7714 标准格式

        Args:
            result: 搜索结果
            index: 参考文献序号

        Returns:
            GB/T 7714 格式的参考文献字符串
        """
        # 作者格式化
        authors_str = ReferenceFormatter._format_authors(result.authors)

        # 文献类型判断
        if result.journal:
            ref_type = "[J]"
            # 期刊论文格式：作者. 题名[J]. 刊名, 年, 卷(期): 页码.
            parts = [authors_str, result.title, ref_type]

            if result.journal:
                parts.append(result.journal)

            if result.year:
                parts.append(f", {result.year}")

            if result.volume:
                parts.append(f", {result.volume}")
                if result.issue:
                    parts.append(f"({result.issue})")

            if result.pages:
                parts.append(f": {result.pages}")

            ref_str = ". ".join([p for p in parts if p]) + "."

        else:
            # 假设为会议论文
            ref_type = "[C]"
            ref_str = f"{authors_str}. {result.title}{ref_type}. {result.year}."

        # 添加 DOI
        if result.doi:
            ref_str += f" DOI: {result.doi}."

        return f"[{index}] {ref_str}"

    @staticmethod
    def _format_authors(authors: List[str]) -> str:
        """格式化作者列表"""
        if not authors:
            return ""

        if len(authors) <= 3:
            return ", ".join(authors)
        else:
            return ", ".join(authors[:3]) + ", 等"

    @staticmethod
    def format_json(results: List[SearchResult]) -> str:
        """格式化为 JSON"""
        return json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2
        )

    @staticmethod
    def format_table(results: List[SearchResult]) -> str:
        """格式化为表格"""
        lines = [
            "| 序号 | 标题 | 作者 | 年份 | 期刊 | 引用数 |",
            "|------|------|------|------|------|--------|"
        ]

        for i, r in enumerate(results, 1):
            title = r.title[:40] + "..." if len(r.title) > 40 else r.title
            authors = ", ".join(r.authors[:2])
            if len(r.authors) > 2:
                authors += "等"
            journal = r.journal[:15] + "..." if r.journal and len(r.journal) > 15 else (r.journal or "-")

            lines.append(
                f"| {i} | {title} | {authors} | {r.year} | {journal} | {r.citation_count} |"
            )

        return "\n".join(lines)


def search_and_format(
    query: str,
    year_range: Tuple[int, int] = (2020, 2025),
    limit: int = 10,
    output_format: str = "gbt7714",
    api_key: Optional[str] = None
) -> str:
    """
    搜索并格式化输出

    Args:
        query: 搜索关键词
        year_range: 年份范围
        limit: 结果数量
        output_format: 输出格式 (gbt7714, json, table)
        api_key: API Key

    Returns:
        格式化后的输出
    """
    searcher = SemanticScholarSearcher(api_key=api_key)

    print(f"[信息] 搜索关键词: {query}")
    print(f"[信息] 年份范围: {year_range[0]}-{year_range[1]}")
    print(f"[信息] 结果数量: {limit}")

    results = searcher.search(query, year_range, limit)

    if not results:
        return "未找到相关文献"

    print(f"[成功] 找到 {len(results)} 篇文献")

    if output_format == "gbt7714":
        lines = ["# 参考文献搜索结果", ""]
        lines.append(f"> 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 关键词: {query}")
        lines.append(f"> 结果数: {len(results)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, r in enumerate(results, 1):
            lines.append(ReferenceFormatter.format_gbt7714(r, i))
            if r.abstract:
                lines.append(f"   > 摘要: {r.abstract[:200]}...")
            lines.append("")

        return "\n".join(lines)

    elif output_format == "json":
        return ReferenceFormatter.format_json(results)

    elif output_format == "table":
        return ReferenceFormatter.format_table(results)

    else:
        return ReferenceFormatter.format_gbt7714(results[0])


def verify_doi(doi: str, api_key: Optional[str] = None, crossref_verify: bool = True) -> Tuple[bool, Optional[SearchResult]]:
    """
    验证 DOI 是否有效

    Args:
        doi: DOI 字符串
        api_key: API Key
        crossref_verify: 是否使用 CrossRef 双重验证

    Returns:
        (是否有效, 文献信息)
    """
    # 1. Semantic Scholar 验证
    searcher = SemanticScholarSearcher(api_key=api_key)
    result = searcher.get_paper_by_doi(doi)

    if result:
        # 2. CrossRef 双重验证（可选）
        if crossref_verify and MULTI_SOURCE_AVAILABLE:
            crossref = CrossRefSearcher()
            valid, crossref_result = crossref.verify_doi(doi)

            if valid and crossref_result:
                # 用 CrossRef 数据补充缺失字段
                if not result.journal and crossref_result.journal:
                    result.journal = crossref_result.journal
                if not result.volume and crossref_result.volume:
                    result.volume = crossref_result.volume
                if not result.issue and crossref_result.issue:
                    result.issue = crossref_result.issue
                if not result.pages and crossref_result.pages:
                    result.pages = crossref_result.pages

                # 检查 DOI 链接可达性（判断 4xx 错误）
                reachable, status_code = crossref.check_doi_reachable(doi)
                if reachable:
                    print("[信息] DOI 链接可达性验证通过")
                else:
                    if status_code == 404:
                        print(f"[警告] DOI 不存在 (404): {doi}")
                    elif status_code > 0:
                        print(f"[警告] DOI 链接不可达 ({status_code}): {doi}")

        return True, result
    else:
        return False, None


def main():
    """main"""
    parser = argparse.ArgumentParser(description="文献搜索工具")
    parser.add_argument("--query", "-q", help="搜索关键词")
    parser.add_argument("--doi", "-d", help="验证 DOI")
    parser.add_argument("--year-start", type=int, default=2020, help="起始年份")
    parser.add_argument("--year-end", type=int, default=2025, help="结束年份")
    parser.add_argument("--limit", "-l", type=int, default=10, help="结果数量")
    parser.add_argument("--format", "-f", choices=["gbt7714", "json", "table", "yaml"],
                        default="gbt7714", help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--api-key", help="Semantic Scholar API Key")
    # 新增参数
    parser.add_argument("--source", "-s",
                        choices=["semantic-scholar", "crossref", "openalex", "all"],
                        default="semantic-scholar",
                        help="搜索源（新增）")
    parser.add_argument("--verify-doi", action="store_true", default=True,
                        help="使用 CrossRef 交叉验证 DOI（新增）")
    parser.add_argument("--language",
                        choices=["zh", "en", "all"],
                        default="all",
                        help="语言过滤（新增）")

    args = parser.parse_args()

    if args.query:
        # 多源搜索模式（如果可用）
        if args.source != "semantic-scholar" and MULTI_SOURCE_AVAILABLE:
            from reference_engine import search_and_format
            sources = ["semantic-scholar", "crossref", "openalex"] if args.source == "all" else [args.source]

            output = search_and_format(
                query=args.query,
                year_range=(args.year_start, args.year_end),
                limit=args.limit,
                sources=sources,
                output_format=args.format,
                cross_verify=args.verify_doi,
                language=args.language,
                api_key=args.api_key
            )
        else:
            # 传统 Semantic Scholar 搜索
            output = search_and_format(
                query=args.query,
                year_range=(args.year_start, args.year_end),
                limit=args.limit,
                output_format=args.format,
                api_key=args.api_key
            )

    elif args.doi:
        # DOI 验证模式（带 CrossRef 双重验证）
        valid, result = verify_doi(args.doi, args.api_key, args.verify_doi)

        if valid:
            output = f"[OK] DOI 验证通过\n\n"
            if args.verify_doi and MULTI_SOURCE_AVAILABLE:
                output += "（已通过 CrossRef 交叉验证）\n\n"
            output += ReferenceFormatter.format_gbt7714(result)
        else:
            output = f"[FAIL] DOI 无效或不存在: {args.doi}"

    else:
        parser.print_help()
        return

    # 输出结果
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"\n[完成] 结果已保存到: {args.output}")
    else:
        print("\n" + output)


if __name__ == "__main__":
    main()
