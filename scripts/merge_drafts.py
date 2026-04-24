#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文章节合并脚本

功能：
1. 按正确顺序合并 drafts 文件夹中的各章节 MD 文件
2. 支持从 outline.md 读取章节标题，按实际名称匹配文件
3. 自动兼容多种章节命名格式（chapter_1.md / chapter-1.md / chapter_1_xxx.md / 第1章xxx.md）
4. 自动识别并合并摘要文件（如存在）
5. 引用编号重排并生成独立参考文献文件（存放在 drafts/ 目录）
6. 生成合并报告

使用方法：
    python scripts/merge_drafts.py --input ../thesis-workspace/workspace/drafts/ --output ../thesis-workspace/workspace/final/论文终稿.md --references ../thesis-workspace/workspace/verified_references.yaml --outline ../thesis-workspace/workspace/outline.md
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("[警告] PyYAML 未安装，参考文献生成功能不可用")
    print("安装命令: pip install pyyaml")


# 正文章节数量（按顺序合并）
CHAPTER_COUNT = 7

# 摘要文件候选名（可选）
ABSTRACT_CANDIDATES = [
    "摘要.md",
    "abstract.md",
    "chapter_0.md",
    "chapter-0.md",
    "chapter_0_摘要.md",
    "chapter-0-摘要.md"
]

# 分页标记（用于 Word 转换时识别）
PAGE_BREAK_MARKER = "\n\n<!-- PAGE_BREAK -->\n\n"

# 预编译正则表达式（用于内容清理与引用处理）
RE_HORIZONTAL_LINE = re.compile(r'\n-{3,}\n')
RE_HORIZONTAL_LINE_START = re.compile(r'\n-{3,}\s*\n')
RE_MULTIPLE_NEWLINES = re.compile(r'\n{4,}')
RE_ASTERISK_LINE = re.compile(r'\n\*{3,}\n')
RE_TRAILING_WHITESPACE = re.compile(r'[ \t]+\n')
RE_TEMP_REF = re.compile(r'\[ref_(\d+)\]')


