# 研途教练｜AI 研发执行包 V1.0

本执行包用于将“考研智能学习系统”交给 AI 主导研发，同时通过规范、测试、独立审查、数据保护和发布门禁，把失败概率压到最低。

它不是产品代码本身，而是**研发控制系统**。所有编码智能体、测试智能体、审查智能体和发布智能体都必须在本执行包规定的边界内工作。

## 1. 使用方式

1. 新建私有 GitHub 仓库。
2. 将本目录全部提交为仓库首个版本。
3. 在 GitHub 中启用 `main` 和 `develop` 分支保护；若当前 GitHub 套餐不支持私有仓库强制分支保护，则必须记录为已知限制，并用 PR、CI 和人工确认流程替代。
4. 根据 `initial_issues/` 依次创建首批 Issue。
5. 把 `prompts/` 中对应角色提示词交给不同 AI 智能体。
6. 每项任务必须执行：Issue → 独立分支 → PR → CI → 测试 AI → 审查 AI → 合并。
7. 阶段版本先进入预发布环境，确认后再发布正式版本。

## 2. 单一事实源

优先级从高到低：

1. `docs/PRODUCT_SPEC.md`：产品目标和业务边界。
2. `docs/ACCEPTANCE_MATRIX.md`：可验证验收标准。
3. `docs/MASTERY_RULES.md`：掌握状态机与学习科学规则。
4. `docs/DATA_MODEL.md` 与 `docs/API_CONTRACT.md`：数据及接口契约。
5. `docs/ARCHITECTURE.md`：模块边界与技术约束。
6. 已批准 ADR：架构决策记录。
7. Issue 中的局部任务合同。

发生冲突时不得自行猜测，必须停止实现并提出“决策请求”。

## 3. 目录说明

```text
.github/            GitHub Issue、PR 和 CI 门禁
config/             可版本化业务规则、质量门槛和 AI JSON Schema
docs/               产品、架构、数据、安全、测试和发布规范
initial_issues/     第一批可直接创建的开发任务
prompts/            总控、架构、实现、测试、审查和发布 AI 提示词
references/         当前 HTML 原型，仅作 UI 与交互参考
scripts/            研发治理检查脚本
templates/          任务、迁移、评测和发布报告模板
```

## 4. AI 可自主完成的工作

- 需求转写、技术方案、编码、重构和文档；
- 数据库迁移、测试、截图、构建和发布准备；
- 问题定位、修复和回归测试；
- 根据验收矩阵创建新测试；
- 形成预发布包与发布报告。

## 5. 必须由产品所有者确认的事项

- 学习规则与掌握阈值的实质性变化；
- 正式数据删除、恢复和不可逆迁移；
- 目标院校、考试科目和考试日期变化；
- 重大界面改版；
- AI 识别结果或大幅计划调整写入正式数据；
- 正式版本发布。

## 6. 首个可靠版本的边界

首个正式版本只要求完成：

```text
周目标 → 今日任务 → 训练记录 → 真实结果 → 掌握判定
→ 状态回退 → 间隔复习 → 明日候选 → 备份恢复
```

必须在**不调用 AI 模型**的情况下完整运行。图片分析、错题 AI、RAG 和联网校准在核心闭环稳定后接入。

## 7. 快速检查

```bash
python scripts/validate_governance.py
python scripts/check_forbidden_patterns.py .
```

CI 会自动执行同类检查。任何失败均不得绕过。

## 8. 本地启动命令

### 后端

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
$env:YANTU_APP_ENV = "dev"
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 前端

```powershell
cd apps/web
npm ci
npm run dev
```

默认地址：`http://127.0.0.1:5173`。

### 全量检查

```powershell
python scripts/validate_governance.py
python scripts/check_forbidden_patterns.py .
python -m pytest apps/api
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app apps/api/tests
cd apps/web
npm run typecheck
npm run lint
npm run test:unit
npm run build
```

## 9. 当前仓库门禁限制

当前仓库位于个人账号的私有仓库中，未升级 GitHub Pro/Team。GitHub Rulesets 和私有仓库分支保护不会被强制执行。

在升级前，本项目采用以下替代约束：

1. 所有开发任务仍按 Issue → 独立分支 → PR → CI → 审查 → 合并执行。
2. 不把 Ruleset 或 Protected Branch 标记为“已强制生效”。
3. `main` 和 `develop` 的直接推送属于流程违规，即使 GitHub 当前无法技术性阻止。
4. 每次合并前必须确认 `backend`、`frontend`、`e2e`、`validate` 检查通过。
