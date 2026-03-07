<div align="center">

# 论文创作 Agent 系统

**面向中国本科生的毕业论文全流程写作辅助系统**

从选题到交稿，一句话搞定

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Claude](https://img.shields.io/badge/Claude-Code-Compatible.svg)](https://claude.ai/)
[![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)](docs/CHANGELOG.md)

[功能特性](#功能特性) •
[快速开始](#快速开始) •
[使用文档](docs/usage_guide.md) •
[贡献指南](CONTRIBUTING.md)

</div>

---

## 简介

论文创作 Agent 系统是一个基于 Claude Code 的毕业论文写作辅助工具。通过智能化的 8 步工作流，帮助本科生高效完成毕业论文创作，同时提供降重优化和 AIGC 检测功能。

## 功能特性

| 特性              | 说明                                 |
| :---------------- | :----------------------------------- |
| 🔄 **全流程覆盖** | 从选题到交稿的端到端 8 步工作流      |
| 📉 **降重优化**   | 句式重构、同义替换、段落重组         |
| 🤖 **AIGC 降低**  | 模拟人类写作特征，降低 AI 检测风险   |
| 🔍 **本地检测**   | 轻量级 AIGC 检测工具，快速预估检测率 |
| 📝 **格式检查**   | 自动检查论文结构规范性               |
| 💬 **智能讨论**   | 三轮深入讨论充分理解论文需求         |
| 📄 **文档导出**   | 支持 Word/PDF 格式一键导出           |

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                      论文创作工作流                           │
├─────────────────────────────────────────────────────────────┤
│  Step 0: 初始化工作区                                        │
│      ↓                                                       │
│  Step 1: 环境准备  →  Step 1.5: 背景信息讨论                  │
│      ↓                                                       │
│  Step 2: 读取参考资料  →  Step 3: 生成论文大纲                │
│      ↓                                                       │
│  Step 4: 分章节撰写  →  Step 5: 降重处理                      │
│      ↓                                                       │
│  Step 6: AIGC 人性化  →  Step 7: 自检输出                     │
│      ↓                                                       │
│  Step 8: 文档导出（Word/PDF）                                 │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 前置要求

- Python 3.9+
- Claude Code 已安装
- Windows 10/11

### 安装

#### 方式一：Claude Skill 安装

```powershell
# 自然语言安装
帮我安装下 skill，项目地址是：https://github.com/Stars-OC/thesis-creator.git

# 从 GitHub 安装
git clone https://github.com/Stars-OC/thesis-creator.git
将文件放入./claude-skills/skills/ 下

# 市场安装 (待进行)

```

#### 方式二：OpenSkills 安装

使用 OpenSkills 包管理器安装：

```powershell
# 安装 OpenSkills CLI（如未安装）
pip install openskills

# 或从 GitHub 安装
openskills install https://github.com/Stars-OC/thesis-creator.git
openskills sync
```

#### 方式三：完整安装（推荐）

包含 Python 工具和依赖：

```powershell
# 克隆仓库
git clone https://github.com/Stars-OC/thesis-creator.git
cd thesis-creator

# 安装 Python 依赖
.\scripts\install.ps1
```

<details>
<summary>手动安装 Python 依赖</summary>

```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r scripts\requirements.txt
```

</details>

### 使用

**1. 准备参考资料**

```
references/
├── templates/         # 学校论文格式模板
├── examples/          # 优秀范文
├── guidelines/        # 写作规范
├── prompt/
│   └── background.md  # 论文背景信息（必填）
└── reference/
    ├── code/          # 参考代码
    └── doc/           # 参考文献
```

**2. 触发 Skill**

在 Claude Code 中输入：

```
帮我写论文，主题是《大数据在精准营销中的应用研究》
```

系统将自动执行完整工作流。

### 单功能模式

| 触发语                   | 功能       |
| :----------------------- | :--------- |
| `帮我降重这段文字：…`    | 降重优化   |
| `降低这段的 AIGC 率：…`  | 人性化改写 |
| `检测这段文字的 AIGC 率` | AIGC 检测  |
| `帮我生成论文大纲`       | 大纲生成   |
| `导出 Word` / `导出 PDF` | 格式转换   |

## 目录结构

```
thesis-creator/
├── SKILL.md                 # 主 Skill 定义
├── README.md                # 项目说明
├── LICENSE                  # MIT 许可证
├── CONTRIBUTING.md          # 贡献指南
├── docs/                    # 文档
│   ├── usage_guide.md       #   使用指南
│   ├── ROADMAP.md           #   开发路线图
│   └── CHANGELOG.md         #   更新日志
├── prompts/                 # 提示词模板
├── scripts/                 # Python 工具
│   ├── aigc_detect.py       #   AIGC 检测
│   ├── synonym_replace.py   #   同义词替换
│   ├── text_analysis.py     #   文本分析
│   ├── format_checker.py    #   格式检查
│   └── document_exporter.py #   文档导出
├── references/              # 参考资料
└── workspace/               # 论文产出
    ├── outline.md           #   论文大纲
    ├── drafts/              #   初稿
    ├── reduced/             #   降重版
    ├── history/             #   历史版本
    └── final/               #   终稿
```

## 目标指标

| 指标         | 目标值            |
| :----------- | :---------------- |
| 论文产出速度 | 3000 字 / 30 分钟 |
| 查重率       | ≤ 30%             |
| AIGC 检测率  | ≤ 15%             |
| 排版合规率   | 符合学校模板      |

## 文档

| 文档                            | 说明                     |
| :------------------------------ | :----------------------- |
| [使用指南](docs/usage_guide.md) | 详细安装、配置和使用说明 |
| [开发路线图](docs/ROADMAP.md)   | 项目功能规划             |
| [更新日志](docs/CHANGELOG.md)   | 版本更新记录             |
| [贡献指南](CONTRIBUTING.md)     | 如何参与项目开发         |

## 注意事项

> [!WARNING]
> 本地 AIGC 检测为近似估计，正式提交前建议使用知网/维普进行官方检测。

- **版本控制**：每次改写前自动备份到 `workspace/history/`
- **术语保护**：专业术语不会被降重工具打乱
- **断点续传**：支持任意步骤中断后恢复

### 测试指南

目前 只用于论文 **初稿** 的创建中，功能尚未完善 需要自己调整 **排版**！

## 贡献

欢迎贡献代码、报告问题或提出建议！

请阅读 [贡献指南](CONTRIBUTING.md) 了解如何参与项目。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 致谢

- [Claude Code](https://claude.ai/) - AI 编程助手
- [Anthropic](https://www.anthropic.com/) - Claude 模型提供方

---

<div align="center">

**[⬆ 回到顶部](#论文创作-agent-系统)**

如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！

</div>
