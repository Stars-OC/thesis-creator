# -*- coding: utf-8 -*-
"""
多源学术搜索引擎（Multi-Source Reference Engine）

整合三个免费学术 API：
1. Semantic Scholar - 学术文献搜索（有API Key更稳定）
2. CrossRef - DOI验证和标题搜索（完全免费）
3. OpenAlex - 学术搜索（完全免费，中文文献覆盖较好）

核心功能：
- 多源聚合搜索：同时查询多个API，去重合并结果
- DOI交叉验证：使用CrossRef验证DOI真实性
- 结果排序：按相关度×引用数×时效性加权排序
- 生成可点击DOI链接

使用方法：
    python scripts/reference_engine.py --query "deep learning recommendation" --limit 10
    python scripts/reference_engine.py --verify-doi "10.18653/v1/2020.naacl-main.13"
    python scripts/reference_engine.py --query "RAG 知识库" --source all --language zh --limit 15
"""

import re
import math
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from difflib import SequenceMatcher


def safe_print(*args, **kwargs):
    """在 Windows 控制台编码不支持时，安全降级输出。"""
    try:
        __import__('builtins').print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        replacements = {
            "✅": "[OK]",
            "❌": "[FAIL]",
            "⚠️": "[WARN]",
            "🔍": "[SEARCH]",
            "📊": "[STAT]",
            "⏱️": "[TIME]",
            "📝": "[NOTE]",
            "📚": "[REF]",
            "⏳": "[WAIT]",
            "💡": "[TIP]",
            "🔄": "[RUN]",
            "⬜": "[TODO]",
            "❓": "[?]",
            "🎯": "[TARGET]",
            "🚀": "[START]",
            "✨": "[*]"
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        __import__('builtins').print(text, **kwargs)


print = safe_print


@dataclass
class VerifiedReference:
    """已验证的参考文献数据结构"""
    title: str
    authors: List[str]
    year: int
    doi: str                              # 已验证的DOI
    doi_url: str                          # 可点击链接 https://doi.org/xxx
    journal: Optional[str] = None
    source_api: str = "unknown"           # 来源API
    cross_verified: bool = False          # 是否经过CrossRef交叉验证
    relevance_score: float = 0.0          # 与查询的相关度
    citation_count: int = 0
    gb7714_format: str = ""               # 预格式化的GB/T 7714引用
    language: str = "en"                  # "zh"或"en"
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    abstract: Optional[str] = None
    paper_id: Optional[str] = None        # API内部ID

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class SemanticScholarSearcher:
    """Semantic Scholar API搜索器

    限流说明：
    - 无 API Key: 每5分钟100次请求，容易触发429限流
    - 有 API Key: 每5分钟5000次请求，稳定可靠

    申请地址: https://www.semanticscholar.org/product/api
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # 限流警告提示
    RATE_LIMIT_WARNING = """
    [重要] Semantic Scholar API 触发 429 限流错误！

    原因: 未配置 API Key，免费额度为每5分钟100次请求，已超限。

    解决方案: 申请免费 API Key
    1. 访问: https://www.semanticscholar.org/product/api
    2. 注册账号并申请 API Key（免费）
    3. 在 .thesis-config.yaml 中配置:

       semantic_scholar:
         api_key: "YOUR_API_KEY_HERE"

    配置后可获得每5分钟5000次请求额度，搜索更稳定。
    """

    def __init__(self, api_key: Optional[str] = None, config_path: Optional[str] = None):
        """__init__"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "thesis-creator/1.0 (https://github.com/thesis-creator)"
        })

        # 尝试从配置文件读取 API Key
        self.api_key = api_key
        if not api_key and config_path:
            self.api_key = self._load_api_key_from_config(config_path)

        if self.api_key:
            self.session.headers["x-api-key"] = self.api_key
            self.min_interval = 0.1  # 有Key时请求间隔较短
        else:
            self.min_interval = 1.0  # 无Key时请求间隔较长，避免限流

        self._last_request_time = 0
        self._rate_limit_warned = False  # 是否已提示过限流警告
        self._max_retries = 2  # 最大重试次数
        self._retry_wait = 5  # 429错误等待时间（秒，避免长时间阻塞）

    def _load_api_key_from_config(self, config_path: str) -> Optional[str]:
        """从配置文件读取 API Key"""
        try:
            import yaml
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    ss_config = config.get('semantic_scholar', {})
                    api_key = ss_config.get('api_key', '')
                    if api_key and api_key.strip():
                        print(f"[信息] 已从配置文件加载 Semantic Scholar API Key")
                        return api_key.strip()
        except Exception as e:
            print(f"[警告] 读取配置文件失败: {e}")
        return None

    def _rate_limit(self):
        """限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _handle_429_error(self, retry_count: int) -> bool:
        """处理 429 限流错误

        Returns:
            True: 可以重试
            False: 不再重试，输出警告
        """
        if not self._rate_limit_warned:
            print(self.RATE_LIMIT_WARNING)
            self._rate_limit_warned = True

        if retry_count < self._max_retries:
            wait_time = self._retry_wait * (retry_count + 1)  # 递增等待时间
            print(f"[信息] 等待 {wait_time} 秒后重试 (第 {retry_count + 1}/{self._max_retries} 次)")
            time.sleep(wait_time)
            return True
        return False

    def search(
        self,
        query: str,
        year_range: Tuple[int, int] = (2020, 2025),
        limit: int = 10
    ) -> List[VerifiedReference]:
        """搜索文献"""
        self._rate_limit()

        fields = [
            "title", "authors", "year", "journal", "volume",
            "issue", "pages", "doi", "url", "abstract",
            "citationCount", "paperId"
        ]

        params = {
            "query": query,
            "year": f"{year_range[0]}-{year_range[1]}",
            "limit": min(limit, 100),
            "fields": ",".join(fields)
        }

        retry_count = 0
        while retry_count <= self._max_retries:
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/paper/search",
                    params=params,
                    timeout=30
                )

                # 处理 429 限流错误
                if response.status_code == 429:
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                    else:
                        print("[警告] Semantic Scholar 搜索失败: 达到重试上限，跳过此源")
                        return []

                response.raise_for_status()
                data = response.json()
                results = []

                for paper in data.get("data", []):
                    authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
                    journal_info = paper.get("journal", {}) or {}
                    journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None
                    doi = paper.get("doi") or ""
                    year_val = paper.get("year", 0) or 0

                    ref = VerifiedReference(
                        title=paper.get("title", ""),
                        authors=authors,
                        year=year_val,
                        doi=doi,
                        doi_url=f"https://doi.org/{doi}" if doi else "",
                        journal=journal_name,
                        source_api="Semantic Scholar",
                        citation_count=paper.get("citationCount", 0) or 0,
                        volume=paper.get("volume"),
                        issue=paper.get("issue"),
                        pages=paper.get("pages"),
                        abstract=paper.get("abstract"),
                        paper_id=paper.get("paperId"),
                        language=self._detect_language(paper.get("title", ""))
                    )
                    results.append(ref)

                return results

            except requests.exceptions.RequestException as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                print(f"[警告] Semantic Scholar搜索失败: {e}")
                return []

        return []

    def get_paper_by_doi(self, doi: str) -> Optional[VerifiedReference]:
        """通过DOI获取文献信息"""
        self._rate_limit()

        fields = [
            "title", "authors", "year", "journal", "volume",
            "issue", "pages", "doi", "url", "abstract",
            "citationCount", "paperId"
        ]

        retry_count = 0
        while retry_count <= self._max_retries:
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/paper/DOI:{doi}",
                    params={"fields": ",".join(fields)},
                    timeout=30
                )

                # 处理 429 限流错误
                if response.status_code == 429:
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                    else:
                        print("[警告] Semantic Scholar DOI查询失败: 达到重试上限")
                        return None

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                paper = response.json()

                authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
                journal_info = paper.get("journal", {}) or {}
                journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None
                doi_val = paper.get("doi") or ""

                return VerifiedReference(
                    title=paper.get("title", ""),
                    authors=authors,
                    year=paper.get("year", 0) or 0,
                    doi=doi_val,
                    doi_url=f"https://doi.org/{doi_val}" if doi_val else "",
                    journal=journal_name,
                    source_api="Semantic Scholar",
                    citation_count=paper.get("citationCount", 0) or 0,
                    volume=paper.get("volume"),
                    issue=paper.get("issue"),
                    pages=paper.get("pages"),
                    abstract=paper.get("abstract"),
                    paper_id=paper.get("paperId"),
                    language=self._detect_language(paper.get("title", ""))
                )

            except requests.exceptions.RequestException as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                print(f"[警告] Semantic Scholar DOI查询失败: {e}")
                return None

        return None

    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text:
            return "en"
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.3:
            return "zh"
        return "en"


class CrossRefSearcher:
    """CrossRef API搜索器

    限流说明：
    - CrossRef 是完全免费的，但仍有请求频率限制
    - 建议请求间隔 >= 1 秒，避免触发 429 限流
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(self):
        """__init__"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "thesis-creator/1.0 (mailto:example@example.com)"
        })
        self._last_request_time = 0
        self.min_interval = 1.0  # 增加 request 间隔
        self._max_retries = 3
        self._retry_wait = 60

    def _rate_limit(self):
        """限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _handle_429_error(self, retry_count: int) -> bool:
        """处理 429 限流错误"""
        if retry_count < self._max_retries:
            wait_time = self._retry_wait * (retry_count + 1)
            print(f"[信息] CrossRef 限流，等待 {wait_time} 秒后重试 (第 {retry_count + 1}/{self._max_retries} 次)")
            time.sleep(wait_time)
            return True
        return False

    def search(
        self,
        query: str,
        year_range: Tuple[int, int] = (2020, 2025),
        limit: int = 10
    ) -> List[VerifiedReference]:
        """搜索文献"""
        self._rate_limit()

        params = {
            "query.bibliographic": query,
            "filter": f"from-pub-date:{year_range[0]},until-pub-date:{year_range[1]}",
            "rows": min(limit, 100),
            "select": "DOI,title,author,published-print,published-online,container-title,volume,issue,page,abstract,is-referenced-by-count"
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/works",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            results = []

            for item in data.get("message", {}).get("items", []):
                # 解析作者
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if family:
                        name = f"{given} {family}" if given else family
                        authors.append(name)

                # 解析年份
                year_val = 0
                published = item.get("published-print") or item.get("published-online") or {}
                if published:
                    date_parts = published.get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        year_val = date_parts[0][0]

                # 解析标题
                titles = item.get("title", [])
                title = titles[0] if titles else ""

                # 解析期刊
                containers = item.get("container-title", [])
                journal = containers[0] if containers else None

                doi = item.get("DOI") or ""

                ref = VerifiedReference(
                    title=title,
                    authors=authors,
                    year=year_val,
                    doi=doi,
                    doi_url=f"https://doi.org/{doi}" if doi else "",
                    journal=journal,
                    source_api="CrossRef",
                    citation_count=item.get("is-referenced-by-count", 0) or 0,
                    volume=item.get("volume"),
                    issue=item.get("issue"),
                    pages=item.get("page"),
                    abstract=item.get("abstract"),
                    language=self._detect_language(title)
                )
                results.append(ref)

            return results

        except requests.exceptions.RequestException as e:
            print(f"[警告] CrossRef搜索失败: {e}")
            return []

    def verify_doi(self, doi: str) -> Tuple[bool, Optional[VerifiedReference]]:
        """
        验证DOI真实性（带 429 重试）

        Args:
            doi: DOI字符串

        Returns:
            (是否有效, 文献信息)
        """
        self._rate_limit()

        retry_count = 0
        while retry_count <= self._max_retries:
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/works/{doi}",
                    timeout=30
                )

                # 处理 429 限流错误
                if response.status_code == 429:
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                    else:
                        print(f"[警告] CrossRef DOI验证失败: 达到重试上限")
                        return False, None

                if response.status_code == 404:
                    return False, None

                response.raise_for_status()
                data = response.json()
                item = data.get("message", {})

                # 解析作者
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if family:
                        name = f"{given} {family}" if given else family
                        authors.append(name)

                # 解析年份
                year_val = 0
                published = item.get("published-print") or item.get("published-online") or {}
                if published:
                    date_parts = published.get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        year_val = date_parts[0][0]

                titles = item.get("title", [])
                title = titles[0] if titles else ""

                containers = item.get("container-title", [])
                journal = containers[0] if containers else None

                doi_val = item.get("DOI") or ""

                ref = VerifiedReference(
                        title=title,
                        authors=authors,
                        year=year_val,
                        doi=doi_val,
                        doi_url=f"https://doi.org/{doi_val}" if doi_val else "",
                        journal=journal,
                        source_api="CrossRef",
                        cross_verified=True,
                        citation_count=item.get("is-referenced-by-count", 0) or 0,
                        volume=item.get("volume"),
                        issue=item.get("issue"),
                        pages=item.get("page"),
                        abstract=item.get("abstract"),
                        language=self._detect_language(title)
                    )

                return True, ref

            except requests.exceptions.RequestException as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if self._handle_429_error(retry_count):
                        retry_count += 1
                        continue
                print(f"[警告] CrossRef DOI验证失败: {e}")
                return False, None

        return False, None

    def check_doi_reachable(self, doi: str) -> Tuple[bool, int]:
        """
        检查DOI链接可达性（判断 4xx 错误）

        Args:
            doi: DOI字符串

        Returns:
            (链接是否可达, 状态码)
            - True: 链接可达（状态码 < 400）
            - False: 链接不可达（4xx 或 5xx 错误）
        """
        try:
            response = requests.head(
                f"https://doi.org/{doi}",
                timeout=10,
                allow_redirects=True
            )
            status_code = response.status_code

            # 判断 4xx 和 5xx 错误
            if 400 <= status_code < 600:
                # 404: DOI 不存在
                # 403: 访问被拒绝
                # 4xx: 客户端错误
                # 5xx: 服务端错误
                return False, status_code

            return True, status_code
        except requests.exceptions.RequestException as e:
            # 网络异常视为不可达
            return False, 0
        except Exception:
            return False, 0

    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text:
            return "en"
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.3:
            return "zh"
        return "en"


