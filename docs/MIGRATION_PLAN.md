# 当前 HTML 原型迁移计划

## 1. 原型定位

`references/考研智能学习系统_V1.1_本地版.html` 作为：

- 视觉基准；
- 页面和文案清单；
- 交互流程参考；
- localStorage 数据结构来源。

不得继续把正式业务逻辑堆入单文件。

## 2. 前端迁移

1. 冻结原型并生成桌面/移动截图；
2. 建立 Vue 3 + TypeScript + Vite；
3. 拆分 AppLayout、Sidebar、Topbar、BottomNav；
4. 建立 Today、Planning、Learning、Progress、Settings 页面；
5. 建立模块化组件和模拟 API；
6. 用 Playwright 对比主要流程；
7. API 稳定后替换模拟层。

## 3. localStorage 导入

旧键：`postgradCoachV11`（实现前必须从原型确认）。

流程：

```text
读取 JSON → Schema 校验 → 生成迁移预览
→ 转换为 profile/goals/tasks/records/resources/inbox
→ 标记无法验证的掌握状态 → 用户确认
→ 事务写入 → 迁移报告 → 保留旧数据副本
```

历史掌握数据若缺少证据，只能标记为 `imported_unverified`，不能直接成为稳定掌握。

## 4. 验收

- 旧原型数据不被修改；
- 导入可重复预览但正式提交幂等；
- 未识别字段进入报告；
- 导入失败不产生部分正式数据；
- 用户可选择放弃导入并从空库开始。
