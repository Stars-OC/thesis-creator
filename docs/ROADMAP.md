# 后续改进计划 (ROADMAP)

> 论文创作 Agent 系统功能路线图

---

## 当前版本 v1.3.0（main）

**最近更新**：2026-05-22

**核心功能**：
- 10 步全流程论文创作工作流（含图片生成与文档导出）
- 本地 AIGC 检测（轻量版 + 完整版）
- 降重优化与同义词替换 + 场景化重写
- Word/PDF 文档导出（含图片自动嵌入与三线表）
- 三轮背景信息讨论
- 三源学术搜索 + DOI 验证 + 虚构文献自动替换
- 默认学科：CS / SE（计算机与软件工程）

---

## v2.0.0-beta（开发中，分支 `multi-discipline-beta`）

> [!IMPORTANT]
> 该版本是**未来正式版的预演**，已在 `multi-discipline-beta` 分支可用，main 暂未合入。
> 预计稳定后以 v2.0.0 合并回 main。

**分支地址**：[`multi-discipline-beta`](https://github.com/Stars-OC/thesis-creator/tree/multi-discipline-beta)
**已完成时间**：2026-05-22
**端到端验证**：教育学（education）测试用例已跑通 Step 0→9，AIGC 检测率 6.1%

### 三大主线

#### ① 多学科模板包系统（核心架构升级）

将原本硬编码于流程脚本中的「CS/SE 7 章结构 + 代码/截图/数据库表要求」抽离为
**通用核心 + 学科技能包**的契约式设计，新学科主要通过模板包接入，不改核心代码。

- 新增 `packages/` 目录：
  - `packages/base/` 通用基础模板（4 章基线）
  - `packages/disciplines/` 9 个学科包：
    - `cs_se`（计算机/软件工程，7 章）
    - `business_management`（经管，5 章）
    - `law`（法学，6 章）
    - `education`（教育学，6 章）
    - `humanities`（人文，5 章）
    - `medical_nursing`（医护，6 章 IMRaD 扩展）
    - `engineering`（工科非软件，7 章）
    - `science`（理科，6 章 IMRaD）
    - `art_design`（艺术与设计，6 章含作品）
  - `packages/modes/` 模式包：`undergraduate.yaml` / `master.yaml`
- 新增 3 个核心脚本：
  - `scripts/core/package_validator.py` — 校验学科 manifest 与必填文件
  - `scripts/core/package_loader.py` — 继承式合并基础与学科模板
  - `scripts/core/config_resolver.py` — 解析「用户覆盖 > 学科 > 模式 > 基础 > 系统默认」
- 工作流改造：
  - `workflows/step_0_init.md` 增加 10 学科速查表与选择决策树
  - `workflows/step_3_outline.md` 从 CS/SE 硬编码改为配置驱动

#### ② 状态机产物对账（运行稳定性）

解决「step 状态显示 completed，但实际产物缺失」的失同步问题。

- `scripts/core/status_manager.py` 升级至 v2.1：
  - `STEP_ARTIFACT_REQUIREMENTS` 声明每步骤必要产物
  - `verify_step_artifacts()` 检查实际文件
  - `reconcile_with_artifacts()` 自动降级 completed → in_progress
- `scripts/core/lifecycle.py` 新增 `--reconcile` CLI 与硬门控：
  - 产物未齐全不可标记 complete
  - 工作流入口前自动 reconcile，防止误进下一步

#### ③ 图片管线增强

- `scripts/charts/manifest_builder.py` 与 `markdown_updater.py`
  支持 HTML 注释 `<!-- image-requirement -->` 与围栏块 `::: image-requirement :::` 双格式
- `scripts/charts/engines/graphviz.py` 修复 Windows 含空格路径，
  改用子进程列表参数避免 shell 注入与解析错误
- 新增 `scripts/charts/user_placeholder.py` 生成中文白底占位 PNG
  （供 `source=user` 类图片在导出阶段不留空）

### 辅助变更

- `workflows/step_4_writing.md` 新增「写作即引用」分章引用配额表
- `workflows/step_7_merge_detect.md` 新增 5 项硬门控自检
- `SKILL.md` 新增 4 条防错条目（状态失同步 / 跳过 7→8 校验 /
  图片字段漏写 / image-requirement 格式错配）
- 新增 `docs/template-package-authoring.md`（社区可参考此文档贡献新学科）
- 新增 5 个测试文件覆盖包加载、校验、配置解析与示例包

### 仍待完成（合入 main 前）

- [ ] 在 humanities / law / medical_nursing 三个学科上跑通端到端验证
- [ ] `art_design` 的作品图片管线（≥5 张/核心章节）压力测试
- [ ] `master` 模式下的章节扩展（硕士比本科多 2~3 章）行为校准
- [ ] 模板包社区贡献指南（`CONTRIBUTING-packages.md`）
- [ ] 更新 `.openskills.json` 版本号到 v2.0.0
- [ ] 用户在 `.thesis-config.yaml` 中切换 discipline 后，
      已有 outline.md 的兼容/迁移策略

---

## v2.1.0 - 体验优化（计划中）

**预计时间**：v2.0 合入 main 后 1~2 个月

### 功能改进

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 进度可视化 | ⭐⭐⭐ | 实时显示工作流进度和预计时间 |
| 断点续传增强 | ⭐⭐ | 支持任意步骤中断后精确恢复（与 reconcile 联动） |
| 批量处理 | ⭐⭐ | 支持多论文并行处理 |
| 学科自动推荐 | ⭐⭐ | 根据用户输入的题目自动建议 discipline 参数 |

### 性能优化

- [ ] 优化 AIGC 检测算法，提升准确率至 75%+
- [ ] 减少 GPT-2 模型加载时间
- [ ] 增量式文档处理，减少内存占用

---

## v2.2.0 - 智能增强（计划中）

**预计时间**：2026-Q4

### AI 能力升级

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 风格学习 | ⭐⭐⭐ | 从范文学习个性化写作风格 |
| 智能引用 | ⭐⭐ | 自动检索并引用相关文献 |
| 图表生成 | ⭐⭐ | 自动生成数据可视化图表（与 charts 引擎打通） |
| 跨学科引用 | ⭐⭐ | 支持「主学科 + 辅学科」混合写作（如教育技术 = 教育 + CS） |

### 检测能力

- [ ] 添加维普检测支持
- [ ] 优化 AIGC 检测准确率至 85%+

---

## 长期愿景

### 学科生态

- **目标 20+ 学科覆盖**：覆盖中国本科专业目录约 90% 的一级学科
- **社区贡献模板包**：开放 `packages/disciplines/` 由社区贡献，核心团队评审合入
- **院校定制包**：支持以学校为单位的模板继承（如「华东师大-教育学」覆盖通用 education 包）

### 学术诚信

我们始终坚持：
1. 提供高质量的写作辅助，而非替代人工创作
2. 帮助学生理解学术规范，培养正确的研究方法
3. 降低 AI 检测风险的同时，保持学术诚信底线

### 开源社区

计划建立：
1. 完善的开发者文档
2. 模板包社区贡献指南
3. 定期的社区活动
4. 技术博客和教程

---

## 贡献指南

欢迎社区贡献！请查看以下方式：

1. **报告问题**：在 Issues 中提交 Bug 报告
2. **功能建议**：提交 Feature Request
3. **代码贡献**：提交 Pull Request
4. **文档改进**：帮助完善文档
5. **学科模板包**：参考 `docs/template-package-authoring.md`（在 beta 分支）贡献新学科包

---

## 版本命名规范

- **主版本号 (Major)**：架构重大变更或不兼容更新（例：v1 → v2 引入模板包系统）
- **次版本号 (Minor)**：新功能添加，向后兼容
- **修订号 (Patch)**：Bug 修复和小改进

---

## 分支策略

| 分支 | 角色 | 状态 |
|------|------|------|
| `main` | 稳定版（v1.2.x） | 生产可用 |
| `multi-discipline-beta` | 多学科 v2.0 预演 | 开发中，已通过 education 端到端验证 |
| `er-textbook-single-entity-ring` | ER 图实验分支 | 试验性 |
| `reference-scripts-modularization` | 引用脚本模块化 | 试验性 |
| `thesis-creator-b-plan` | 替代方案探索 | 试验性 |

---

> 最后更新：2026-05-22
