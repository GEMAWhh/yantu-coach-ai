# Web

Vue 3 + TypeScript 前端骨架。当前阶段实现五页应用壳、桌面侧栏、移动底部导航、集中设计 token、模拟学习数据和 typed API client。

## 页面

- `/today`：今日计划、执行记录、学习证据、AI 复盘提示。
- `/planning`：学期、季度、月、周、日五层规划展示。
- `/learning`：资料、学习单元、题库、错题、复习卡片和知识图谱入口。
- `/progress`：计划偏差、掌握阶段、正确率、错因和风险。
- `/settings`：考试信息、规则、AI 配置和数据管理。

## 本地运行

```powershell
cd apps/web
npm ci
npm run dev
```

默认地址：http://127.0.0.1:5173

## 检查

```powershell
npm run typecheck
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

`npm run test:e2e` 会为五个一级页面分别生成桌面和 360px 手机截图到 Playwright `test-results` 目录，并检查移动端无横向溢出。
