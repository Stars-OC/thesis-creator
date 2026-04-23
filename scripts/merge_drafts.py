#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文章节合并脚本

功能：
1. 按正确顺序合并 drafts 文件夹中的各章节 MD 文件
2. 处理章节间的分隔符和分页标记
3. 生成合并报告

使用方法：
    python scripts/merge_drafts.py --input ../thesis-workspace/workspace/drafts/ --output ../thesis-workspace/workspace/final/论文终稿.md
"""

import os
import re
import sys
import json
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


# 章节顺序定义（必须按此顺序合并）
CHAPTER_ORDER = [
    "摘要.md",
    "第1章_绪论.md",
    "第2章_相关技术与开发环境.md",
    "第3章_系统需求分析.md",
    "第4章_系统设计.md",
    "第5章_系统实现.md",
    "第6章_系统测试.md",
    "第7章_总结与展望.md",
    "致谢.md"
]

# 注意：参考文献.md 不在 CHAPTER_ORDER 中，因为它由脚本从文献池自动生成

# 分页标记（用于 Word 转换时识别）
PAGE_BREAK_MARKER = "\n\n<!-- PAGE_BREAK -->\n\n"

# 章节分隔符
CHAPTER_SEPARATOR = "\n\n---\n\n"

# 不需要前置分页的章节
NO_PAGE_BREAK_CHAPTERS = ['摘要.md', '参考文献.md', '致谢.md']

# 预编译正则表达式（用于内容清理）
RE_HORIZONTAL_LINE = re.compile(r'\n-{3,}\n')
RE_HORIZONTAL_LINE_START = re.compile(r'\n-{3,}\s*\n')
RE_MULTIPLE_NEWLINES = re.compile(r'\n{4,}')
RE_ASTERISK_LINE = re.compile(r'\n\*{3,}\n')
RE_TRAILING_WHITESPACE = re.compile(r'[ \t]+\n')


class DraftMerger:
    """论文章节合并器"""

    def __init__(self, input_dir: str, output_path: str, references_yaml: str = None):
        """
        初始化合并器

        Args:
            input_dir: 输入目录（drafts 文件夹路径）
            output_path: 输出文件路径
            references_yaml: 文献池 YAML 文件路径（可选）
        """
        self.input_dir = Path(input_dir)
        self.output_path = Path(output_path)
        self.references_yaml = Path(references_yaml) if references_yaml else None
        self.ref_pool = {}  # ref_id -> ref_data 的映射
        self.ref_order = []  # 按正文出现顺序的 ref_id 列表
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

    def validate_input(self) -> Tuple[bool, List[str]]:
        """
        验证输入文件是否存在

        Returns:
            (是否全部存在, 缺失的章节列表)
        """
        missing = []

        for chapter in CHAPTER_ORDER:
            chapter_path = self.input_dir / chapter
            if not chapter_path.exists():
                missing.append(chapter)

        self.merge_report['missing_chapters'] = missing

        return len(missing) == 0, missing

    def read_chapter(self, filename: str) -> Optional[str]:
        """
        读取单个章节内容

        Args:
            filename: 章节文件名

        Returns:
            章节内容（如果文件存在），否则返回 None
        """
        chapter_path = self.input_dir / filename

        if not chapter_path.exists():
            return None

        try:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
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
        """
        清理内容中的冗余标记

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        # 移除连续多个 ---（3个以上的水平线）
        content = RE_HORIZONTAL_LINE.sub('\n\n', content)
        content = RE_HORIZONTAL_LINE_START.sub('\n\n', content)

        # 移除开头的 ---
        content = re.sub(r'^-{3,}\s*\n', '', content)

        # 移除结尾的 ---
        content = re.sub(r'\n\s*-{3,}$', '', content)

        # 移除多余的星号分隔线
        content = RE_ASTERISK_LINE.sub('\n\n', content)

        # 压缩多个空行为最多两个
        content = RE_MULTIPLE_NEWLINES.sub('\n\n\n', content)

        # 移除行尾空白
        content = RE_TRAILING_WHITESPACE.sub('\n', content)

        # 移除开头的空白
        content = content.lstrip('\n')

        # 移除结尾的空白
        content = content.rstrip('\n')

        return content

    def add_page_break(self, content: str, is_chapter: bool = True) -> str:
        """
        添加分页标记

        Args:
            content: 章节内容
            is_chapter: 是否为正文章节（摘要、参考文献、致谢不需要分页）

        Returns:
            带分页标记的内容
        """
        # 对于正文章节，在开头添加分页标记
        if is_chapter:
            return PAGE_BREAK_MARKER + content
        return content

    def get_chapter_info(self, filename: str, content: str) -> Dict:
        """
        获取章节信息

        Args:
            filename: 文件名
            content: 章节内容

        Returns:
            章节信息字典
        """
        # 计算字数（中文字符）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        # 计算英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        # 计算总字符数
        total_chars = len(content)

        # 获取章节标题
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

    # 预编译临时引用编号的正则
    pattern_sub_ref = re.compile(r'\[ref_(\d+)\]')

    def load_references_pool(self) -> bool:
        """
        加载文献池 YAML 文件

        Returns:
            是否成功加载
        """
        if not self.references_yaml or not self.references_yaml.exists():
            print(f"[警告] 文献池文件不存在: {self.references_yaml}")
            return False

        if not YAML_AVAILABLE:
            print(f"[警告] PyYAML 未安装，无法加载文献池")
            return False

        try:
            with open(self.references_yaml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            refs = data.get('references', [])
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
        """
        收集文本中引用的临时编号（[ref_XXX] 格式）

        Args:
            content: 合并后的全部文本内容

        Returns:
            按出现顺序排列的 ref_id 列表（已去重）
        """
        # 匹配 [ref_001], [ref_012] 等临时引用编号
        pattern = re.compile(r'\[ref_(\d+)\]')
        seen = set()
        ordered = []

        for match in pattern.finditer(content):
            ref_id = f"ref_{match.group(1)}"
            if ref_id not in seen:
                seen.add(ref_id)
                ordered.append(ref_id)

        return ordered

    def renumber_references(self, content: str) -> Tuple[str, Dict[str, int]]:
        """
        将临时引用编号重排为正式编号

        Args:
            content: 合并后的全部文本内容

        Returns:
            (重排后的文本, 映射表 {ref_id: 正式编号})
        """
        cited_refs = self.collect_cited_references(content)
        mapping = {}
        current_num = 1

        for ref_id in cited_refs:
            mapping[ref_id] = current_num
            current_num += 1

        # 执行替换：[ref_001] -> [1]
        def replace_ref(match):
            ref_id = f"ref_{match.group(1)}"
            if ref_id in mapping:
                return f"[{mapping[ref_id]}]"
            return match.group(0)  # 未在文献池中的引用保留原样

        new_content = pattern_sub_ref.sub(replace_ref, content)
        return new_content, mapping

    def generate_references_md(self, mapping: Dict[str, int], output_path: Path) -> bool:
        """
        生成独立的参考文献 MD 文件

        Args:
            mapping: 映射表 {ref_id: 正式编号}
            output_path: 输出路径

        Returns:
            是否成功
        """
        if not mapping:
            print("[警告] 没有引用编号需要生成参考文献")
            return False

        lines = ["# 参考文献", ""]

        # 按正式编号排序
        sorted_refs = sorted(mapping.items(), key=lambda x: x[1])

        for ref_id, num in sorted_refs:
            ref_data = self.ref_pool.get(ref_id)
            if ref_data:
                # 优先使用预格式化的 GB/T 7714 格式
                gb7714 = ref_data.get('gb7714', '')
                if gb7714:
                    # 替换预格式化中的编号
                    gb7714 = re.sub(r'^\[\d+\]', f'[{num}]', gb7714)
                    lines.append(gb7714)
                else:
                    # 从字段手动构建 GB/T 7714 格式
                    authors = ref_data.get('authors', [])
                    title = ref_data.get('title', '')
                    year = ref_data.get('year', '')
                    doi = ref_data.get('doi', '')
                    doi_url = ref_data.get('doi_url', '')
                    journal = ref_data.get('journal', '')
                    volume = ref_data.get('volume', '')
                    issue = ref_data.get('issue', '')
                    pages = ref_data.get('pages', '')

                    # 作者格式化
                    if len(authors) <= 3:
                        authors_str = ", ".join(authors)
                    else:
                        authors_str = ", ".join(authors[:3]) + ", 等"

                    # 构建引用字符串
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

            lines.append("")  # 空行分隔

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            self.merge_report['references_count'] = len(sorted_refs)
            print(f"[成功] 参考文献已生成: {output_path} ({len(sorted_refs)} 篇)")
            return True

        except Exception as e:
            print(f"[失败] 生成参考文献失败: {e}")
            self.merge_report['errors'].append(f"生成参考文献失败: {str(e)}")
            return False


        """
        获取章节信息

        Args:
            filename: 文件名
            content: 章节内容

        Returns:
            章节信息字典
        """
        # 计算字数（中文字符）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        # 计算英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', content))
        # 计算总字符数
        total_chars = len(content)

        # 获取章节标题
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

    def merge(self) -> bool:
        """
        执行合并操作

        Returns:
            是否成功
        """
        print(f"[信息] 开始合并论文章节...")
        print(f"[信息] 输入目录: {self.input_dir}")
        print(f"[信息] 输出文件: {self.output_path}")
        if self.references_yaml:
            print(f"[信息] 文献池: {self.references_yaml}")
        print()

        # 验证输入
        all_exist, missing = self.validate_input()
        if missing:
            print(f"[警告] 以下章节文件缺失:")
            for m in missing:
                print(f"  - {m}")
            print()

        # 加载文献池（如果提供）
        if self.references_yaml:
            self.load_references_pool()

        # 创建输出目录
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 合并内容
        merged_content = []
        total_chars = 0
        total_words = 0

        for i, chapter in enumerate(CHAPTER_ORDER):
            content = self.read_chapter(chapter)

            if content is None:
                self.merge_report['chapters'].append({
                    'filename': chapter,
                    'title': '缺失',
                    'chinese_chars': 0,
                    'english_words': 0,
                    'total_chars': 0,
                    'status': 'missing'
                })
                continue

            # 清理内容
            content = self.clean_content(content)

            # 获取章节信息
            chapter_info = self.get_chapter_info(chapter, content)
            self.merge_report['chapters'].append(chapter_info)

            # 累计统计
            total_chars += chapter_info['total_chars']
            total_words += chapter_info['chinese_chars'] + chapter_info['english_words']

            # 判断是否需要分页（摘要、致谢不分页）
            is_chapter = chapter not in NO_PAGE_BREAK_CHAPTERS

            # 添加分页标记
            if i > 0:  # 第一个章节不需要分页
                content = self.add_page_break(content, is_chapter)

            merged_content.append(content)

            print(f"[成功] 已合并: {chapter} ({chapter_info['chinese_chars']} 字)")

        # 更新统计
        self.merge_report['total_chars'] = total_chars
        self.merge_report['total_words'] = total_words

        # 合并所有内容
        final_content = '\n'.join(merged_content)

        # 引用编号重排（如果有文献池）
        ref_mapping = {}
        if self.ref_pool:
            print(f"[信息] 开始引用编号重排...")
            final_content, ref_mapping = self.renumber_references(final_content)
            print(f"[信息] 共发现 {len(ref_mapping)} 个引用编号")

            # 生成独立的参考文献 MD 文件
            ref_output_path = self.output_path.parent / "参考文献.md"
            self.generate_references_md(ref_mapping, ref_output_path)

            # 在论文终稿末尾插入参考文献引用标记
            final_content += f"\n\n<!-- REFERENCES: {ref_output_path} -->\n"

        # 在文件开头添加标题和元信息
        header = f"""# 论文终稿

> 合并时间: {self.merge_report['timestamp']}
> 章节数量: {len([c for c in self.merge_report['chapters'] if c['status'] == 'success'])}
> 总字数: {total_words} 字
> 参考文献数: {len(ref_mapping)} 篇

---

"""

        final_content = header + final_content

        # 验证输出路径
        if self.output_path.is_dir():
            self.merge_report['errors'].append(f"输出路径是目录，不是文件: {self.output_path}")
            print(f"[失败] 输出路径是目录，不是文件: {self.output_path}")
            return False

        # 使用原子写入：先写临时文件，成功后重命名
        temp_output = self.output_path.with_suffix('.tmp')
        try:
            with open(temp_output, 'w', encoding='utf-8') as f:
                f.write(final_content)
            temp_output.rename(self.output_path)

            print()
            print(f"[成功] 合并完成！")
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
        """打印合并报告"""
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
                print(f"      标题: {chapter['title']}")
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
                print(f"  - {error}")
            print("-" * 60)

        print("=" * 60)


def main():
    """主函数"""
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

    args = parser.parse_args()

    # 创建合并器
    merger = DraftMerger(args.input, args.output, references_yaml=args.references)

    # 验证输入目录
    if not merger.input_dir.exists():
        print(f"[错误] 输入目录不存在: {merger.input_dir}")
        sys.exit(1)

    # 执行合并
    success = merger.merge()

    # 打印报告
    if not args.no_report:
        merger.print_report()

    # 退出
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()