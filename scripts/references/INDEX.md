# 参考文献脚本索引

本目录负责论文参考文献链路：多源搜索、DOI/元数据验证、合并去重、文献池维护、GB/T 7714 格式检查与输出。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `reference_engine.py` | 多源学术搜索引擎，整合 Semantic Scholar、CrossRef、OpenAlex，并处理 DOI 验证 |
| `reference_searcher.py` | 旧搜索接口与多源搜索适配层，支持关键词、DOI 与语言过滤 |
| `reference_merger.py` | 合并多个 YAML 文献文件，按 DOI 和标题相似度去重，并输出 `verified_references.yaml` |
| `reference_validator.py` | 校验参考文献格式、可疑占位符、DOI 可达性和在线元数据 |
| `verified_reference_pool.py` | 管理 `workspace/references/verified_references.yaml`，推荐、占用和导出文献 |

## 推荐顺序

1. `reference_engine.py` 或 `reference_searcher.py` 搜索候选文献
2. `reference_merger.py` 合并去重并生成文献池
3. `reference_validator.py` 检查格式和链接风险
4. `verified_reference_pool.py` 在写作阶段推荐和占用文献

## 推荐命令

```bash
python scripts/references/reference_engine.py --query "RAG 知识库" --source all --language zh --limit 15
python scripts/references/reference_merger.py -i workspace/references/ --top 25 -o workspace/references/verified_references.yaml
python scripts/references/reference_validator.py workspace/final/论文终稿.md --output workspace/reports/
python scripts/references/verified_reference_pool.py --recommend --keywords "RAG 知识库 检索"
```

## 关键约束

- 文献池路径统一为 `workspace/references/verified_references.yaml`
- 同一 `ref_id` 整篇论文仅允许引用一次
- 无 DOI 不等于假文献，但必须记录验证状态
- 中文文献不足时提示人工补充真实来源，禁止伪造
