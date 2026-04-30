# -*- coding: utf-8 -*-
"""
已验证文献池管理器（Verified Reference Pool Manager）

核心功能：
1. 加载/保存 `workspace/references/verified_references.yaml`
2. 按章节/主题管理文献分组
3. 为段落内容推荐最相关的文献（基于关键词匹配）
4. 防止同一文献被重复引用过多次
5. 导出最终参考文献列表（带可点击 DOI 链接）

使用方法：
    python scripts/verified_reference_pool.py --init --chapter "第四章"
    python scripts/verified_reference_pool.py --add --file search_results.yaml
    python scripts/verified_reference_pool.py --recommend --keywords "RAG 知识库 检索"
    python scripts/verified_reference_pool.py --export --format gbt7714
"""

import re
import json
import yaml
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher


@dataclass
class PoolReference:
    """文献池中的参考文献"""
    id: str
    title: str
    authors: List[str]
    year: int
    doi: str
    doi_url: str
    journal: Optional[str] = None
    source_api: str = "unknown"
    cross_verified: bool = False
    relevance_score: float = 0.0
    citation_count: int = 0
    gb7714: str = ""
    keywords: List[str] = []
    language: str = "en"
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    used_count: int = 0  # 已被引用次数
    chapters_used: List[str] = []  # 已被引用的章节列表

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class VerifiedReferencePool:
    """已验证文献池管理器"""

    DEFAULT_POOL_FILE = "workspace/references/verified_references.yaml"
    MAX_USE_PER_REFERENCE = 1  # 单篇文献最大引用次数

    def __init__(self, pool_file: Optional[str] = None):
        """
        初始化文献池管理器

        Args:
            pool_file: 文献池文件路径
        """
        self.pool_file = Path(pool_file or self.DEFAULT_POOL_FILE)
        self.references: Dict[str, PoolReference] = {}
        self.groups: Dict[str, List[str]] = {}  # 章节/主题分组
        self.metadata = {
            "pool_id": "thesis_references",
            "created_at": datetime.now().strftime('%Y-%m-%d'),
            "last_updated": datetime.now().strftime('%Y-%m-%d'),
            "total": 0,
            "chapters": []
        }

        # 自动加载现有文献池
        if self.pool_file.exists():
            self.load()

    def load(self) -> bool:
        """
        加载文献池

        Returns:
            是否成功加载
        """
        if not self.pool_file.exists():
            return False

        try:
            with open(self.pool_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return False

            # 加载元数据
            self.metadata = {
                "pool_id": data.get("pool_id", "thesis_references"),
                "created_at": data.get("created_at", datetime.now().strftime('%Y-%m-%d')),
                "last_updated": data.get("last_updated", datetime.now().strftime('%Y-%m-%d')),
                "total": data.get("total", 0),
                "chapters": data.get("chapters", [])
            }

            # 加载参考文献
            for ref_data in data.get("references", []):
                ref = PoolReference(
                    id=ref_data.get("id", ""),
                    title=ref_data.get("title", ""),
                    authors=ref_data.get("authors", []),
                    year=ref_data.get("year", 0),
                    doi=ref_data.get("doi", ""),
                    doi_url=ref_data.get("doi_url", ""),
                    journal=ref_data.get("journal"),
                    source_api=ref_data.get("source_api", "unknown"),
                    cross_verified=ref_data.get("verified", False),
                    relevance_score=ref_data.get("relevance_score", 0.0),
                    citation_count=ref_data.get("citation_count", 0),
                    gb7714=ref_data.get("gb7714", ""),
                    keywords=ref_data.get("keywords", []),
                    language=ref_data.get("language", "en"),
                    volume=ref_data.get("volume"),
                    issue=ref_data.get("issue"),
                    pages=ref_data.get("pages"),
                    used_count=ref_data.get("used_count", 0),
                    chapters_used=ref_data.get("chapters_used", [])
                )
                if ref.id:
                    self.references[ref.id] = ref

            # 加载分组
            for group_name, ref_ids in data.get("groups", {}).items():
                self.groups[group_name] = ref_ids

            print(f"[成功] 加载文献池: {len(self.references)} 条文献")
            return True

        except Exception as e:
            print(f"[错误] 加载文献池失败: {e}")
            return False

    def save(self) -> bool:
        """
        保存文献池

        Returns:
            是否成功保存
        """
        try:
            # 确保目录存在
            self.pool_file.parent.mkdir(parents=True, exist_ok=True)

            # 更新元数据
            self.metadata["last_updated"] = datetime.now().strftime('%Y-%m-%d')
            self.metadata["total"] = len(self.references)

            # 构建数据结构
            data = {
                "pool_id": self.metadata["pool_id"],
                "created_at": self.metadata["created_at"],
                "last_updated": self.metadata["last_updated"],
                "total": self.metadata["total"],
                "chapters": self.metadata["chapters"],
                "references": [ref.to_dict() for ref in self.references.values()],
                "groups": self.groups
            }

            with open(self.pool_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            print(f"[成功] 保存文献池: {self.pool_file}")
            return True

        except Exception as e:
            print(f"[错误] 保存文献池失败: {e}")
            return False

    def add_references(
        self,
        references: List[Dict],
        chapter: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> int:
        """
        批量添加参考文献

        Args:
            references: 参考文献列表（字典格式）
            chapter: 所属章节
            keywords: 附加关键词

        Returns:
            成功添加的数量
        """
        added_count = 0

        for ref_data in references:
            # 生成 ID
            ref_id = ref_data.get("id") or f"ref_{len(self.references) + 1:03d}"

            # 检查是否已存在（DOI去重）
            doi = ref_data.get("doi", "")
            if doi:
                existing = self.find_by_doi(doi)
                if existing:
                    print(f"[跳过] DOI已存在: {doi}")
                    continue

            # 创建参考文献对象
            ref = PoolReference(
                id=ref_id,
                title=ref_data.get("title", ""),
                authors=ref_data.get("authors", []),
                year=ref_data.get("year", 0),
                doi=doi,
                doi_url=ref_data.get("doi_url", f"https://doi.org/{doi}" if doi else ""),
                journal=ref_data.get("journal"),
                source_api=ref_data.get("source_api", "unknown"),
                cross_verified=ref_data.get("verified", False) or ref_data.get("cross_verified", False),
                relevance_score=ref_data.get("relevance_score", 0.0),
                citation_count=ref_data.get("citation_count", 0),
                gb7714=ref_data.get("gb7714", ""),
                keywords=keywords or ref_data.get("keywords", []),
                language=ref_data.get("language", "en"),
                volume=ref_data.get("volume"),
                issue=ref_data.get("issue"),
                pages=ref_data.get("pages")
            )

            self.references[ref_id] = ref
            added_count += 1

            # 添加到章节分组
            if chapter:
                if chapter not in self.groups:
                    self.groups[chapter] = []
                if ref_id not in self.groups[chapter]:
                    self.groups[chapter].append(ref_id)
                if chapter not in self.metadata["chapters"]:
                    self.metadata["chapters"].append(chapter)

        if added_count > 0:
            self.save()
            print(f"[成功] 添加 {added_count} 条文献")

        return added_count

    def find_by_doi(self, doi: str) -> Optional[PoolReference]:
        """
        通过 DOI 查找文献

        Args:
            doi: DOI 字符串

        Returns:
            参考文献对象
        """
        for ref in self.references.values():
            if ref.doi == doi:
                return ref
        return None

    def find_by_title(self, title: str, threshold: float = 0.8) -> Optional[PoolReference]:
        """
        通过标题相似度查找文献

        Args:
            title: 标题字符串
            threshold: 相似度阈值

        Returns:
            参考文献对象
        """
        best_match = None
        best_score = 0

        for ref in self.references.values():
            score = SequenceMatcher(None, title.lower(), ref.title.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = ref

        return best_match

    def recommend(
        self,
        keywords: List[str],
        chapter: Optional[str] = None,
        limit: int = 5,
        exclude_used: bool = True
    ) -> List[PoolReference]:
        """
        根据关键词推荐最相关的文献

        Args:
            keywords: 关键词列表
            chapter: 目标章节（优先推荐该章节的文献）
            limit: 推荐数量
            exclude_used: 是否排除已达到引用上限的文献

        Returns:
            推荐的参考文献列表
        """
        candidates = []

        # 收集候选文献
        for ref in self.references.values():
            # 排除已达引用上限的文献
            if exclude_used and ref.used_count >= self.MAX_USE_PER_REFERENCE:
                continue

            # 计算关键词匹配得分
            score = self._calculate_keyword_score(ref, keywords)

            # 章节相关性加分
            if chapter and chapter in ref.chapters_used:
                score += 0.1

            candidates.append((ref, score))

        # 按得分排序
        candidates.sort(key=lambda x: x[1], reverse=True)

        return [c[0] for c in candidates[:limit]]

    def _calculate_keyword_score(self, ref: PoolReference, keywords: List[str]) -> float:
        """
        计算关键词匹配得分

        Args:
            ref: 参考文献
            keywords: 关键词列表

        Returns:
            匹配得分
        """
        if not keywords:
            return 0.0

        # 合并文献的关键词和标题词汇
        ref_words = set(ref.keywords)
        ref_words.update([w.lower() for w in ref.title.split() if len(w) > 2])

        # 计算关键词重叠率
        query_words = set([k.lower() for k in keywords])
        overlap = len(query_words & ref_words)
        total = len(query_words)

        return overlap / total if total > 0 else 0.0

    def mark_used(self, ref_id: str, chapter: str) -> bool:
        """
        标记文献已被引用

        Args:
            ref_id: 文献 ID
            chapter: 使用章节

        Returns:
            是否成功标记
        """
        if ref_id not in self.references:
            return False

        ref = self.references[ref_id]
        if ref.used_count >= self.MAX_USE_PER_REFERENCE:
            return False

        ref.used_count += 1
        if chapter not in ref.chapters_used:
            ref.chapters_used.append(chapter)

        self.save()
        return True

    def export(
        self,
        format: str = "gbt7714",
        chapter: Optional[str] = None,
        include_used_count: bool = False
    ) -> str:
        """
        导出参考文献列表

        Args:
            format: 导出格式 (gbt7714, yaml, json)
            chapter: 仅导出指定章节的文献
            include_used_count: 是否包含引用次数

        Returns:
            导出的内容
        """
        # 收集要导出的文献
        refs_to_export = []

        if chapter and chapter in self.groups:
            for ref_id in self.groups[chapter]:
                if ref_id in self.references:
                    refs_to_export.append(self.references[ref_id])
        else:
            refs_to_export = list(self.references.values())

        # 按引用次数排序（高频引用优先）
        refs_to_export.sort(key=lambda x: x.citation_count, reverse=True)

        if format == "gbt7714":
            lines = [
                "# 参考文献",
                "",
                f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"> 文献总数: {len(refs_to_export)}",
                "",
                "---",
                ""
            ]

            for i, ref in enumerate(refs_to_export, 1):
                ref_line = ref.gb7714 if ref.gb7714 else self._format_gbt7714(ref, i)

                # 添加 DOI 链接
                if ref.doi and ref.doi_url:
                    if "[DOI]" not in ref_line:
                        ref_line += f" [DOI]({ref.doi_url})"

                lines.append(ref_line)

                if include_used_count:
                    lines.append(f"   > 已引用: {ref.used_count} 次")

                lines.append("")

            return "\n".join(lines)

        elif format == "yaml":
            data = {
                "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total": len(refs_to_export),
                "chapter": chapter,
                "references": [ref.to_dict() for ref in refs_to_export]
            }
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)

        elif format == "json":
            data = {
                "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total": len(refs_to_export),
                "chapter": chapter,
                "references": [ref.to_dict() for ref in refs_to_export]
            }
            return json.dumps(data, ensure_ascii=False, indent=2)

        return ""

    def _format_gbt7714(self, ref: PoolReference, index: int) -> str:
        """
        格式化为 GB/T 7714 标准格式

        Args:
            ref: 参考文献
            index: 序号

        Returns:
            GB/T 7714 格式字符串
        """
        # 作者格式化
        if len(ref.authors) <= 3:
            authors_str = ", ".join(ref.authors)
        else:
            authors_str = ", ".join(ref.authors[:3]) + ", 等"

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

        return f"[{index}] {ref_str}"

    def get_stats(self) -> Dict:
        """
        获取文献池统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total": len(self.references),
            "verified": sum(1 for r in self.references.values() if r.cross_verified),
            "chinese": sum(1 for r in self.references.values() if r.language == "zh"),
            "english": sum(1 for r in self.references.values() if r.language == "en"),
            "used_count": sum(r.used_count for r in self.references.values()),
            "chapters": len(self.metadata["chapters"]),
            "over_used": sum(1 for r in self.references.values() if r.used_count >= self.MAX_USE_PER_REFERENCE)
        }

        return stats

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print("\n=== 文献池统计 ===")
        print(f"文献总数: {stats['total']}")
        print(f"已验证: {stats['verified']} ({stats['verified']/stats['total']*100:.1f}%)")
        print(f"中文文献: {stats['chinese']}")
        print(f"英文文献: {stats['english']}")
        print(f"总引用次数: {stats['used_count']}")
        print(f"章节分组: {stats['chapters']}")
        print(f"达引用上限: {stats['over_used']}")


def main():
    """main"""
    parser = argparse.ArgumentParser(description="已验证文献池管理器")

    parser.add_argument("--init", action="store_true", help="初始化文献池")
    parser.add_argument("--load", action="store_true", help="加载文献池")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--file", "-f", help="文献池文件路径或导入文件路径")
    parser.add_argument("--chapter", "-c", help="章节名称")
    parser.add_argument("--add", action="store_true", help="添加文献")
    parser.add_argument("--recommend", action="store_true", help="推荐文献")
    parser.add_argument("--export", action="store_true", help="导出参考文献")
    parser.add_argument("--keywords", "-k", nargs="+", help="关键词列表")
    parser.add_argument("--limit", "-l", type=int, default=5, help="数量限制")
    parser.add_argument("--exclude-used", action="store_true", help="推荐时排除已达到引用上限的文献")
    parser.add_argument("--format", choices=["gbt7714", "yaml", "json"], default="gbt7714", help="导出格式")
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()

    # 确定文献池文件路径
    pool_file = args.file if args.file and not args.add else None
    pool = VerifiedReferencePool(pool_file)

    if args.init:
        # 初始化文献池
        pool.metadata["pool_id"] = args.chapter or "thesis_references"
        pool.save()
        print(f"[成功] 初始化文献池: {pool.pool_file}")

    elif args.load or args.stats:
        # 加载并显示统计
        pool.print_stats()

    elif args.add:
        # 批量添加文献
        if not args.file:
            print("[错误] 请指定导入文件: --file <path>")
            return

        import_file = Path(args.file)
        if not import_file.exists():
            print(f"[错误] 文件不存在: {args.file}")
            return

        # 加载导入文件
        with open(import_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) if import_file.suffix == ".yaml" else json.load(f)

        refs = data.get("references", [])
        added = pool.add_references(refs, chapter=args.chapter, keywords=args.keywords)
        print(f"[成功] 添加 {added} 条文献")

    elif args.recommend:
        # 推荐文献
        if not args.keywords:
            print("[错误] 请指定关键词: --keywords <word1> <word2> ...")
            return

        recommendations = pool.recommend(
            keywords=args.keywords,
            chapter=args.chapter,
            limit=args.limit,
            exclude_used=args.exclude_used or True
        )

        print("\n=== 推荐文献 ===")
        for i, ref in enumerate(recommendations, 1):
            print(f"\n{i}. {ref.title}")
            print(f"   作者: {', '.join(ref.authors[:3])}")
            print(f"   年份: {ref.year}")
            print(f"   DOI: {ref.doi_url}")
            print(f"   引用数: {ref.citation_count}")
            print(f"   验证: {'[OK]' if ref.cross_verified else '[FAIL]'}")

    elif args.export:
        # 导出参考文献
        output = pool.export(
            format=args.format,
            chapter=args.chapter,
            include_used_count=True
        )

        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"[成功] 导出到: {args.output}")
        else:
            print(output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
