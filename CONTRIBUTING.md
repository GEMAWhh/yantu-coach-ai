# 贡献与 AI 协作流程

## 分支

- `main`：正式稳定版本，只接受发布 PR。
- `develop`：集成分支。
- `feature/<issue>-<slug>`：功能。
- `fix/<issue>-<slug>`：缺陷修复。
- `release/<version>`：发布候选。

## 标准流程

1. 从 `develop` 创建分支。
2. 根据 Issue 编写或补充失败测试。
3. 实现最小变更。
4. 运行全部相关检查。
5. 创建 PR 到 `develop`。
6. 测试 AI 和审查 AI 独立审查。
7. CI 全绿且所有严重意见解决后合并。
8. 阶段完成后从 `develop` 创建 `release/*`，预发布验收后合并到 `main`。

## 提交信息

```text
feat(mastery): add recall evidence transition
fix(planning): enforce single-subject filter
test(wrongbook): cover interval verification rollback
docs(api): clarify idempotency behavior
```

## Definition of Done

- 验收矩阵中的相关条目通过；
- 没有新增高危安全问题；
- 数据迁移可回滚；
- 新功能可从 UI 或 API 完整使用；
- 空状态、错误状态和移动端可用；
- 文档与实现一致；
- 有明确回滚路径。
