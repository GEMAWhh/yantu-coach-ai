# 数据模型契约

## 1. 通用字段

正式业务表原则上包含：

```text
id: UUID/ULID
created_at, updated_at
version: 乐观锁版本
created_by: user/system/ai_draft
is_deleted, deleted_at
```

关键自动判定表还应包含 `rule_version`、`source_type` 和 `source_id`。

## 2. 核心实体关系

```text
Profile ── Subjects
Profile ── Goals(parent-child)
Goal ── Tasks ── TaskResults
KnowledgeNode ── MasteryEvidence ── MasterySnapshot
KnowledgeNode ── ReviewSchedules
Asset ── EvidenceDraft ── ConfirmedStudyRecord
Question ── QuestionAssets ── Attempts ── WrongRecord
KnowledgeNode ── KnowledgeEdges
AIJob ── AIDraft ── ConfirmationAudit
```

## 3. 建议表

### profiles

`name, target_school, target_major, exam_date, current_phase, coach_style, timezone`

### subjects

`name, exam_code, priority, target_score, status`

### goals

`parent_id, level, subject_id, title, description, start_date, end_date, estimated_minutes, actual_minutes, completion_standard, progress, risk_status, status, adjustment_reason`

`level`: semester / quarter / month / week / day。

### tasks

`goal_id, subject_id, knowledge_node_id, wrong_record_id, review_schedule_id, title, task_type, priority, source_type, source_id, planned_date, estimated_minutes, difficulty, cognitive_load, current_stage, target_stage, reason, completion_standard, prerequisite_status, status`

### task_results

`task_id, result_type, completion_ratio, actual_minutes, question_count, correct_count, accuracy, confidence, hint_level, focus_level, difficulty_rating, problem_description, confirmed_at`

当前实现额外保存 `idempotency_key` 和 `request_id`。提交结果用于更新目标进度，
但不会直接创建或修改掌握快照。首次提交的任务结果会进入个人用时系数校准；
重复幂等提交不会重复调整系数。

### knowledge_nodes

`subject_id, parent_id, code, name, node_type, importance, exam_frequency, description, status`

### knowledge_edges

`source_node_id, target_node_id, relation_type, weight, source, confirmed`

关系：belongs_to / prerequisite / similar_to / confused_with / co_tested / transforms_to。

当前 `prerequisite` 约定：`source_node_id` 是前置节点，
`target_node_id` 是被阻塞节点。写入时必须防止前置环路。

### mastery_evidence

`knowledge_node_id, evidence_type, source_type, source_id, score, sample_count, hint_level, occurred_at, confirmed`

当前证据类型：reading / self_explanation / closed_book_recall / basic_question /
variant_question / integrated_question / interval_test / repeat_deep_cause。

### mastery_snapshots

`knowledge_node_id, stage, recall_score, basic_score, variant_score, transfer_score, retention_score, repeat_error_rate, confidence_calibration, missing_link, evaluated_at, rule_version, transition_reason`

当前快照额外保存 `previous_stage`、`evidence_ids_json`、`computed_metrics_json`、
`blocking_reasons_json` 和 `remediation_json`，用于审计 MAST-001 至 MAST-009。

### review_schedules

`knowledge_node_id, subject_id, current_stage, status, due_at, interval_days, pass_streak, fail_streak, last_reviewed_at, last_result_id, source_snapshot_id, rule_version, next_reason`

当前实现使用 `review-v1.0.0`，按 `mastery_rules.v1.yaml` 的阶段基础间隔生成到期时间。

### review_results

`schedule_id, knowledge_node_id, result_type, score, sample_count, correct_count, accuracy, occurred_at, independent_timepoint, evidence_id, snapshot_id, request_id`

当前实现额外保存 `idempotency_key`。独立复习结果会创建 `interval_test` 掌握证据；
失败结果会触发掌握回退并缩短下一次间隔，同日即时重做不计入独立时间点。

### time_coefficients

`subject_id, task_type, difficulty, coefficient, sample_count, overtime_streak, last_ratio, last_estimated_minutes, last_actual_minutes, last_task_result_id, rule_version, rationale_json`

当前实现使用 `time-calibration-v1.0.0`，系数按科目、任务类型和难度隔离，范围限制为
`0.6–1.8`。

### time_adjustments

`coefficient_id, task_id, task_result_id, subject_id, task_type, difficulty, estimated_minutes, actual_minutes, raw_ratio, applied_ratio, previous_coefficient, new_coefficient, ignored, ignore_reason, overtime, suggested_split, rule_version, occurred_at, request_id`

调整记录用于向用户展示系数来源。零用时和异常极值会记录为 ignored，但不更新当前系数。

### assets

`sha256, original_name, storage_path, mime_type, size_bytes, width, height, page_count, state`

### evidence_records

