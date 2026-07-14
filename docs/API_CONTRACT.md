# API 契约 V1

基路径：`/api/v1`。使用 JSON；上传接口使用 multipart/form-data。所有时间使用 ISO 8601，数据库保存 UTC，前端按用户时区显示。

## 1. 通用规则

- 成功响应统一使用 envelope：

```json
{
  "data": {},
  "meta": {"request_id": "..."}
}
```

- 错误响应统一使用 envelope：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {"errors": []},
    "request_id": "..."
  }
}
```

- 每次请求必须返回 `X-Request-ID` 响应头，响应体中的 `request_id` 必须与其一致；
- 创建、确认、提交结果等写操作接受 `Idempotency-Key`；
- 资源版本通过 `version` 或 `If-Match` 防止覆盖；
- 分页：`page`, `page_size`，返回 `items`, `total`；
- 删除默认软删除；永久删除需单独端点和确认参数；
- API 不返回本地绝对文件路径。

## 2. 今日与任务

```http
GET    /today?date=YYYY-MM-DD
POST   /today/generate
POST   /tasks
GET    /tasks/{task_id}
PATCH  /tasks/{task_id}
POST   /tasks/{task_id}/start
POST   /tasks/{task_id}/results
POST   /tasks/{task_id}/skip
POST   /tasks/{task_id}/withdraw
```

`POST /today/generate` 使用 `planning-v1.0.0` 规则从候选任务生成今日计划。请求体包含：
`available_minutes`、`energy`、可选 `subject_filter` 和 `candidates`。候选任务必须携带
`subject_id`、`estimated_minutes`、`cognitive_load`、`source_type/source_id` 以及各评分分项。
响应必须返回 `schedulable_minutes`、`planned_minutes`、`buffer_minutes`、入选任务的
`score.breakdown/explanations`，以及未纳入候选的 `reasons`。

`POST /tasks/{task_id}/results` 必须支持 `Idempotency-Key`，重复提交同一 key
返回同一结果；任务状态与任务结果分离，结果不得直接推动掌握阶段。

## 3. 规划

```http
GET    /goals/tree
POST   /goals
GET    /goals/{goal_id}
PATCH  /goals/{goal_id}
DELETE /goals/{goal_id}
POST   /goals/{goal_id}/recalculate
GET    /goals/{goal_id}/history
```

## 4. 知识与掌握

```http
GET  /knowledge/nodes
GET  /knowledge/nodes/{node_id}
POST /knowledge/nodes
PATCH /knowledge/nodes/{node_id}
DELETE /knowledge/nodes/{node_id}
GET  /knowledge/nodes/{node_id}/tree
GET  /knowledge/nodes/{node_id}/prerequisites
POST /knowledge/edges
GET  /knowledge/nodes/{node_id}/evidence
POST /knowledge/nodes/{node_id}/evidence
POST /knowledge/nodes/{node_id}/evaluate
POST /knowledge/nodes/{node_id}/rollback
GET  /knowledge/nodes/{node_id}/history
```

状态变化响应必须包含：`previous_stage, new_stage, rule_version, evidence_ids, reason, next_action`。

## 5. 复习

```http
GET  /reviews/due?date=YYYY-MM-DD
POST /reviews/{review_id}/results
POST /reviews/recalculate
```

`GET /reviews/due` 返回到期复习计划和可直接传入今日计划引擎的
`review_schedule` 候选任务。`POST /reviews/{review_id}/results` 必须支持
`Idempotency-Key`；独立通过会延长间隔，失败会写入 `interval_test` 证据并触发掌握回退，
同一日期的即时重做只记录结果，不计入独立时间点。

## 6. 每日证据

```http
POST /evidence/uploads
POST /evidence/{record_id}/analyze
GET  /evidence/{record_id}/draft
PATCH /evidence/{record_id}/draft
POST /evidence/{record_id}/confirm
POST /evidence/{record_id}/reject
```

确认必须在一个事务中创建正式记录、掌握证据、计划调整候选和审计事件。

## 7. 错题

```http
POST /wrongbook/drafts
POST /wrongbook/{wrong_id}/assets
POST /wrongbook/{wrong_id}/analyze
GET  /wrongbook/{wrong_id}/draft
PATCH /wrongbook/{wrong_id}/draft
POST /wrongbook/{wrong_id}/confirm
POST /wrongbook/{wrong_id}/attempts
POST /wrongbook/{wrong_id}/variant-results
POST /wrongbook/{wrong_id}/interval-results
GET  /wrongbook/{wrong_id}/history
```

## 8. 资料与文件

```http
POST   /assets
GET    /assets/{asset_id}/metadata
GET    /assets/{asset_id}/content
DELETE /assets/{asset_id}
POST   /assets/{asset_id}/restore
POST   /resources
GET    /resources
```

## 9. 图谱与统计

```http
GET /graph/full
GET /graph/weak
GET /analytics/overview
GET /analytics/time
GET /analytics/errors
GET /analytics/mastery
GET /analytics/goal-risk
```

图表响应必须包含可点击对象 ID，不只返回聚合数值。

## 10. 设置与数据管理

```http
GET  /settings/profile
PATCH /settings/profile
GET  /settings/rules
POST /backups
GET  /backups
POST /backups/{backup_id}/verify
POST /backups/{backup_id}/restore
POST /imports/localstorage
GET  /exports/full
```

## 11. 系统与契约端点

```http
GET  /health
GET  /api/v1/health
GET  /api/v1/meta
POST /api/v1/meta/version-check
```

`POST /api/v1/meta/version-check` 使用 `If-Match: contract-v1` 验证版本冲突响应结构。

## 12. 错误代码示例

- `VALIDATION_ERROR`
- `NOT_FOUND`
- `VERSION_CONFLICT`
- `INTERNAL_SERVER_ERROR`
- `PREREQUISITE_NOT_MET`
- `MASTERY_TRANSITION_BLOCKED`
- `AI_DRAFT_NOT_CONFIRMED`
- `AI_OUTPUT_SCHEMA_INVALID`
- `ASSET_TYPE_INVALID`
- `BACKUP_VERIFICATION_FAILED`
- `MIGRATION_FAILED_ROLLED_BACK`
