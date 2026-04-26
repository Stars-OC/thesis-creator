# -*- coding: utf-8 -*-
"""
文献合并去重脚本（Reference Merger）

功能：
1. 合并多个 YAML 文献文件
2. 基于 DOI + 标题相似度去重
3. 按 relevance_score 综合排序，选出最相关的 x 篇
4. 检查中英文文献均包含
5. 重新编号输出到 workspace/references/verified_references.yaml

使用方法：
    # 合并目录下所有 YAML 文献文件，选出最相关 25 篇
    python scripts/reference_merger.py -i workspace/references/ --top 25

    # 合并指定文件
    python scripts/reference_merger.py -i workspace/references/search_rag.yaml workspace/references/search_vector.yaml --top 30

    # 包含已有的文献池
    python scripts/reference_merger.py -i workspace/references/ --existing workspace/references/verified_references.yaml --top 25
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Optional

try:
    import yaml
except ImportError:
    print("[错误] 需要 PyYAML，请运行: pip install pyyaml")
    sys.exit(1)


def load_yaml_file(path: Path) -> List[Dict]:
    """加载单个 YAML 文献文件，返回 references 列表"""
    if not path.exists():
        print(f"[警告] 文件不存在: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"[警告] {path.name} YAML 解析失败: {e}")
        return []

    if not data:
        return []

    refs = data.get("references", [])
    if not refs:
        print(f"[警告] {path.name} 中无 references 条目")
    return refs


def load_from_directory(dir_path: Path) -> List[Dict]:
    """加载目录下所有 YAML 文献文件"""
    all_refs = []
    yaml_files = list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))

    if not yaml_files:
        print(f"[警告] 目录 {dir_path} 中无 YAML 文件")
        return []

    for f in sorted(yaml_files):
        refs = load_yaml_file(f)
        if refs:
            print(f"[加载] {f.name}: {len(refs)} 条")
            all_refs.extend(refs)

    return all_refs


def title_similarity(t1: str, t2: str) -> float:
    """计算标题相似度"""
    if not t1 or not t2:
        return 0.0
    s1 = t1.lower().strip()
    s2 = t2.lower().strip()
    if s1 == s2:
        return 1.0
    return SequenceMatcher(None, s1, s2).ratio()


def compute_score(ref: Dict) -> float:
    """计算综合得分：relevance_score(0.4) + 引用数(0.2) + 时效性(0.2) + 验证状态(0.2)"""
    relevance = float(ref.get("relevance_score", 0.0)) * 0.4
    citations = min(int(ref.get("citation_count", 0)) / 1000, 1.0) * 0.2

    current_year = datetime.now().year
    year = int(ref.get("year", 0))
    year_diff = current_year - year if year else 10
    year_score = max(0, 1 - year_diff / 10) * 0.2

    verified = 0.2 if ref.get("cross_verified") or ref.get("verified") else 0.1

    return relevance + citations + year_score + verified


def deduplicate(refs: List[Dict]) -> List[Dict]:
    """基于 DOI + 标题相似度去重"""
    deduped = []
    seen_dois = set()
    seen_titles = []

    for ref in refs:
        doi = ref.get("doi", "")
        title = ref.get("title", "")

        # DOI 去重
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)

        # 标题相似度去重（阈值 0.85）
        is_dup = False
        for seen_t in seen_titles:
            if title_similarity(title, seen_t) > 0.85:
                is_dup = True
                break

        if not is_dup:
            deduped.append(ref)
            seen_titles.append(title)

    return deduped


def check_language_balance(refs: List[Dict]) -> Dict[str, int]:
    """检查中英文文献分布"""
    zh_count = 0
    en_count = 0
    for ref in refs:
        lang = ref.get("language", "")
        title = ref.get("title", "")
        if lang == "zh" or (not lang and re.findall(r"[一-鿿]", title)):
            zh_count += 1
        else:
            en_count += 1
    return {"zh": zh_count, "en": en_count}


def select_top(refs: List[Dict], top_n: int) -> List[Dict]:
    """按综合得分排序并选出 top_n 篇，同时确保中英文文献都有"""
    sorted_refs = sorted(refs, key=compute_score, reverse=True)
    selected = sorted_refs[:top_n]

    # 确保中英文文献都有
    lang_stats = check_language_balance(selected)
    if lang_stats["zh"] == 0 or lang_stats["en"] == 0:
        missing_lang = "zh" if lang_stats["zh"] == 0 else "en"
        print(f"[警告] 选出的 {top_n} 篇中缺少{('中文' if missing_lang == 'zh' else '英文')}文献，尝试补充...")

        # 从剩余文献中补充缺失语种
        remaining = sorted_refs[top_n:]
        supplement = []
        for ref in remaining:
            lang = ref.get("language", "")
            title = ref.get("title", "")
            is_missing_lang = (
                (missing_lang == "zh" and (lang == "zh" or re.findall(r"[一-鿿]", title)))
                or (missing_lang == "en" and lang != "zh" and not re.findall(r"[一-鿿]", title))
            )
            if is_missing_lang:
                supplement.append(ref)
                if len(supplement) >= 5:  # 最多补充 5 篇
                    break

        if supplement:
            selected.extend(supplement)
            new_stats = check_language_balance(selected)
            print(f"[补充] 添加了 {len(supplement)} 篇{('中文' if missing_lang == 'zh' else '英文')}文献")
        else:
            print(f"[警告] 未找到可补充的{('中文' if missing_lang == 'zh' else '英文')}文献")

    return selected


def renumber(refs: List[Dict]) -> List[Dict]:
    """重新编号 ref_id"""
    for i, ref in enumerate(refs, 1):
        ref["id"] = f"ref_{i:03d}"
    return refs


def save_yaml(refs: List[Dict], output_path: Path, pool_id: str = "thesis_references"):
    """保存为 YAML 格式"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "pool_id": pool_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "total": len(refs),
        "references": refs,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"[完成] 已保存 {len(refs)} 篇文献到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="文献合并去重脚本")
    parser.add_argument(
        "-i", "--inputs", nargs="+", required=True,
        help="输入文件或目录路径（支持多个）",
    )
    parser.add_argument(
        "-e", "--existing", type=str, default=None,
        help="已有的文献池路径（合并时保留）",
    )
    parser.add_argument(
        "--top", "-t", type=int, default=25,
        help="选出最相关的 N 篇（默认 25）",
    )
    parser.add_argument(
        "-o", "--output", type=str, default="workspace/references/verified_references.yaml",
        help="输出文件路径",
    )
    parser.add_argument(
        "--pool-id", type=str, default="thesis_references",
        help="文献池 ID",
    )

    args = parser.parse_args()

    # 1. 加载所有文献
    all_refs = []

    # 加载已有文献池
    if args.existing:
        existing_path = Path(args.existing)
        existing_refs = load_yaml_file(existing_path)
        if existing_refs:
            print(f"[加载] 已有文献池 {existing_path.name}: {len(existing_refs)} 条")
            all_refs.extend(existing_refs)

    # 加载输入文件/目录
    for input_path_str in args.inputs:
        input_path = Path(input_path_str)
        if input_path.is_dir():
            all_refs.extend(load_from_directory(input_path))
        else:
            refs = load_yaml_file(input_path)
            if refs:
                print(f"[加载] {input_path.name}: {len(refs)} 条")
                all_refs.extend(refs)

    total_loaded = len(all_refs)
    print(f"\n[统计] 共加载 {total_loaded} 条文献")

    if total_loaded == 0:
        print("[错误] 未加载到任何文献，退出")
        sys.exit(1)

    # 2. 去重
    deduped = deduplicate(all_refs)
    print(f"[去重] {total_loaded} → {len(deduped)} 条")

    # 3. 选出最相关的 x 篇
    selected = select_top(deduped, args.top)
    print(f"[筛选] 选出最相关 {len(selected)} 篇")

    # 4. 中英文检查
    lang_stats = check_language_balance(selected)
    print(f"[语言] 中文: {lang_stats['zh']} 篇, 英文: {lang_stats['en']} 篇")
    if lang_stats["zh"] == 0 or lang_stats["en"] == 0:
        print("[警告] 参考文献缺少中文或英文文献！")

    # 5. 重新编号
    selected = renumber(selected)

    # 6. 保存
    output_path = Path(args.output)
    save_yaml(selected, output_path, pool_id=args.pool_id)

    # 打印摘要
    print(f"\n{'='*40}")
    print(f"文献合并去重完成")
    print(f"  加载: {total_loaded} 条")
    print(f"  去重: {len(deduped)} 条")
    print(f"  选出: {len(selected)} 篇")
    print(f"  中文: {lang_stats['zh']} | 英文: {lang_stats['en']}")
    print(f"  输出: {output_path}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