class OpenAlexSearcher:
    """OpenAlex API搜索器"""

    BASE_URL = "https://api.openalex.org"

    def __init__(self):
        """__init__"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "thesis-creator/1.0 (mailto:example@example.com)"
        })
        self._last_request_time = 0
        self.min_interval = 0.1

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
        limit: int = 10
    ) -> List[VerifiedReference]:
        """搜索文献"""
        self._rate_limit()

        # OpenAlex的年份过滤
        filter_str = f"from_publication_date:{year_range[0]}-01-01,to_publication_date:{year_range[1]}-12-31"

        params = {
            "search": query,
            "filter": filter_str,
            "per_page": min(limit, 100)
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/works",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            results = []

            for item in data.get("results", []):
                # 解析作者
                authors = []
                for authorship in item.get("authorships", []):
                    author = authorship.get("author", {})
                    name = author.get("display_name", "")
                    if name:
                        authors.append(name)

                # 解析年份
                year_val = 0
                pub_date = item.get("publication_date", "")
                if pub_date:
                    year_val = int(pub_date.split("-")[0])

                # 解析标题
                title = item.get("title", "") or item.get("display_name", "")

                # 解析期刊
                primary_location = item.get("primary_location", {}) or {}
                source = primary_location.get("source", {}) or {}
                journal = source.get("display_name", "")

                # 解析DOI
                doi = item.get("doi", "") or ""
                if doi and doi.startswith("https://doi.org/"):
                    doi = doi.replace("https://doi.org/", "")

                ref = VerifiedReference(
                    title=title,
                    authors=authors,
                    year=year_val,
                    doi=doi,
                    doi_url=f"https://doi.org/{doi}" if doi else "",
                    journal=journal,
                    source_api="OpenAlex",
                    citation_count=item.get("cited_by_count", 0) or 0,
                    abstract=item.get("abstract_inverted_index"),  # OpenAlex使用倒排索引
                    paper_id=item.get("id"),
                    language=self._detect_language(title)
                )
                results.append(ref)

            return results

        except requests.exceptions.RequestException as e:
            print(f"[警告] OpenAlex搜索失败: {e}")
            return []

    def _detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text:
            return "en"
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.3:
            return "zh"
        return "en"


class MultiSourceSearcher:
    """多源聚合搜索引擎"""

    DEFAULT_CONFIG_PATH = "thesis-workspace/.thesis-config.yaml"

    def __init__(
        self,
        semantic_scholar_key: Optional[str] = None,
        sources: List[str] = ["semantic-scholar", "crossref", "openalex"],
        config_path: Optional[str] = None
    ):
        self.searchers = {}

        if "semantic-scholar" in sources:
            ss_config_path = config_path or self.DEFAULT_CONFIG_PATH
            self.searchers["semantic-scholar"] = SemanticScholarSearcher(
                api_key=semantic_scholar_key,
                config_path=ss_config_path
            )

        if "crossref" in sources:
            self.searchers["crossref"] = CrossRefSearcher()

        if "openalex" in sources:
            self.searchers["openalex"] = OpenAlexSearcher()

        self.crossref_searcher = CrossRefSearcher()

    def search(
        self,
        query: str,
        year_range: Tuple[int, int] = (2020, 2025),
        limit: int = 10,
        cross_verify: bool = True,
        language: str = "all"
    ) -> List[VerifiedReference]:
        print(f"\n{'='*50}")
        print(f"[搜索进度] 多源搜索: {query}")
        print(f"[搜索进度] API源: {list(self.searchers.keys())}")
        print(f"[搜索进度] 目标数量: {limit} 条/源")
        print(f"{'='*50}")

        all_results = []
        total_sources = len(self.searchers)

        for i, (source_name, searcher) in enumerate(self.searchers.items(), 1):
            print(f"\n[搜索进度] ({i}/{total_sources}) 搜索 {source_name}...")
            try:
                results = searcher.search(query, year_range, limit)
                print(f"[搜索进度] {source_name}: ✅ 完成 ({len(results)} 条结果)")
                all_results.extend(results)
            except Exception as e:
                print(f"[搜索进度] {source_name}: ❌ 失败 ({e})")

        deduplicated = self._deduplicate(all_results)
        print(f"\n[搜索进度] 去重合并: {len(all_results)} → {len(deduplicated)} 条")

        if cross_verify:
            deduplicated = self._cross_verify_dois_with_progress(deduplicated)
            verified_count = sum(1 for r in deduplicated if r.cross_verified)
            print(f"\n[DOI验证] ✅ 验证完成: {verified_count}/{len(deduplicated)} 条通过")

        if language != "all":
            deduplicated = [r for r in deduplicated if r.language == language]
            print(f"[信息] 语言过滤后 {language}: {len(deduplicated)} 条")

        sorted_results = self._sort_by_relevance(deduplicated, query)
        return sorted_results

    def _deduplicate(self, results: List[VerifiedReference]) -> List[VerifiedReference]:
        if not results:
            return []

        deduplicated = []
        seen_dois = set()
        seen_titles = []

        for ref in results:
            if ref.doi:
                if ref.doi in seen_dois:
                    continue
                seen_dois.add(ref.doi)

            is_duplicate = False
            for seen_title in seen_titles:
                similarity = self._title_similarity(ref.title, seen_title)
                if similarity > 0.85:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(ref)
                seen_titles.append(ref.title)

        return deduplicated

    def _title_similarity(self, title1: str, title2: str) -> float:
        if not title1 or not title2:
            return 0.0

        t1 = title1.lower().strip()
        t2 = title2.lower().strip()

        if t1 == t2:
            return 1.0

        return SequenceMatcher(None, t1, t2).ratio()

    def _cross_verify_dois_with_progress(self, results: List[VerifiedReference]) -> List[VerifiedReference]:
        total = len(results)
        doi_refs = [r for r in results if r.doi]
        doi_count = len(doi_refs)

        print(f"\n[DOI验证] 开始验证 {doi_count} 个DOI（共 {total} 条文献）")

        verified = 0
        failed = 0

        for ref in results:
            if ref.doi:
                valid, crossref_ref = self.crossref_searcher.verify_doi(ref.doi)
                if valid and crossref_ref:
                    ref.cross_verified = True
                    verified += 1
                    if not ref.journal and crossref_ref.journal:
                        ref.journal = crossref_ref.journal
                    if not ref.volume and crossref_ref.volume:
                        ref.volume = crossref_ref.volume
                    if not ref.issue and crossref_ref.issue:
                        ref.issue = crossref_ref.issue
                    if not ref.pages and crossref_ref.pages:
                        ref.pages = crossref_ref.pages
                else:
                    ref.cross_verified = False
                    failed += 1

                checked = verified + failed
                if checked % 5 == 0 or checked == doi_count:
                    remaining = doi_count - checked
                    est_seconds = remaining * 4
                    if remaining > 0:
                        print(f"[DOI验证] 验证进度: {checked}/{doi_count} (通过:{verified} 失败:{failed}) 约还需 {est_seconds} 秒")
                    else:
                        print(f"[DOI验证] 验证进度: {checked}/{doi_count} ✅")

        print(f"[DOI验证] 结果: 通过 {verified}, 失败 {failed}, 无DOI {total - doi_count}")
        return results

    def _sort_by_relevance(
        self,
        results: List[VerifiedReference],
        query: str
    ) -> List[VerifiedReference]:
        query_words = set(query.lower().split())
        current_year = datetime.now().year

        for ref in results:
            title_words = set(ref.title.lower().split()) if ref.title else set()
            overlap = len(query_words & title_words)
            relevance = overlap / max(len(query_words), 1) if query_words else 0
            ref.relevance_score = relevance

        def compute_score(ref: VerifiedReference) -> float:
            relevance_score = ref.relevance_score * 0.4
            citation_score = min(ref.citation_count / 1000, 1.0) * 0.2
            year_diff = current_year - ref.year if ref.year else 10
            year_score = max(0, 1 - year_diff / 10) * 0.2
            verify_score = 0.2 if ref.cross_verified else 0.1
            return relevance_score + citation_score + year_score + verify_score

        return sorted(results, key=compute_score, reverse=True)

    def verify_doi(self, doi: str) -> Tuple[bool, Optional[VerifiedReference]]:
        reachable, status_code = self.crossref_searcher.check_doi_reachable(doi)
        if not reachable:
            return False, None

        valid, ref = self.crossref_searcher.verify_doi(doi)

        if valid and ref:
            ref.cross_verified = True
            return True, ref

        return False, None

class ReferenceFormatter:
    """参考文献格式化器"""

    @staticmethod
    def format_gbt7714(ref: VerifiedReference, index: int = 1) -> str:
        """
        格式化为GB/T 7714标准格式

        Args:
            ref: 已验证的参考文献
            index: 参考文献序号

        Returns:
            GB/T 7714格式的参考文献字符串
        """
        # 作者格式化
        authors_str = ReferenceFormatter._format_authors(ref.authors)

        # 文献类型判断
        if ref.journal:
            ref_type = "[J]"
            parts = [authors_str, ref.title, ref_type]

            if ref.journal:
                parts.append(ref.journal)

            if ref.year:
                parts.append(f", {ref.year}")

            if ref.volume:
                parts.append(f", {ref.volume}")
                if ref.issue:
                    parts.append(f"({ref.issue})")

            if ref.pages:
                parts.append(f": {ref.pages}")

            ref_str = ". ".join([p for p in parts if p]) + "."
        else:
            ref_type = "[C]"
            ref_str = f"{authors_str}. {ref.title}{ref_type}. {ref.year}."

        # 添加DOI链接
        if ref.doi and ref.doi_url:
            ref_str += f" [DOI]({ref.doi_url})"

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
    def format_yaml(results: List[VerifiedReference], pool_id: str = "references") -> str:
        """
        格式化为YAML文献池格式

        Args:
            results: 参考文献列表
            pool_id: 文献池ID

        Returns:
            YAML格式字符串
        """
        lines = [
            f"# 已验证的真实文献池",
            f"pool_id: {pool_id}",
            f"generated_at: {datetime.now().strftime('%Y-%m-%d')}",
            f"total: {len(results)}",
            "",
            "references:"
        ]

        for i, ref in enumerate(results, 1):
            gb7714 = ReferenceFormatter.format_gbt7714(ref, i)

            lines.append(f"  - id: ref_{i:03d}")
            lines.append(f"    title: \"{ref.title}\"")
            lines.append(f"    authors:")
            for author in ref.authors[:5]:
                lines.append(f"      - \"{author}\"")
            lines.append(f"    year: {ref.year}")
            lines.append(f"    doi: \"{ref.doi}\"")
            lines.append(f"    doi_url: \"{ref.doi_url}\"")
            lines.append(f"    verified: {ref.cross_verified}")
            lines.append(f"    source: \"{ref.source_api}\"")
            lines.append(f"    language: \"{ref.language}\"")
            lines.append(f"    keywords: []  # 待填充")
            lines.append(f"    gb7714: \"{gb7714}\"")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_json(results: List[VerifiedReference]) -> str:
        """格式化为JSON"""
        return json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2
        )

    @staticmethod
    def format_table(results: List[VerifiedReference]) -> str:
        """格式化为表格"""
        lines = [
            "| 序号 | 标题 | 作者 | 年份 | DOI验证 | 引用数 |",
            "|------|------|------|------|---------|--------|"
        ]

        for i, r in enumerate(results, 1):
            title = r.title[:40] + "..." if len(r.title) > 40 else r.title
            authors = ", ".join(r.authors[:2])
            if len(r.authors) > 2:
                authors += "等"
            verified = "[OK]" if r.cross_verified else "[X]"

            lines.append(
                f"| {i} | {title} | {authors} | {r.year} | {verified} | {r.citation_count} |"
            )

        return "\n".join(lines)


def search_and_format(
    query: str,
    year_range: Tuple[int, int] = (2020, 2025),
    limit: int = 10,
    sources: List[str] = ["semantic-scholar", "crossref", "openalex"],
    output_format: str = "yaml",
    cross_verify: bool = True,
    language: str = "all",
    api_key: Optional[str] = None,
    config_path: Optional[str] = None,
    zh_ratio: float = 0.65,
    search_multiplier: float = 1.5
) -> str:
    """
    多源搜索并格式化输出

    Args:
        query: 搜索关键词
        year_range: 年份范围
        limit: 最终目标数量
        sources: API源列表
        output_format: 输出格式 (yaml, gbt7714, json, table)
        cross_verify: 是否进行DOI交叉验证
        language: 语言过滤
        api_key: Semantic Scholar API Key
        config_path: 配置文件路径（自动读取API Key）
        zh_ratio: 中文文献占比（默认0.65，要求中文>65%）
        search_multiplier: 搜索放大倍数（默认 1.5 倍）

    Returns:
        格式化后的输出
    """
    searcher = MultiSourceSearcher(
        semantic_scholar_key=api_key,
        sources=sources,
        config_path=config_path
    )

    expanded_limit = max(limit, int(math.ceil(limit * search_multiplier)))

    if zh_ratio > 0 and zh_ratio < 1.0 and language == "all":
        zh_target = int(math.ceil(expanded_limit * zh_ratio))
        en_target = max(1, expanded_limit - zh_target)

        print(f"\n[比例控制] 搜索目标: {expanded_limit} 篇（约 {search_multiplier:.1f}x）")
        print(f"[比例控制] 中文目标: {zh_target} 篇, 英文目标: {en_target} 篇 (比例 {zh_ratio:.0%})")

        zh_results = searcher.search(
            query=query,
            year_range=year_range,
            limit=zh_target,
            cross_verify=False,
            language="zh"
        )
        print(f"[比例控制] 中文文献搜索完成: {len(zh_results)} 篇")

        en_results = searcher.search(
            query=query,
            year_range=year_range,
            limit=en_target,
            cross_verify=False,
            language="en"
        )
        print(f"[比例控制] 英文文献搜索完成: {len(en_results)} 篇")

        results = zh_results + en_results

        zh_count = sum(1 for r in results if r.language == "zh")
        actual_ratio = zh_count / len(results) if results else 0
        if actual_ratio <= zh_ratio:
            print(f"[比例控制] ⚠️ 中文比例 {actual_ratio:.1%} 未超过目标 {zh_ratio:.0%}，触发补充搜索")
            supplement_limit = max(3, int((zh_ratio * len(results) - zh_count) / max(1e-6, (1 - zh_ratio))) + 3)
            supplement_zh = searcher.search(
                query=query,
                year_range=year_range,
                limit=supplement_limit,
                cross_verify=False,
                language="zh"
            )
            results.extend(supplement_zh)
            print(f"[比例控制] 补充中文文献: {len(supplement_zh)} 篇")

        if cross_verify:
            results = searcher._cross_verify_dois_with_progress(results)

        results = searcher._sort_by_relevance(results, query)
    else:
        results = searcher.search(
            query=query,
            year_range=year_range,
            limit=expanded_limit,
            cross_verify=cross_verify,
            language=language
        )

    if not results:
        return "未找到相关文献"

    if len(results) > limit:
        results = results[:limit]

    print(f"[成功] 找到 {len(results)} 篇文献")

    if output_format == "yaml":
        return ReferenceFormatter.format_yaml(results, pool_id=query.replace(" ", "_"))
    elif output_format == "gbt7714":
        lines = ["# 参考文献搜索结果", ""]
        lines.append(f"> 搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 关键词: {query}")
        lines.append(f"> 结果数: {len(results)}")
        lines.append(f"> DOI验证通过: {sum(1 for r in results if r.cross_verified)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, r in enumerate(results, 1):
            lines.append(ReferenceFormatter.format_gbt7714(r, i))
            if r.abstract and isinstance(r.abstract, str):
                lines.append(f"   > 摘要: {r.abstract[:200]}...")
            lines.append("")

        return "\n".join(lines)
    elif output_format == "json":
        return ReferenceFormatter.format_json(results)
    elif output_format == "table":
        return ReferenceFormatter.format_table(results)
    else:
        return ReferenceFormatter.format_gbt7714(results[0])
def main():
    """main"""
    parser = argparse.ArgumentParser(description="多源学术搜索引擎")

    parser.add_argument("--query", "-q", help="搜索关键词")
    parser.add_argument("--doi", "-d", help="验证DOI")
    parser.add_argument("--year-start", type=int, default=2020, help="起始年份")
    parser.add_argument("--year-end", type=int, default=2025, help="结束年份")
    parser.add_argument("--limit", "-l", type=int, default=10, help="每个API结果数量")
    parser.add_argument("--source", "-s",
                        choices=["semantic-scholar", "crossref", "openalex", "all"],
                        default="all",
                        help="API源")
    parser.add_argument("--format", "-f",
                        choices=["yaml", "gbt7714", "json", "table"],
                        default="yaml",
                        help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--verify-doi", action="store_true",
                        default=True,
                        help="进行DOI交叉验证（默认启用）")
    parser.add_argument("--no-verify", action="store_true",
                        help="跳过DOI交叉验证（稍后校验模式）")
    parser.add_argument("--language",
                        choices=["zh", "en", "all"],
                        default="all",
                        help="语言过滤")
    parser.add_argument("--api-key", help="Semantic Scholar API Key")
    parser.add_argument("--zh-ratio", type=float, default=0.65,
                        help="中文文献占比（默认0.65，要求中文大于65），仅在language=all时生效")
    parser.add_argument("--search-multiplier", type=float, default=1.5,
                        help="搜索放大倍数（默认1.5，先搜到目标数量的1.5倍再筛选）")

    args = parser.parse_args()

    # 处理验证选项（--no-verify 优先级高于 --verify-doi）
    cross_verify = args.verify_doi and not args.no_verify

    # 确定API源
    if args.source == "all":
        sources = ["semantic-scholar", "crossref", "openalex"]
    else:
        sources = [args.source]

    if args.query:
        # 搜索模式
        output = search_and_format(
            query=args.query,
            year_range=(args.year_start, args.year_end),
            limit=args.limit,
            sources=sources,
            output_format=args.format,
            cross_verify=cross_verify,
            language=args.language,
            api_key=args.api_key,
            zh_ratio=args.zh_ratio,
            search_multiplier=args.search_multiplier
        )

    elif args.doi:
        # DOI验证模式
        searcher = MultiSourceSearcher(semantic_scholar_key=args.api_key)
        valid, ref = searcher.verify_doi(args.doi)

        if valid and ref:
            output = f"[OK] DOI验证通过\n\n"
            output += ReferenceFormatter.format_gbt7714(ref)
            output += f"\n\n来源: {ref.source_api}"
            output += f"\n标题: {ref.title}"
            output += f"\n年份: {ref.year}"
            if ref.journal:
                output += f"\n期刊: {ref.journal}"
        else:
            output = f"[FAIL] DOI无效或不存在: {args.doi}"

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
