# 测试策略与质量门禁

## 1. 测试层次

1. 纯领域单元测试：掌握、计划、复习、错题规则。
2. 应用服务测试：事务、幂等、审计和权限。
3. API 集成测试：FastAPI + 测试数据库 + 临时文件目录。
4. 前端组件测试：状态、表单和错误提示。
5. Playwright E2E：真实用户流程和移动端。
6. 迁移、备份和恢复测试。
7. AI 黄金测试集与 Schema 测试。
8. 视觉回归与可访问性检查。

## 2. 测试独立性

- 每次测试使用新建临时数据库；
- 不依赖执行顺序；
- 不访问正式目录；
- AI、时间、随机数和网络通过可替换接口注入；
- 固定时钟验证到期复习和日期边界。

## 3. 必测业务不变量

- 阅读不进入可回忆；
- 任务完成不等于掌握；
- 原题重做不等于错题解决；
- 状态推进需要证据且不能非法跳级；
- 稳定掌握允许回退；
- 单科过滤严格生效；
- 前置缺失阻止后续；
- 计划保留机动；
- AI 未确认不写正式库；
- 备份恢复后引用和哈希一致。

当前自动化覆盖今日计划验收矩阵 `PLAN-004` 至 `PLAN-008`：
计划不排满全天并保留配置机动、单科过滤严格生效、低精力不安排高认知负荷任务、
反复超时任务按最大单任务时长拆分、连续未完成任务进入诊断而不是机械复制。

当前自动化覆盖复习调度核心验收：阶段基础间隔、失败回退和短间隔、独立通过延长、
同日重做不计独立时间点、幂等提交、到期复习进入今日计划候选。

当前自动化覆盖用时校准核心验收：实际/预计比更新系数、零用时和异常极值忽略、
任务结果幂等不重复调整、不同任务类型隔离、连续超时建议拆分、计划生成读取最新系数。

当前自动化覆盖最小学习闭环 E2E：周目标、今日任务、任务结果幂等、阅读不越级、
掌握正常推进、复习失败回退、补救候选、单科过滤、机动时间和备份恢复后继续查询核心流程。

## 4. AI 黄金测试集

目录建议：

```text
tests/fixtures/ai/
  daily_evidence/
  math_wrong_questions/
  course_841_wrong_questions/
  expected/
```

每个样本包含原图、期望关键字段、允许差异、不确定字段和禁止推断。

## 5. PR 门禁

- 格式、静态检查、类型检查全部通过；
- 变更相关测试通过；
- 核心领域全量回归通过；
- 覆盖率不得低于配置门槛；
- 无高危依赖或密钥泄漏；
- 数据迁移通过双向验证；
- UI 变更附截图；
- 重大规则变更附新规则版本和验收矩阵更新。

## 6. 发布门禁

- 全量 E2E；
- Windows 目标构建；
- 干净安装初始化；
- 从上一正式版本升级；
- 自动备份、模拟失败和回滚；
- 关键数据一致性检查；
- 发布报告和已知问题完成。


## 6.1 LocalStorage import coverage

`apps/api/tests/test_localstorage_import.py` covers the localStorage migration boundary:

- `/imports/localstorage/preview` validates payloads without writing import batches.
- `/imports/localstorage/commit` commits idempotently by source hash.
- `/imports/localstorage` is a contract-compatible commit alias that returns the same batch on duplicate payloads.

## 7. Evidence draft acceptance coverage

`apps/api/tests/test_evidence_draft_pipeline.py` covers the first AI-draft gate:

- `EVID-001`: two uploaded files are linked to one evidence record with stable page order.
- `AI-002`: Fake Provider and mocked OpenAI-compatible output conform to `evidence-analysis-v1`.
- `EVID-002`: unconfirmed drafts do not create tasks, mastery evidence, mastery snapshots, or formal confirmed fields.
- `EVID-003`: confirmation is idempotent and writes exactly one `evidence.confirmed` audit event.
- `AI-003`: schema-invalid Fake Provider output becomes `failed`/`needs_correction`, then can be manually patched to `draft`.
- `AI-005`: mocked DeepSeek requests include image inputs while persisted jobs exclude API keys and base64 content.
- `AI-006`: a PDF sent to a real Provider fails closed as `AI_EVIDENCE_TYPE_UNSUPPORTED`.
- `EVID-004`: rejected drafts mark the draft and record as rejected without confirmation side effects.
- `EVID-005`: history returns ordered attachment metadata; deleting unconfirmed evidence removes drafts, jobs, links, and unreferenced files, while confirmed evidence returns a conflict.

## 8. Wrongbook domain acceptance coverage

`apps/api/tests/test_wrongbook_domain.py` covers the deterministic wrongbook lifecycle:

