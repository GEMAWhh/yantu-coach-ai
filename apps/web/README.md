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

## 联网演示构建

静态托管或没有在线后端时，使用 demo API 构建。该模式只在 `--mode demo` 下启用，普通本地开发仍请求真实 API。

```powershell
cd apps/web
npm run build:demo
```

构建产物会使用内存样例数据展示今日任务、五层规划、资料队列、复习、证据草稿、错题草稿、进度分析和设置规则。

## 检查

```powershell
npm run typecheck
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

`npm run test:e2e` 会为五个一级页面分别生成桌面和 360px 手机截图到 Playwright `test-results` 目录，并检查移动端无横向溢出。
