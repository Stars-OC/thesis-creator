# 贡献指南

感谢你考虑为论文创作 Agent 系统做出贡献！

---

## 如何贡献

### 报告问题

如果你发现了 Bug 或有功能建议，请：

1. 在 [Issues](../../issues) 中搜索是否已有相关问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤（如果是 Bug）
   - 期望行为
   - 实际行为
   - 系统环境信息

### 提交代码

1. **Fork 本仓库**

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **进行修改**
   - 遵循现有代码风格
   - 添加必要的注释
   - 更新相关文档

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   # 或
   git commit -m "fix: 修复问题描述"
   ```

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 描述你的更改
   - 关联相关 Issue

---

## 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式调整（不影响功能） |
| `refactor` | 代码重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具相关 |

**示例**：
```
feat: 添加多语言支持
fix: 修复 AIGC 检测计算错误
docs: 更新安装文档
```

---

## 代码风格

### Python

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范
- 使用 4 空格缩进
- 函数和变量使用 snake_case
- 类使用 PascalCase
- 添加类型注解

### Markdown

- 使用中文撰写文档
- 标题层级清晰
- 代码块指定语言

---

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-username/thesis-creator.git
cd thesis-creator

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/macOS

# 安装依赖
pip install -r scripts/requirements.txt

# 安装开发依赖
pip install -r scripts/requirements-dev.txt
```

---

## 测试

```bash
# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_aigc_detect.py

# 生成覆盖率报告
pytest --cov=scripts tests/
```

---

## 文档贡献

文档位于 `docs/` 目录：

- `usage_guide.md` - 使用指南
- `ROADMAP.md` - 开发路线图
- `CHANGELOG.md` - 更新日志

欢迎改进文档，包括：
- 修正错误
- 补充缺失内容
- 改进表述
- 添加示例

---

## 行为准则

- 尊重所有贡献者
- 保持建设性讨论
- 接受不同观点
- 专注于项目改进

---

## 联系方式

如有疑问，可以通过以下方式联系：
- 创建 Issue
- 发送邮件至：[项目邮箱]

---

感谢你的贡献！