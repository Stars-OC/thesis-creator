# 图表脚本索引

本目录负责论文图片生成链路：从正文占位符抽取图片需求，维护 `images.yaml`，接收大模型生成的 `.dot/.mmd/.puml` 源文件，渲染 PNG，并回填 Markdown。ER 图由 `.thesis-config.yaml` 的 `er_modeling.graph_type` 决定，默认输出教科书 Chen 风格 DOT；用例图使用固定 PlantUML 提示词；系统架构图由用户自行生成或 GPT image 后作为用户图片补入。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `manifest_builder.py` | 从 Markdown 中的 `[image_N]` 与图片需求块生成或更新 `workspace/references/images.yaml` |
| `source_writer.py` | 根据 `images.yaml` 创建源码文件占位，并校验大模型生成的源码文件是否存在 |
| `render.py` | 按 `engine` 调用 Mermaid、Graphviz、PlantUML 渲染 PNG；PlantUML 支持本地、Kroki 与官方服务器兜底 |
| `markdown_updater.py` | 将正文中的 `[image_N]` 替换成 Markdown 图片引用 |
| `validate.py` | 校验占位符、源码、PNG、路径和状态一致性 |

## 推荐顺序

1. `manifest_builder.py`
2. 大模型根据 `images.yaml` 写源码文件
3. `source_writer.py --validate`
4. `render.py`
5. `markdown_updater.py`
6. `validate.py`
