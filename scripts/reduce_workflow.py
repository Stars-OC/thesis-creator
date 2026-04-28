#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
论文降重自动化流程脚本

整合以下流程：
1. 同义词替换
2. 生成大模型审核 Prompt
3. AIGC 检测
4. 输出报告

使用方法：
    python scripts/reduce_workflow.py --input workspace/final/论文终稿.md --output workspace/reduced/
"""

import os
import re
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional

# 增强版同义词词典
ENHANCED_SYNONYM_DICT = {
    # 高频名词
    "系统": ["平台", "体系", "架构", "框架", "整体", "应用平台"],
    "文档": ["资料", "文件", "素材", "文献", "文本材料"],
    "实现": ["完成", "达成", "落实", "构建", "实施", "开展"],
    "支持": ["支撑", "辅助", "配合", "保障", "提供服务"],
    "管理": ["管控", "治理", "运营", "统筹", "维护", "监管"],
    "功能": ["能力", "特性", "效用", "功用", "服务能力"],
    "技术": ["科技", "工艺", "技能", "手段", "方法"],
    "存储": ["保存", "存放", "保留", "记录", "持久化"],
    "通过": ["经由", "借助", "依靠", "利用", "采取", "运用"],
    "用户": ["使用者", "客户", "终端用户", "访问者", "操作人员"],
    "测试": ["检验", "验证", "考核", "测试验证", "实验", "评测"],
    "设计": ["构建", "开发", "规划", "制定", "架构设计"],
    "采用": ["使用", "运用", "应用", "选取", "采纳", "引入"],
    "问题": ["难题", "困境", "挑战", "议题", "课题", "疑问"],
    "包括": ["包含", "涵盖", "涉及", "囊括", "覆盖", "纳入"],
    "结果": ["成果", "产出", "结论", "成效", "效果"],
    "内容": ["信息内容", "文本内容", "资料内容", "数据内容"],
    "响应": ["回应", "反馈", "返回结果", "输出结果"],
    "进行": ["开展", "实施", "执行", "着手", "推进"],
    "服务": ["服务模块", "功能服务", "后台服务", "服务组件"],
    "企业": ["公司", "组织", "机构", "商业机构"],
    "生成": ["产生", "创建", "输出", "生成输出", "自动生成"],
    "能力": ["本领", "功能", "实力", "服务能力", "处理能力"],
    "处理": ["处置", "应对", "解决", "操作", "数据处理"],
    "需求": ["要求", "需要", "诉求", "期望", "业务需求"],
    "模块": ["组件", "功能模块", "服务模块", "子系统"],
    "应用": ["运用", "使用", "实践", "实际应用", "应用场景"],
    "提供": ["供给", "给予", "交付", "提供支持", "提供服务"],

    # 高频动词
    "提高": ["提升", "增强", "改善", "优化", "改进", "增进"],
    "降低": ["减少", "削减", "缩减", "下降", "减轻"],
    "增加": ["增添", "加大", "扩展", "提升"],
    "获取": ["取得", "获得", "采集", "收集", "提取"],
    "展示": ["呈现", "显示", "表现", "可视化展示"],
    "构建": ["搭建", "建立", "创建", "组建"],
    "集成": ["整合", "融合", "组合", "结合"],
    "优化": ["改进", "完善", "改良", "提升", "调优"],
    "分析": ["剖析", "研究", "探究", "考察", "解析"],
    "研究": ["探究", "分析", "考察", "调研", "深入研究"],
    "开发": ["构建", "实现", "设计", "编写", "开发实现"],

    # 高频形容词
    "重要": ["关键", "核心", "主要", "要紧", "至关重要"],
    "显著": ["明显", "突出", "可观", "引人注目"],
    "有效": ["有力", "高效", "可行", "实用"],
    "准确": ["精确", "精准", "正确", "无误"],
    "快速": ["迅速", "高效", "快捷", "高速"],
    "稳定": ["可靠", "稳固", "平稳", "健壮"],
    "灵活": ["机动", "弹性", "便捷", "自如"],
    "强大": ["强劲", "有力", "完备", "完善"],

    # 过渡词替换
    "此外": ["同时", "与之相伴", "另外"],
    "值得注意的是": ["需要关注的是", "值得关注的是", "应当说明的是"],
    "综上所述": ["总体而言", "概括来说", "总的来看"],
    "不可否认": ["必须承认", "诚然", "毋庸置疑"],

    # 学术用语
    "本文": ["本研究", "本论文", "笔者"],
    "本研究": ["本文", "本论文", "笔者"],
    "研究表明": ["研究显示", "研究发现", "调研结果揭示"],
}

# 默认术语白名单
DEFAULT_WHITELIST = {
    "检索", "向量", "知识库", "模型", "语义", "问答", "数据库", "接口",
    "语言", "量化", "架构", "框架", "组件", "模块", "服务", "缓存",
    "存储", "索引", "查询", "请求", "响应", "并发", "分布式",
    "深度学习", "机器学习", "神经网络", "自然语言处理", "文本挖掘",
    "特征工程", "训练", "推理", "预测", "分类", "聚类", "回归",
    "前端", "后端", "全栈", "微服务", "容器", "部署", "测试", "调试",
    "系统", "平台", "功能", "性能", "安全", "可靠", "可用", "扩展",
    "SpringBoot", "Spring", "PostgreSQL", "MySQL", "Redis", "MongoDB",
    "Elasticsearch", "Neo4j", "MinIO", "Docker", "Kubernetes",
    "BERT", "GPT", "LLM", "RAG", "API", "RESTful", "JSON", "SQL",
    "JWT", "RBAC", "OAuth", "HTTP", "HTTPS", "TCP", "IP",
}


class PaperReducer:
    """论文降重处理器"""

    def __init__(self, whitelist: Set[str] = None, ratio: float = 0.5):
        """__init__"""
        self.whitelist = whitelist or DEFAULT_WHITELIST
        self.ratio = ratio
        self.replacements = []
        self.replacement_stats = {}

    def replace_text(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """执行同义词替换"""
        result = text
        self.replacements = []

        # 按长度排序，优先替换长短语
        sorted_synonyms = sorted(ENHANCED_SYNONYM_DICT.items(), key=lambda x: len(x[0]), reverse=True)

        for original, synonyms_list in sorted_synonyms:
            if original in self.whitelist:
                continue

            pattern = re.compile(re.escape(original))
            matches = list(pattern.finditer(result))

            if not matches:
                continue

            num_to_replace = max(1, int(len(matches) * self.ratio))
            selected_matches = random.sample(matches, min(num_to_replace, len(matches)))

            for match in reversed(selected_matches):
                replacement = random.choice(synonyms_list)
                result = result[:match.start()] + replacement + result[match.end():]
                self.replacements.append((original, replacement))

                # 统计
                if original not in self.replacement_stats:
                    self.replacement_stats[original] = {"count": 0, "replacements": []}
                self.replacement_stats[original]["count"] += 1
                self.replacement_stats[original]["replacements"].append(replacement)

        return result, self.replacements

    def generate_review_prompt(self, original_text: str, replaced_text: str, output_path: str) -> str:
        """生成大模型审核 Prompt"""

        prompt = f'''你是一位资深的学术论文编辑，请对以下同义词替换后的论文进行审核和优化。

## 任务背景

我使用自动化工具对论文进行了同义词替换，目的是降低 AIGC 检测率。请帮我审核替换结果是否合理。

## 替换统计

- 总替换数：{len(self.replacements)} 处
- 涉及词汇：{len(self.replacement_stats)} 个不同词汇

### 替换分布（前20个高频词）

'''
        # 添加替换统计
        sorted_stats = sorted(self.replacement_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        for word, stats in sorted_stats[:20]:
            prompt += f'- "{word}" 被替换 {stats["count"]} 次，替换为：{", ".join(set(stats["replacements"][:5]))}\n'

        prompt += f'''
## 术语白名单（以下术语不应被替换）

```
{", ".join(sorted(self.whitelist))}
```

## 审核要求

### 1. 术语保护检查
- 检查白名单中的术语是否被误替换
- 如发现误替换，请标注并建议恢复

### 2. 表达自然性检查
- 替换后的表达是否符合学术规范？
- 是否存在生硬或不自然的表达？

### 3. 语义一致性检查
- 核心观点是否保持不变？
- 论述逻辑是否通顺？

## 输出格式

请输出以下内容：

### 问题报告

| 序号 | 位置/原文 | 问题类型 | 具体问题 | 修改建议 |
|------|----------|---------|---------|---------|
| 1 | ... | 术语误替换 | ... | ... |

### 统计信息

- 术语误替换数量：X 处
- 表达优化建议：X 处
- 其他问题：X 处

---

**注意**：由于论文篇幅较长，请重点关注替换频率最高的词汇是否合理。
'''

        # 保存 Prompt
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prompt)

        return prompt


def run_workflow(input_path: str, output_dir: str, ratio: float = 0.5, whitelist_path: str = None):
    """运行完整降重流程"""

    # 创建输出目录
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 加载白名单
    whitelist = set(DEFAULT_WHITELIST)
    if whitelist_path and Path(whitelist_path).exists():
        with open(whitelist_path, 'r', encoding='utf-8') as f:
            for line in f:
                term = line.strip()
                if term and not term.startswith('#'):
                    whitelist.add(term)

    # 读取原文
    with open(input_path, 'r', encoding='utf-8') as f:
        original_text = f.read()

    print(f"原始论文长度: {len(original_text)} 字符")
    print(f"替换比例: {ratio * 100}%")
    print(f"术语白名单: {len(whitelist)} 个")

    # 执行替换
    reducer = PaperReducer(whitelist=whitelist, ratio=ratio)
    replaced_text, replacements = reducer.replace_text(original_text)

    print(f"替换数量: {len(replacements)} 处")

    # 保存替换后论文
    output_paper = output_dir / f"论文降重版_{timestamp}.md"
    with open(output_paper, 'w', encoding='utf-8') as f:
        f.write(replaced_text)
    print(f"替换后论文: {output_paper}")

    # 生成审核 Prompt
    prompt_path = output_dir / f"审核Prompt_{timestamp}.md"
    reducer.generate_review_prompt(original_text, replaced_text, str(prompt_path))
    print(f"审核 Prompt: {prompt_path}")

    # 保存替换记录
    record_path = output_dir / f"替换记录_{timestamp}.json"
    record_data = {
        "timestamp": timestamp,
        "input_file": input_path,
        "output_file": str(output_paper),
        "total_replacements": len(replacements),
        "replacement_stats": {k: v["count"] for k, v in reducer.replacement_stats.items()},
        "replacements": [{"original": o, "replacement": r} for o, r in replacements[:100]]
    }
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, ensure_ascii=False, indent=2)
    print(f"替换记录: {record_path}")

    # 生成报告
    report_path = output_dir / f"降重报告_{timestamp}.md"
    report = f'''# 论文降重报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 基本信息

| 项目 | 值 |
|------|-----|
| 原始文件 | {input_path} |
| 输出文件 | {output_paper} |
| 原文字数 | {len(original_text)} |
| 替换比例 | {ratio * 100}% |
| 替换数量 | {len(replacements)} 处 |
| 涉及词汇 | {len(reducer.replacement_stats)} 个 |

## 替换分布

| 原词 | 替换次数 | 替换为 |
|------|---------|--------|
'''
    sorted_stats = sorted(reducer.replacement_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    for word, stats in sorted_stats[:20]:
        unique_replacements = list(set(stats["replacements"]))[:3]
        report += f'| {word} | {stats["count"]} | {", ".join(unique_replacements)} |\n'

    report += f'''
## 后续步骤

1. **大模型审核**: 使用生成的 Prompt 让大模型审核替换结果
   - Prompt 文件: `{prompt_path}`

2. **人工检查**: 重点检查以下内容
   - 专业术语是否被误替换
   - 表达是否通顺自然
   - 核心观点是否保持不变

3. **AIGC 检测**: 使用检测脚本验证效果
   ```bash
   python scripts/aigc_detect_technical.py --input {output_paper}
   ```

## 文件清单

| 文件 | 路径 |
|------|------|
| 降重后论文 | {output_paper} |
| 审核Prompt | {prompt_path} |
| 替换记录 | {record_path} |
| 本报告 | {report_path} |
'''

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"降重报告: {report_path}")

    return {
        "output_paper": str(output_paper),
        "prompt_path": str(prompt_path),
        "record_path": str(record_path),
        "report_path": str(report_path),
        "total_replacements": len(replacements)
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='论文降重自动化流程')
    parser.add_argument('--input', '-i', required=True, help='输入文件路径')
    parser.add_argument('--output', '-o', default='workspace/reduced/', help='输出目录')
    parser.add_argument('--ratio', '-r', type=float, default=0.5, help='替换比例（0-1）')
    parser.add_argument('--whitelist', '-w', default='scripts/term_whitelist.txt', help='术语白名单文件')

    args = parser.parse_args()

    result = run_workflow(args.input, args.output, args.ratio, args.whitelist)

    print("\n" + "=" * 50)
    print("降重流程完成！")
    print("=" * 50)
    print(f"输出文件: {result['output_paper']}")
    print(f"审核Prompt: {result['prompt_path']}")
    print(f"替换数量: {result['total_replacements']} 处")
