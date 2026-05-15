# 图表脚本索引

本目录负责论文图片生成链路：从正文占位符抽取图片需求，维护 `images.yaml`，接收大模型生成的 `.dot/.mmd/.puml` 源文件，渲染 PNG，并回填 Markdown。ER 图由 `.thesis-config.yaml` 的 `er_modeling.graph_type` 决定，默认输出教科书 Chen 风格 DOT；`diagram_type=entity_er` 可进一步通过 `er_modeling.dot_mode=textbook-single-entity-ring` 或 `images.yaml` 单图 `dot_mode` 启用单实体字段环绕布局；用例图使用固定 PlantUML 提示词；系统架构图由用户自行生成或 GPT image 后作为用户图片补入。

## 脚本职责

| 脚本 | 职责 |
|---|---|
| `manifest_builder.py` | 从 Markdown 中的 `[image_N]` 与图片需求块生成或更新 `workspace/references/images.yaml` |
| `source_writer.py` | 根据 `images.yaml` 创建源码文件占位，并校验大模型生成的源码文件是否存在 |
| `render.py` | 按 `engine` 调用 Mermaid、Graphviz、PlantUML 渲染 PNG；PlantUML 支持本地、Kroki 与官方服务器兜底 |
| `markdown_updater.py` | 将正文中的 `[image_N]` 替换成 Markdown 图片引用 |
| `validate.py` | 校验占位符、源码、PNG、路径和状态一致性 |
| `chart_generator.py` | 旧版图表生成入口，负责从 Markdown 占位符生成图表需求和代码块 |
| `chart_renderer.py` | 旧版图表渲染入口，优先使用 `render.py` 的新链路 |
| `chart_renderer_offline.py` | 离线图表渲染辅助 |
| `chart_template_loader.py` | 读取 `templates/charts/` 图表模板 |
| `image_manifest_builder.py` | 旧版图片清单生成入口，优先使用 `manifest_builder.py` |
| `llm_chart_generator.py` | 基于大模型提示的图表源码生成辅助 |
| `demo_chart_generation.py` | 图表生成演示脚本 |

## 推荐顺序

1. `manifest_builder.py`
2. 大模型根据 `images.yaml` 写源码文件
3. `source_writer.py --validate`
4. `render.py`
5. `markdown_updater.py`
6. `validate.py`
