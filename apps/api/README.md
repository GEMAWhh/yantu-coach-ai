# API

FastAPI 本地后端骨架。当前阶段提供系统端点、统一 API 契约、SQLite 初始化、Alembic 迁移、审计事件、本地文件存储和备份恢复基础，用于验证服务、环境隔离、错误结构、事务和 CI。

## 契约端点

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/meta`
- `POST /api/v1/meta/version-check`

成功响应统一使用 `{data, meta}`；错误响应统一使用 `{error}`；每次响应都带 `X-Request-ID`。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
$env:YANTU_APP_ENV = "dev"
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

启动时会自动确保 `data/<env>/database/study.db` 初始化到 Alembic head。手动升级命令：

```powershell
$env:YANTU_APP_ENV = "dev"
alembic -c apps/api/alembic.ini upgrade head
```

测试必须设置 `YANTU_APP_ENV=test` 和临时 `YANTU_DATA_ROOT`，不得访问 `data/prod`。

## 文件与备份

当前提供服务层能力，不包含 OCR、PDF 解析或用户上传 UI：

- `app.files.storage.store_original_file`：校验文件名、扩展名、MIME 与文件头，按 SHA-256 去重后写入 `files/original/`。
- `app.files.storage.release_asset_reference`：减少引用计数。
- `app.files.storage.delete_asset_file_if_unreferenced`：只允许删除引用计数为 0 的原始文件。
- `app.files.backup.create_backup`：生成包含 `database/study.db`、`files/` 和 `manifest.json` 的 ZIP。
- `app.files.backup.verify_backup`：校验 manifest、路径安全和每个条目的 SHA-256。
- `app.files.backup.restore_backup`：恢复前自动创建 `pre-restore` 备份，恢复后重新建立运行目录。

## 测试

```powershell
python -m pytest apps/api
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app apps/api/tests
```

## localStorage 导入

阶段 2 提供原型数据一次性导入边界，旧原型 key 固定为
`postgradCoachV11`。

- `POST /api/v1/imports/localstorage/preview`：只解析和生成迁移预览，不写入数据库。
- `POST /api/v1/imports/localstorage/commit`：事务化提交导入批次，按
  `source_key + source_sha256` 幂等；重复提交返回同一个 `batch_id` 且
  `created=false`。

请求体支持三种形态：

```json
{"version": "1.1", "settings": {}, "tasks": [], "knowledge": []}
```

```json
{"postgradCoachV11": "{\"version\":\"1.1\"}"}
```

```json
{"source_key": "postgradCoachV11", "payload": {"version": "1.1"}}
```

导入服务识别原型顶层字段
`version/settings/today/tasks/knowledge/wrongs/resources/inbox/goals/records/adjustments`。
其他顶层字段和二级字段会进入 `unknown_fields`，并保留在迁移报告中。历史
`knowledge` 掌握数据缺少可验证证据，因此只标记为
`imported_unverified`，不会直接升级为稳定掌握。

## 知识节点与前置关系

阶段 3 提供正式知识图谱的最小后端边界：

- `POST /api/v1/knowledge/nodes`：创建知识节点，层级必须遵循
  `subject -> module -> chapter -> knowledge`。
- `GET /api/v1/knowledge/nodes`：按 `parent_id` 查询节点列表，默认过滤软删除。
- `GET /api/v1/knowledge/nodes/{node_id}/tree`：返回节点及子树。
- `PATCH /api/v1/knowledge/nodes/{node_id}`：更新名称、状态、重要度、描述等非结构字段。
- `DELETE /api/v1/knowledge/nodes/{node_id}`：软删除节点子树，并软删除相关边。
- `POST /api/v1/knowledge/edges`：创建关系边，支持
  `belongs_to/prerequisite/similar_to/confused_with/co_tested/transforms_to`。
- `GET /api/v1/knowledge/nodes/{node_id}/prerequisites`：返回前置是否满足和结构化阻塞原因。

当前前置满足规则先使用前置节点 `status` 判断：
`satisfied/mastered/completed` 视为满足，其他状态返回
`PREREQUISITE_NOT_MET`。后续掌握状态机落地后，该判断应切换为正式
`mastery_snapshots`。

## 掌握证据与状态机

阶段 3 提供 `mastery-v1.0.0` 的最小可执行状态机：

- `POST /api/v1/knowledge/nodes/{node_id}/evidence`：记录已确认掌握证据。
- `GET /api/v1/knowledge/nodes/{node_id}/evidence`：查询节点证据。
- `POST /api/v1/knowledge/nodes/{node_id}/evaluate`：按规则逐级推进并返回阻塞原因。
- `POST /api/v1/knowledge/nodes/{node_id}/rollback`：基于证据创建回退快照。
- `GET /api/v1/knowledge/nodes/{node_id}/history`：查询状态快照历史。

当前自动化覆盖验收矩阵 `MAST-001` 至 `MAST-009`：
阅读最多到已接触、可回忆必须有闭卷回忆、基础/变式/综合迁移必须满足样本与正确率、
稳定掌握必须多时间点达标、稳定后失败会进入掌握衰退、重复深层错因会回退并提高补救优先级。
每次状态变化都会保存 `rule_version` 与证据 ID。

## 目标、任务与结果

阶段 3 提供最小周目标到今日任务链路：

- `POST /api/v1/goals`：创建学期/季度/月/周/日目标。
- `GET /api/v1/goals/tree`：返回目标树，供规划页展示进度。
- `PATCH /api/v1/goals/{goal_id}`：更新目标，支持 `If-Match` 版本冲突保护。
- `POST /api/v1/tasks`：创建今日任务，保留 `goal_id/source_type/source_id/reason`
  以追溯来源。
- `GET /api/v1/today?date=YYYY-MM-DD`：返回当天任务和预计总用时。
- `POST /api/v1/tasks/{task_id}/start|skip|withdraw`：只改变任务状态。
- `POST /api/v1/tasks/{task_id}/results`：提交真实结果，支持
  `Idempotency-Key` 幂等；结果保存真实用时、正确率、把握度和问题描述。

任务状态与任务结果严格分离：结果提交不会自动改任务状态，任务完成也不会直接创建
`mastery_snapshots`。目标进度当前按该目标下任务结果的 `completion_ratio` 汇总。

## 今日计划引擎 V1

阶段 3 提供 `planning-v1.0.0` 的确定性计划生成边界：

- `POST /api/v1/today/generate`：根据候选任务、可用时间、精力和可选单科过滤生成今日计划。
- 默认保留 18% 机动时间，单个可拆分任务最多安排 60 分钟。
- 低精力会拒绝高认知负荷任务，单科过滤会严格拒绝其他科目。
- 前置未满足任务返回 `PREREQUISITE_NOT_MET`，连续 3 天未完成返回诊断原因。
- 每个入选任务返回 `score.breakdown` 与 `explanations`；每个拒绝任务返回 `reasons`。

## 间隔复习调度

阶段 3 提供 `review-v1.0.0` 的最小复习调度边界：

- `POST /api/v1/reviews/recalculate`：基于最新掌握快照生成或刷新复习计划。
- `GET /api/v1/reviews/due?date=YYYY-MM-DD`：返回到期复习，并给出可传入今日计划引擎的候选任务。
- `POST /api/v1/reviews/{schedule_id}/results`：提交复习结果，支持 `Idempotency-Key` 幂等。
- 独立通过会逐步延长间隔；失败会写入 `interval_test` 证据、触发掌握回退并缩短下一次间隔。
- 同一日期即时重做会保留结果，但 `independent_timepoint=false`，不计入连续独立通过。

## 个人用时校准

阶段 3 提供 `time-calibration-v1.0.0` 的最小用时校准边界：

- 任务结果首次提交后，按 `actual_minutes / estimated_minutes` 更新个人用时系数。
- 系数按 `subject_id + task_type + difficulty` 隔离，使用有界指数平滑，范围为 `0.6–1.8`。
- 零用时和异常极值会保留调整记录，但不会更新系数。
- 连续超时会提高 `overtime_streak`，达到阈值后在调整记录中给出拆分建议。
- `POST /api/v1/today/generate` 会读取最新系数，先校准候选任务预计用时再生成计划。
- `GET /api/v1/time-calibration/coefficients|adjustments` 可查看当前系数和调整依据。


## Daily evidence draft pipeline

Stage 5 adds the first governed AI-draft boundary for daily study evidence:

- `POST /api/v1/evidence/uploads`: accepts JSON/base64 files and links multiple images or PDFs to one `evidence_record`.
- `POST /api/v1/evidence/{record_id}/analyze`: runs the deterministic Fake Provider and stores an `ai_job` plus `evidence_draft`.
- `GET|PATCH /api/v1/evidence/{record_id}/draft`: reads or edits the structured draft. Schema-invalid payloads stay in `needs_correction`.
- `POST /api/v1/evidence/{record_id}/confirm`: idempotently copies a valid draft into the formal evidence record and writes `evidence.confirmed` audit once.
- `POST /api/v1/evidence/{record_id}/reject`: marks the current draft and record as rejected.

Current scope is governance only: no OCR, no multimodal parsing, and no automatic mastery or planning side effects before confirmation. Confirmation persists the formal evidence record and audit event; later issues can map confirmed evidence into mastery or wrongbook workflows.

## Wrongbook domain lifecycle

Stage 6 adds the deterministic wrongbook domain model without OCR or AI analysis:

- `POST /api/v1/wrongbook/questions`: creates a structured question and optional knowledge-node link.
- `POST /api/v1/wrongbook/records`: creates a wrong record with manual causes and an empty verification row.
- `POST /api/v1/wrongbook/{wrong_id}/assets`: links an existing asset to one of seven strict roles: `statement`, `figure`, `my_answer`, `marking`, `standard_answer`, `original_solution`, `supplement`.
- `POST /api/v1/wrongbook/{wrong_id}/attempts`: records `original_redo`, `no_hint_redo`, `variant`, `interval_test`, or `transfer_test` attempts with `Idempotency-Key` support.
- `GET /api/v1/wrongbook/planning-candidates`: returns non-resolved wrong records as `wrong_record` planning candidates.

Resolution requires all three required checks: no-hint redo, variant, and interval test. Immediate original redo can advance the record only to `pending_variant`; any failed attempt marks the record `regressed`, clears that verification flag, and increments `error_count`.

## Goal recalculation and history

Stage 4 adds deterministic five-layer planning rollup:

- `POST /api/v1/goals/{goal_id}/recalculate`: recalculates a goal subtree from child goals and task results.
- `GET /api/v1/goals/{goal_id}/history`: returns `goal.recalculated` events with previous/new progress, actual minutes, risk status, and status.
- Task result submission now recalculates the root ancestor goal so week/month/quarter/semester progress stays linked.
- Overdue unfinished goals become `risk_status=high`; overdue unfinished tasks make the direct goal `at_risk`.

History events preserve `request_id`, `source_type`, `source_id`, and a human reason so later UI can explain why a goal changed.