- `WRONG-001`: seven attachment roles are accepted only as separate strict roles; duplicate role/page links are rejected.
- `WRONG-002`: immediate original redo can only reach `pending_variant`; missing no-hint redo, variant, or interval test prevents `stable_corrected`.
- `WRONG-003`: failed attempts roll the record back to `regressed`, clear that verification flag, and increment `error_count`.
- Duplicate attempt submissions with the same `Idempotency-Key` return `created=false` and do not repeat state changes.
- Wrongbook history returns current record state, verification flags, ordered attempts, request ids, and no duplicate idempotency attempts.
- Regressed or unresolved wrong records appear as `wrong_record` planning candidates linked to their knowledge node subject.

## 9. Goal recalculation acceptance coverage

`apps/api/tests/test_goal_recalculation_history.py` covers stage 4 planning rollup:

- Task result submission recalculates the child goal and root ancestor goal.
- Goal progress and actual minutes roll up from task results into parent goals.
- `goal.recalculated` history events preserve request id and task-result source.
- Manual recalculate marks overdue unfinished goals high risk and delayed.
- Goal history API returns the emitted recalculation evidence.

## 10. Assets and resource index coverage

`apps/api/tests/test_assets_resources_api.py` covers the implemented file API boundary:

- `POST /assets` stores supported files, deduplicates by SHA-256, and increments reference count.
- Metadata responses expose relative storage paths only.
- `GET /assets/{asset_id}/content` returns the original content as base64.
- `DELETE /assets/{asset_id}` soft-deletes the asset and hides normal metadata reads.
- `POST /assets/{asset_id}/restore` restores deleted assets to `inbox`.
- `POST /resources` promotes an asset to the organized resource index.
- MIME masquerade and path traversal uploads are rejected with asset-specific error codes.

## 11. Graph and analytics coverage

`apps/api/tests/test_graph_analytics_api.py` covers the read-only insight API boundary:

- `GET /graph/full` returns clickable knowledge-node ids plus prerequisite edges.
- Graph node metrics include latest mastery stage and evidence count.
- `GET /graph/weak` filters latest mastery snapshots below stage 4 and preserves blocking reasons.
- `GET /analytics/overview` aggregates knowledge, goals, tasks, task results, wrong records, mastery snapshots, task status, and goal risk.
- `GET /analytics/time` aggregates estimated and actual minutes by subject.
- `GET /analytics/errors`, `/analytics/mastery`, and `/analytics/goal-risk` expose wrong-record distribution, mastery stage distribution, and risky goals.

## 12. Backup and export API coverage

`apps/api/tests/test_data_management_backup_api.py` covers the data-management API boundary:

- `POST /backups` creates a verified ZIP backup and returns a filename backup id without absolute paths.
- `GET /backups` lists available local backup archives.
- `POST /backups/{backup_id}/verify` validates the manifest and archive entries.
- `POST /backups/{backup_id}/restore` creates a pre-restore backup and restores both database state and file content visibility.
- Restore also rolls back `settings/profile.json` so local profile changes are protected.
- `GET /exports/full` creates an export archive through the same backup mechanism.
- Invalid backup labels and missing backup ids return structured API errors.

## 13. Settings profile and rules coverage

`apps/api/tests/test_settings_profile_rules_api.py` covers the settings API boundary:

- `GET /settings/profile` creates and returns the default local exam profile.
- `PATCH /settings/profile` persists partial updates into the runtime data directory.
- `GET /settings/rules` returns the three governed rule files with relative paths, versions, SHA-256 hashes, and raw content.
- Rules responses do not expose local absolute file paths.

## 14. Wrongbook result shortcut coverage

`apps/api/tests/test_wrongbook_domain.py` covers `POST /wrongbook/{wrong_id}/variant-results` and `POST /wrongbook/{wrong_id}/interval-results`:

- Shortcut endpoints force `variant` and `interval_test` attempt types without accepting an explicit `attempt_type`.
- The endpoints reuse the same deterministic wrongbook state machine as `/attempts`.
- `Idempotency-Key` prevents duplicate shortcut submissions from adding duplicate attempts or redo counts.

## 15. Wrongbook draft pipeline coverage

`apps/api/tests/test_wrongbook_domain.py` covers the wrongbook AI draft governance boundary:

- `POST /wrongbook/{wrong_id}/analyze` creates a fake-provider `ai_jobs` row and a `wrongbook_drafts` row.
- `POST /wrongbook/drafts` creates a manual draft for an existing wrong record behind the same confirmation gate.
- Unconfirmed drafts do not mutate formal wrong-record cause fields.
- Invalid drafts return `AI_DRAFT_NOT_CONFIRMED` on confirmation and keep the wrong record unchanged.
- `PATCH /wrongbook/{wrong_id}/draft` revalidates structured JSON and can repair a failed draft.
- `POST /wrongbook/{wrong_id}/confirm` is idempotent after first confirmation and writes one audit event.