class DraftMerger:
    """论文章节合并器"""

    def __init__(self, input_dir: str, output_path: str, references_yaml: str = None, outline_path: str = None):
        self.input_dir = Path(input_dir)
        self.output_path = Path(output_path)
        self.references_yaml = Path(references_yaml) if references_yaml else None
        self.outline_path = Path(outline_path) if outline_path else None
        self.ref_pool: Dict[str, Dict] = {}
        self.merge_targets: List[str] = []
        # 从大纲解析出的章节标题列表，格式: [(index, title), ...]
        self.outline_chapters: List[Tuple[int, str]] = []

        self.merge_report = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'input_dir': str(self.input_dir),
            'output_path': str(self.output_path),
            'chapters': [],
            'total_chars': 0,
            'total_words': 0,
            'missing_chapters': [],
            'errors': [],
            'references_count': 0
        }

    @staticmethod
    def _console_safe(text: str) -> str:
        """将文本转换为当前控制台可编码字符串，避免 Windows GBK 崩溃"""
        encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
        try:
            text.encode(encoding)
            return text
        except UnicodeEncodeError:
            return text.encode(encoding, errors='replace').decode(encoding, errors='replace')

    def _list_markdown_files(self) -> List[str]:
        if not self.input_dir.exists() or not self.input_dir.is_dir():
            return []
        # 排除参考文献.md，避免误合并
        return [p.name for p in self.input_dir.iterdir()
                if p.is_file() and p.suffix.lower() == '.md'
                and p.stem != '参考文献']

    def parse_outline(self) -> bool:
        """从 outline.md 解析一级章节标题（第N章），用于精准匹配 drafts 中文件名"""
        if not self.outline_path or not self.outline_path.exists():
            print("[信息] 未指定大纲文件，使用默认模式匹配")
            return False

        try:
            content = self.outline_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[警告] 读取大纲文件失败: {e}")
            return False

        # 每次解析前先清空，避免重复调用时累积
        self.outline_chapters = []

        # 仅匹配一级章节："## 第1章 绪论"
        # 不匹配子章节："### 1.1 研究背景"
        chapter_pattern = re.compile(
            r'^\s*#{1,3}\s*第\s*(\d+)\s*章(?:\s*[：:、.．-]?\s*(.+))?\s*$',
            re.MULTILINE
        )

        seen_index = set()
        for match in chapter_pattern.finditer(content):
            idx = int(match.group(1))
            title = (match.group(2) or "").strip()

            # 同一章节编号只保留第一次出现（避免目录重复）
            if idx in seen_index:
                continue
            seen_index.add(idx)
            self.outline_chapters.append((idx, title))

        self.outline_chapters.sort(key=lambda x: x[0])

        if self.outline_chapters:
            print(f"[信息] 从大纲解析到 {len(self.outline_chapters)} 个一级章节标题:")
            for idx, title in self.outline_chapters:
                if title:
                    print(self._console_safe(f"  第{idx}章: {title}"))
                else:
                    print(self._console_safe(f"  第{idx}章"))
        else:
            print("[警告] 未能从大纲中解析出一级章节标题，使用默认模式匹配")

        return len(self.outline_chapters) > 0

    def _find_abstract_file(self, file_names: List[str]) -> Optional[str]:
        lowered = {name.lower(): name for name in file_names}

        for candidate in ABSTRACT_CANDIDATES:
            exact = lowered.get(candidate.lower())
            if exact:
                return exact

        for name in file_names:
            stem = Path(name).stem.lower()
            if stem.startswith('摘要') or stem.startswith('abstract'):
                return name

        return None

    def _find_chapter_file(self, file_names: List[str], index: int) -> Optional[str]:
        """查找指定章节的文件，优先使用大纲标题匹配"""

        # ---- 优先级1: 从大纲标题生成精确文件名模式 ----
        outline_title = None
        for ch_idx, ch_title in self.outline_chapters:
            if ch_idx == index:
                outline_title = ch_title
                break

        if outline_title:
            # 生成可能的文件名变体：
            # "第1章 绪论" → chapter_1_绪论.md / chapter-1-绪论.md / 第1章绪论.md / 第1章 绪论.md
            clean_title = re.sub(r'[\\/:*?"<>|]', '', outline_title).strip()
            title_patterns = [
                re.compile(rf'^chapter[_-]{index}[_-]{re.escape(clean_title)}\.md$', re.IGNORECASE),
                re.compile(rf'^chapter[_-]{index}[_-].*\.md$', re.IGNORECASE),
                re.compile(rf'^第\s*{index}\s*章\s*{re.escape(clean_title)}\.md$', re.IGNORECASE),
                re.compile(rf'^第\s*{index}\s*章\s*.*\.md$', re.IGNORECASE),
            ]

            for pattern in title_patterns:
                matched = [name for name in file_names if pattern.match(name)]
                if matched:
                    matched.sort(key=lambda n: (len(n), n.lower()))
                    return matched[0]

            # 模糊匹配：文件名包含章节标题关键词
            title_keywords = [kw for kw in re.split(r'[，,、\s]+', clean_title) if len(kw) >= 2]
            for name in file_names:
                stem = Path(name).stem
                # 必须包含章节编号
                has_index = bool(re.search(rf'(chapter[_-]?{index}|第\s*{index}\s*章)', stem, re.IGNORECASE))
                if has_index and title_keywords:
                    # 至少包含一个标题关键词
                    if any(kw in stem for kw in title_keywords):
                        return name

        # ---- 优先级2: 默认模式匹配（兜底） ----
        patterns = [
            re.compile(rf'^chapter[_-]?{index}\.md$', re.IGNORECASE),
            re.compile(rf'^chapter[_-]?{index}[_-].*\.md$', re.IGNORECASE),
            re.compile(rf'^第{index}章.*\.md$', re.IGNORECASE),
        ]

        matched = [name for name in file_names if any(p.match(name) for p in patterns)]
        if not matched:
            return None

        matched.sort(key=lambda n: (len(n), n.lower()))
        return matched[0]

    def _build_merge_targets(self) -> Tuple[List[str], List[str]]:
        files = self._list_markdown_files()
        targets: List[str] = []
        missing: List[str] = []

        # 查找摘要文件
        abstract_file = self._find_abstract_file(files)
        if abstract_file:
            targets.append(abstract_file)

        # 确定要合并的章节数量：优先使用大纲中的章节数，否则用默认值
        chapter_count = max(idx for idx, _ in self.outline_chapters) if self.outline_chapters else CHAPTER_COUNT

        for index in range(1, chapter_count + 1):
            chapter_file = self._find_chapter_file(files, index)
            if chapter_file:
                targets.append(chapter_file)
            else:
                # 生成更有意义的缺失提示
                outline_title = None
                for ch_idx, ch_title in self.outline_chapters:
                    if ch_idx == index:
                        outline_title = ch_title
                        break
                if outline_title:
                    missing.append(f"第{index}章 {outline_title} (chapter_{index}_*.md)")
                else:
                    missing.append(f"chapter_{index}.md")

        # 查找致谢文件（可选）
        thanks_candidates = ["致谢.md", "acknowledgement.md", "chapter_99.md", "chapter-99.md"]
        lowered = {name.lower(): name for name in files}
        for candidate in thanks_candidates:
            exact = lowered.get(candidate.lower())
            if exact:
                targets.append(exact)
                break

        return targets, missing

    def validate_input(self) -> Tuple[bool, List[str]]:
        targets, missing = self._build_merge_targets()
        self.merge_targets = targets
        self.merge_report['missing_chapters'] = missing

        if not targets:
            if not missing:
                missing.append("未找到可合并的章节文件")
            return False, missing

        return len(missing) == 0, missing

    def read_chapter(self, filename: str) -> Optional[str]:
        chapter_path = self.input_dir / filename
        if not chapter_path.exists():
            return None

        try:
            return chapter_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            self.merge_report['errors'].append(f"文件不存在: {filename}")
            return None
        except PermissionError:
            self.merge_report['errors'].append(f"无权限读取: {filename}")
            return None
        except UnicodeDecodeError as e:
            self.merge_report['errors'].append(f"文件编码错误: {filename} - {str(e)}")
            return None

    def clean_content(self, content: str) -> str:
        content = RE_HORIZONTAL_LINE.sub('\n\n', content)
        content = RE_HORIZONTAL_LINE_START.sub('\n\n', content)
        content = re.sub(r'^-{3,}\s*\n', '', content)
        content = re.sub(r'\n\s*-{3,}$', '', content)
        content = RE_ASTERISK_LINE.sub('\n\n', content)
        content = RE_MULTIPLE_NEWLINES.sub('\n\n\n', content)
        content = RE_TRAILING_WHITESPACE.sub('\n', content)
        content = content.lstrip('\n').rstrip('\n')
        return content

    def _needs_page_break(self, filename: str) -> bool:
        stem = Path(filename).stem.lower()
        if stem.startswith('摘要') or stem.startswith('abstract'):
            return False
        if stem.startswith('参考文献') or stem.startswith('致谢'):
            return False
        return True

    def add_page_break(self, content: str) -> str:
        return PAGE_BREAK_MARKER + content

    def get_chapter_info(self, filename: str, content: str) -> Dict:
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        total_chars = len(content)

        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else filename

        return {
            'filename': filename,
            'title': title,
            'chinese_chars': chinese_chars,
            'english_words': english_words,
            'total_chars': total_chars,
            'status': 'success'
        }

    def load_references_pool(self) -> bool:
        if not self.references_yaml or not self.references_yaml.exists():
            print(f"[警告] 文献池文件不存在: {self.references_yaml}")
            return False

        if not YAML_AVAILABLE:
            print("[警告] PyYAML 未安装，无法加载文献池")
            return False

        try:
            data = yaml.safe_load(self.references_yaml.read_text(encoding='utf-8'))
            refs = data.get('references', []) if isinstance(data, dict) else []
            for ref in refs:
                ref_id = ref.get('id', '')
                if ref_id:
                    self.ref_pool[ref_id] = ref
            print(f"[信息] 已加载文献池: {len(self.ref_pool)} 篇文献")
            return True
        except Exception as e:
            print(f"[警告] 加载文献池失败: {e}")
            return False

    def collect_cited_references(self, content: str) -> List[str]:
        seen = set()
        ordered = []

        for match in RE_TEMP_REF.finditer(content):
            ref_id = f"ref_{match.group(1)}"
            if ref_id not in seen:
                seen.add(ref_id)
                ordered.append(ref_id)

        return ordered

    def renumber_references(self, content: str) -> Tuple[str, Dict[str, int]]:
        cited_refs = self.collect_cited_references(content)
        mapping: Dict[str, int] = {}

        for idx, ref_id in enumerate(cited_refs, start=1):
            mapping[ref_id] = idx

        def replace_ref(match):
            ref_id = f"ref_{match.group(1)}"
            if ref_id in mapping:
                return f"[{mapping[ref_id]}]"
            return match.group(0)

        new_content = RE_TEMP_REF.sub(replace_ref, content)
        return new_content, mapping

    def generate_references_md(self, mapping: Dict[str, int], output_path: Path) -> bool:
        if not mapping:
            print("[警告] 没有引用编号需要生成参考文献")
            return False

        lines = ["# 参考文献", ""]
        sorted_refs = sorted(mapping.items(), key=lambda x: x[1])

        for ref_id, num in sorted_refs:
            ref_data = self.ref_pool.get(ref_id)
            if ref_data:
                gb7714 = ref_data.get('gb7714', '')
                if gb7714:
                    gb7714 = re.sub(r'^\[\d+\]', f'[{num}]', gb7714)
                    lines.append(gb7714)
                else:
                    authors = ref_data.get('authors', [])
                    title = ref_data.get('title', '')
                    year = ref_data.get('year', '')
                    doi = ref_data.get('doi', '')
                    doi_url = ref_data.get('doi_url', '')
                    journal = ref_data.get('journal', '')
                    volume = ref_data.get('volume', '')
                    issue = ref_data.get('issue', '')
                    pages = ref_data.get('pages', '')

                    if len(authors) <= 3:
                        authors_str = ", ".join(authors)
                    else:
                        authors_str = ", ".join(authors[:3]) + ", 等"

                    ref_type = "[J]" if journal else "[C]"
                    parts = [f"[{num}] {authors_str}. {title}{ref_type}"]

                    if journal:
                        parts.append(journal)

                    if year:
                        year_part = f", {year}"
                        if volume:
                            year_part += f", {volume}"
                            if issue:
                                year_part += f"({issue})"
                        parts.append(year_part)

                    if pages:
                        parts.append(f": {pages}")

                    ref_str = ". ".join([p for p in parts if p]) + "."

                    if doi and doi_url:
                        ref_str += f" [DOI]({doi_url})"

                    lines.append(ref_str)
            else:
                lines.append(f"[{num}] [未找到文献: {ref_id}]")

            lines.append("")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text('\n'.join(lines), encoding='utf-8')
            self.merge_report['references_count'] = len(sorted_refs)
            print(f"[成功] 参考文献已生成: {output_path} ({len(sorted_refs)} 篇)")
            return True
        except Exception as e:
            print(f"[失败] 生成参考文献失败: {e}")
            self.merge_report['errors'].append(f"生成参考文献失败: {str(e)}")
            return False

    def merge(self) -> bool:
        print("[信息] 开始合并论文章节...")
        print(f"[信息] 输入目录: {self.input_dir}")
        print(f"[信息] 输出文件: {self.output_path}")
        if self.references_yaml:
            print(f"[信息] 文献池: {self.references_yaml}")
        print()

        # 解析大纲文件（如提供）
        if self.outline_path:
            self.parse_outline()

        _, missing = self.validate_input()
        if missing:
            print("[警告] 以下章节文件缺失:")
            for item in missing:
                print(self._console_safe(f"  - {item}"))
            print()

        if self.references_yaml:
            self.load_references_pool()

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        merged_content: List[str] = []
        total_chars = 0
        total_words = 0

        for index, filename in enumerate(self.merge_targets):
            content = self.read_chapter(filename)

            if content is None:
                self.merge_report['chapters'].append({
                    'filename': filename,
                    'title': '缺失',
                    'chinese_chars': 0,
                    'english_words': 0,
                    'total_chars': 0,
                    'status': 'missing'
                })
                continue

            content = self.clean_content(content)
            chapter_info = self.get_chapter_info(filename, content)
            self.merge_report['chapters'].append(chapter_info)

            total_chars += chapter_info['total_chars']
            total_words += chapter_info['chinese_chars'] + chapter_info['english_words']

            if index > 0 and self._needs_page_break(filename):
                content = self.add_page_break(content)

            merged_content.append(content)
            print(f"[成功] 已合并: {filename} ({chapter_info['chinese_chars']} 字)")

        self.merge_report['total_chars'] = total_chars
        self.merge_report['total_words'] = total_words

        if not merged_content:
            self.merge_report['errors'].append("没有成功合并任何章节")
            print("[失败] 没有成功合并任何章节")
            return False

        final_content = '\n'.join(merged_content)

        ref_mapping: Dict[str, int] = {}
        if self.ref_pool:
            print("[信息] 开始引用编号重排...")
            final_content, ref_mapping = self.renumber_references(final_content)
            print(f"[信息] 共发现 {len(ref_mapping)} 个引用编号")

            # 按需求：参考文献放在 drafts 目录，并内联合并到终稿
            ref_output_path = self.input_dir / "参考文献.md"
            if self.generate_references_md(ref_mapping, ref_output_path):
                try:
                    references_content = ref_output_path.read_text(encoding='utf-8').strip()
                    if references_content:
                        final_content += f"{PAGE_BREAK_MARKER}{references_content}\n"
                except Exception as e:
                    self.merge_report['errors'].append(f"读取参考文献失败: {str(e)}")
                    print(f"[警告] 参考文献读取失败，终稿未内联: {e}")

        if self.output_path.is_dir():
            self.merge_report['errors'].append(f"输出路径是目录，不是文件: {self.output_path}")
            print(f"[失败] 输出路径是目录，不是文件: {self.output_path}")
            return False

        temp_output = self.output_path.with_suffix('.tmp')
        try:
            temp_output.write_text(final_content, encoding='utf-8')
            temp_output.replace(self.output_path)

            print()
            print("[成功] 合并完成！")
            print(f"[信息] 输出文件: {self.output_path}")
            print(f"[信息] 总字符数: {total_chars}")
            print(f"[信息] 总字数: {total_words}")
            return True
        except PermissionError:
            self.merge_report['errors'].append(f"无权限写入输出文件: {self.output_path}")
            print(f"[失败] 无权限写入输出文件: {self.output_path}")
            if temp_output.exists():
                temp_output.unlink()
            return False
        except OSError as e:
            self.merge_report['errors'].append(f"写入输出文件失败: {str(e)}")
            print(f"[失败] 写入输出文件失败: {str(e)}")
            if temp_output.exists():
                temp_output.unlink()
            return False

    def print_report(self):
        print()
        print("=" * 60)
        print("[论文合并报告]")
        print("=" * 60)
        print(f"合并时间: {self.merge_report['timestamp']}")
        print(f"输入目录: {self.merge_report['input_dir']}")
        print(f"输出文件: {self.merge_report['output_path']}")
        print("-" * 60)
        print("章节详情:")
        print("-" * 60)

        for i, chapter in enumerate(self.merge_report['chapters'], 1):
            status_icon = "[OK]" if chapter['status'] == 'success' else "[缺失]"
            print(f"{i:2d}. {status_icon} {chapter['filename']}")
            if chapter['status'] == 'success':
                print(self._console_safe(f"      标题: {chapter['title']}"))
                print(f"      中文字数: {chapter['chinese_chars']} | 英文单词: {chapter['english_words']}")

        print("-" * 60)
        print("统计信息:")
        print(f"  成功合并: {len([c for c in self.merge_report['chapters'] if c['status'] == 'success'])} 个章节")
        print(f"  缺失章节: {len(self.merge_report['missing_chapters'])} 个")
        print(f"  总字符数: {self.merge_report['total_chars']}")
        print(f"  总字数: {self.merge_report['total_words']}")
        print("-" * 60)

        if self.merge_report['errors']:
            print("错误信息:")
            for error in self.merge_report['errors']:
                print(self._console_safe(f"  - {error}"))
            print("-" * 60)

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='论文章节合并脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python scripts/merge_drafts.py -i ../thesis-workspace/workspace/drafts/ -o ../thesis-workspace/workspace/final/论文终稿.md
    python scripts/merge_drafts.py --input ./drafts/ --output ./output/论文合并版.md
        """
    )

    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入目录路径（包含各章节 MD 文件的 drafts 文件夹）'
    )

    parser.add_argument(
        '--output', '-o',
        required=True,
        help='输出文件路径（合并后的 MD 文件）'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='不打印详细报告'
    )

    parser.add_argument(
        '--references', '-r',
        help='文献池 YAML 文件路径（用于引用编号重排和生成参考文献MD）'
    )

    parser.add_argument(
        '--outline',
        help='大纲文件路径（用于解析章节标题，精准匹配文件名）'
    )

    args = parser.parse_args()

    merger = DraftMerger(args.input, args.output, references_yaml=args.references, outline_path=args.outline)

    if not merger.input_dir.exists():
        print(f"[错误] 输入目录不存在: {merger.input_dir}")
        sys.exit(1)

    success = merger.merge()

    if not args.no_report:
        merger.print_report()

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
