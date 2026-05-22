# 学科模板包编写指南

## 模板包是什么

模板包是 thesis-creator 的学科能力模块，作用类似 skill。每个模板包通过 `manifest.yaml` 暴露能力，通过 YAML 文件和提示词定义学科差异。

## 最小目录

```text
packages/disciplines/your_discipline/
├── manifest.yaml
├── structure.yaml
├── writing_rules.yaml
├── checklist.yaml
└── prompts/
    └── writer.md
```

## 新增学科步骤

1. 复制 `packages/disciplines/cs_se/` 或 `packages/base/`。
2. 修改 `manifest.yaml` 的 `id`、`name`、`supports` 和 `capabilities`。
3. 修改 `structure.yaml`，只描述章节结构。
4. 修改 `writing_rules.yaml`，只描述写作和产物要求。
5. 修改 `checklist.yaml`，只描述质量门禁。
6. 修改 `prompts/writer.md`，补充学科语境。
7. 运行模板包测试。

## 合并优先级

`用户覆盖 > 学科模板 > 模式模板 > 基础模板 > 系统默认`

## 注意事项

- 不要在模板包里写核心流程逻辑。
- 非 CS/SE 学科不要继承代码、截图、数据库表等要求。
- 如果某个学科确实需要特殊图表，优先补 `diagrams.yaml`，不要改图表主流程。