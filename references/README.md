# 参考资料（References）

本目录用于存放论文写作所需的各类参考资料。

---

## 📁 目录结构

```
references/
├── templates/          # 学校格式模板
├── examples/           # 优秀范文参考
├── guidelines/         # 写作规范文件
├── prompt/             # 论文背景信息（必需填写）
└── reference/          # 参考资料目录
    ├── code/           # 代码参考
    └── doc/            # 文档参考
```

---

## 📋 各目录用途

| 目录 | 用途 | 必需程度 |
|------|------|----------|
| `prompt/` | 论文背景信息 | ⭐⭐⭐ **必需** |
| `templates/` | 学校论文格式模板 | ⭐⭐⭐ 推荐 |
| `guidelines/` | 学校写作规范 | ⭐⭐⭐ 推荐 |
| `examples/` | 往届优秀范文 | ⭐⭐ 可选 |
| `reference/doc/` | 相关论文、报告 | ⭐⭐ 推荐 |
| `reference/code/` | 研究代码 | ⭐ 可选 |

---

## 🚀 快速开始

### 第一步：填写背景信息（必需）

```bash
cd references/prompt/
cp template.md background.md
# 编辑 background.md，填写您的论文信息
```

### 第二步：放入学校模板和规范

- 学校模板 → `templates/` 目录
- 写作规范 → `guidelines/` 目录

### 第三步：添加参考资料（可选）

- 代码参考 → `reference/code/`
- 文档参考 → `reference/doc/`

### 第四步：启动 Skill

```
帮我写论文，我已经填写了背景信息
```

---

## 📖 详细说明

| 目录 | 说明文件 |
|------|----------|
| `templates/` | [README.md](./templates/README.md) |
| `examples/` | [README.md](./examples/README.md) |
| `guidelines/` | [README.md](./guidelines/README.md) |
| `prompt/` | [README.md](./prompt/README.md) |
| `reference/` | [README.md](./reference/README.md) |

---

## ⚠️ 防呆机制

AI 会**自动排除**以下文件，不会读取：

- 所有 `README.md` 文件
- `template.md` 空白模板
- 文件名包含「模板」「template」的文件

**只有您实际创建或修改的文件才会被识别。**