`evidence_type, study_date, subject_id, knowledge_node_id, confirmed_status, actual_minutes, question_count, accuracy, confirmed_facts_json, uncertain_fields_json`

### questions

`subject_id, knowledge_node_id, standard_text, question_type, difficulty, source, source_year, source_page, status`

### question_assets

`question_id, asset_id, asset_role, page_order`

`asset_role`: statement / figure / my_answer / marking / standard_answer / original_solution / supplement。

### attempts

`question_id, attempt_type, attempted_at, answer_text, is_correct, score, duration_seconds, hint_level, confidence`

### wrong_records

`question_id, surface_cause, deep_cause, prerequisite_gap, error_count, redo_count, current_status, next_review_at, resolved_at`

### wrong_verifications

`wrong_record_id, original_redo_passed, no_hint_redo_passed, variant_passed, interval_test_passed, transfer_test_passed`

### ai_jobs

`job_type, provider, model_name, prompt_version, status, attempts, started_at, completed_at, error_code`

### ai_drafts

`job_id, draft_type, source_asset_id, raw_response_ref, structured_json, confidence_json, status, confirmed_at`

### audit_events

`event_type, actor_type, actor_id, object_type, object_id, before_json, after_json, reason, request_id`

### backups

`version, created_at, database_hash, manifest_hash, file_count, size_bytes, status, restore_tested_at`

## 4. 状态枚举

- Goal: draft / active / completed / delayed / archived / cancelled
- Task: pending / in_progress / completed / skipped / withdrawn
- TaskResult: completed / partial / wrong / unknown
- Asset: inbox / organized / archived / deleted
- AIDraft: processing / draft / needs_correction / confirmed / rejected / failed
- WrongRecord: pending_analysis / pending_no_hint_redo / pending_variant / pending_interval / stable_corrected / regressed

## 5. 数据完整性

- 开启外键；
- 状态字段使用约束或枚举映射；
- 正确率范围 0–100；
- 实际用时不得为负；
- 确认后的 AI 草稿不可再次确认；
- 掌握快照不可无证据来源；
- 删除文件前检查引用计数；
- 恢复备份前先备份当前状态。


## 6. Implemented evidence draft tables

Migration `0009_evidence_draft_pipeline` adds these concrete tables:

- `ai_jobs`: `job_type`, `provider`, `model_name`, `prompt_version`, `status`, `attempts`, `input_json`, `output_json`, `error_code`, `error_message`, `started_at`, `completed_at`.
- `evidence_records`: `created_by`, `study_date`, `subject_id`, `status`, `asset_count`, `confirmed_facts_json`, `inferences_json`, `uncertain_fields_json`, `teaching_judgment_json`, `suggested_actions_json`, `confirmed_at`, `rejected_at`.
- `evidence_assets`: `evidence_record_id`, `asset_id`, `page_order`.
- `evidence_drafts`: `evidence_record_id`, `ai_job_id`, `status`, `schema_version`, `structured_json`, `validation_errors_json`, `confirmed_at`, `rejected_at`, `rejection_reason`, `confirmed_once`.

Status values currently used:

- `evidence_records.status`: `pending`, `confirmed`, `rejected`.
- `evidence_drafts.status`: `draft`, `needs_correction`, `confirmed`, `rejected`.
- `ai_jobs.status`: `succeeded`, `failed`.

Unconfirmed drafts are isolated from `tasks`, `mastery_evidence`, and `mastery_snapshots`. Confirmation copies only the validated structured evidence fields into the formal record and writes an audit event.

## 7. Implemented wrongbook tables

Migration `0010_wrongbook_domain` adds these concrete tables:

- `questions`: structured question text, optional `subject_id`, optional `knowledge_node_id`, type, difficulty, source, year, page, and status.
- `question_assets`: existing `asset_id` linked to a question through strict `asset_role` and `page_order`.
- `wrong_records`: question link, optional knowledge-node link, manual causes, `error_count`, `redo_count`, `current_status`, `next_review_at`, and `resolved_at`.
- `attempts`: attempt type, correctness, score, duration, hint level, confidence, idempotency key, and request id.
- `wrong_verifications`: per-record flags for original redo, no-hint redo, variant, interval test, transfer test, and latest attempt.

Current wrong statuses are `pending_analysis`, `pending_no_hint_redo`, `pending_variant`, `pending_interval`, `stable_corrected`, and `regressed`. Required stable correction checks are no-hint redo, variant, and interval test.

## 8. Implemented goal history events

Migration `0011_goal_recalculation_history` adds `goal_history_events`:

`goal_id, event_type, previous_progress, new_progress, previous_actual_minutes, new_actual_minutes, previous_risk_status, new_risk_status, previous_status, new_status, reason, source_type, source_id, request_id`

These events are append-only audit evidence for deterministic goal recalculation. They do not replace `audit_events`; they are domain-level planning history optimized for the UI and reports.
