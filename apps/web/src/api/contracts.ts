export type ResponseMeta = {
  request_id: string;
};

export type ApiResponse<TData> = {
  data: TData;
  meta: ResponseMeta;
};

export type ApiErrorBody = {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
  request_id: string;
};

export type ApiErrorResponse = {
  error: ApiErrorBody;
};

export type HealthPayload = {
  status: "ok";
  service: "yantu-coach-api";
  environment: "dev" | "test" | "prod";
  data_root: string;
};

export type ApiMetaPayload = {
  service: "yantu-coach-api";
  api_version: "v1";
  contract_version: "contract-v1";
  environment: "dev" | "test" | "prod";
  features: string[];
};

export type TaskPayload = {
  id: string;
  version: number;
  goal_id: string | null;
  subject_id: string | null;
  knowledge_node_id: string | null;
  title: string;
  task_type: string;
  priority: string;
  source_type: string;
  source_id: string | null;
  planned_date: string;
  estimated_minutes: number;
  current_stage: number | null;
  target_stage: number | null;
  reason: string | null;
  completion_standard: string | null;
  prerequisite_status: string;
  status: "pending" | "in_progress" | "completed" | "skipped" | "withdrawn";
};

export type TodayPayload = {
  date: string;
  tasks: TaskPayload[];
  total_tasks: number;
  estimated_minutes: number;
};

export type TaskResultType = "completed" | "partial" | "wrong" | "unknown";

export type TaskResultCreatePayload = {
  result_type: TaskResultType;
  completion_ratio: number;
  actual_minutes: number;
  question_count?: number | null;
  correct_count?: number | null;
  accuracy?: number | null;
  confidence?: number | null;
  hint_level?: number | null;
  focus_level?: number | null;
  difficulty_rating?: number | null;
  problem_description?: string | null;
  confirmed_at?: string | null;
};

export type TaskResultPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  task_id: string;
  result_type: TaskResultType;
  completion_ratio: number;
  actual_minutes: number;
  question_count: number | null;
  correct_count: number | null;
  accuracy: number | null;
  confidence: number | null;
  hint_level: number | null;
  focus_level: number | null;
  difficulty_rating: number | null;
  problem_description: string | null;
  confirmed_at: string;
};

export type TaskResultSubmitPayload = {
  result: TaskResultPayload;
  created: boolean;
};

export type EvidenceRecordStatus = "pending" | "confirmed" | "rejected";
export type EvidenceDraftStatus = "draft" | "needs_correction" | "confirmed" | "rejected";
export type EvidenceProviderMode = "valid" | "invalid_schema";

export type EvidenceFileUploadPayload = {
  original_name: string;
  mime_type: "image/png" | "image/jpeg" | "application/pdf";
  content_base64: string;
};

export type EvidenceUploadCreatePayload = {
  study_date: string;
  subject_id?: string | null;
  files: EvidenceFileUploadPayload[];
};

export type EvidenceAssetPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  original_name: string;
  storage_path: string;
  mime_type: string;
  size_bytes: number;
  state: string;
  reference_count: number;
  page_order: number;
};

export type EvidenceRecordPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  study_date: string;
  subject_id: string | null;
  status: EvidenceRecordStatus;
  asset_count: number;
  confirmed_facts: Record<string, unknown> | null;
  inferences: Record<string, unknown> | null;
  uncertain_fields: Array<Record<string, unknown>> | null;
  teaching_judgment: Record<string, unknown> | null;
  suggested_actions: Array<Record<string, unknown>> | null;
  confirmed_at: string | null;
  rejected_at: string | null;
};

export type EvidenceUploadPayload = {
  record: EvidenceRecordPayload;
  assets: EvidenceAssetPayload[];
};

export type EvidenceAIJobPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  job_type: string;
  provider: string;
  model_name: string;
  prompt_version: string;
  status: "queued" | "running" | "succeeded" | "failed";
  attempts: number;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

export type EvidenceDraftPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  evidence_record_id: string;
  ai_job_id: string;
  status: EvidenceDraftStatus;
  schema_version: "evidence-analysis-v1";
  structured_json: Record<string, unknown>;
  validation_errors: string[];
  confirmed_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  confirmed_once: boolean;
};

export type EvidenceAnalyzeCreatePayload = {
  provider_mode?: EvidenceProviderMode;
};

export type EvidenceAnalyzePayload = {
  draft: EvidenceDraftPayload;
  ai_job: EvidenceAIJobPayload;
};

export type EvidenceConfirmPayload = {
  record: EvidenceRecordPayload;
  draft: EvidenceDraftPayload;
  created: boolean;
};

export type EvidenceHistoryItemPayload = {
  record: EvidenceRecordPayload;
  draft: EvidenceDraftPayload | null;
};

export type EvidenceHistoryPayload = {
  items: EvidenceHistoryItemPayload[];
  total: number;
};

export type EvidenceRejectCreatePayload = {
  reason: string;
};

export type GoalPayload = {
  id: string;
  version: number;
  parent_id: string | null;
  level: "semester" | "quarter" | "month" | "week" | "day";
  subject_id: string | null;
  title: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  estimated_minutes: number;
  actual_minutes: number;
  completion_standard: string | null;
  progress: number;
  risk_status: string;
  status: "draft" | "active" | "completed" | "delayed" | "archived" | "cancelled";
  adjustment_reason: string | null;
};

export type GoalTreePayload = GoalPayload & {
  children: GoalTreePayload[];
};

export type GoalTreeListPayload = {
  items: GoalTreePayload[];
  total: number;
};

export type SettingsProfilePayload = {
  name: string;
  target_school: string | null;
  target_major: string | null;
  exam_date: string | null;
  current_phase: string | null;
  coach_style: string;
  timezone: string;
  updated_at: string;
};

export type SettingsRulePayload = {
  key: string;
  version: string | null;
  path: string;
  sha256: string;
  content: string;
};

export type SettingsRulesPayload = {
  items: SettingsRulePayload[];
  total: number;
};

export type CountBucketPayload = {
  key: string;
  count: number;
};

export type AnalyticsOverviewPayload = {
  knowledge_nodes: number;
  goals: number;
  tasks: number;
  task_results: number;
  wrong_records: number;
  mastery_snapshots: number;
  average_goal_progress: number;
  task_status: CountBucketPayload[];
  goal_risk: CountBucketPayload[];
};

export type AnalyticsTimeBySubjectPayload = {
  subject_id: string;
  estimated_minutes: number;
  actual_minutes: number;
};

export type AnalyticsTimePayload = {
  estimated_minutes: number;
  actual_minutes: number;
  by_subject: AnalyticsTimeBySubjectPayload[];
};

export type AnalyticsErrorsByKnowledgePayload = {
  knowledge_node_id: string;
  count: number;
};

export type AnalyticsErrorsPayload = {
  total_wrong_records: number;
  by_status: CountBucketPayload[];
  by_knowledge_node: AnalyticsErrorsByKnowledgePayload[];
};

export type AnalyticsMasteryPayload = {
  latest_snapshot_count: number;
  weak_node_count: number;
  stage_distribution: CountBucketPayload[];
};

export type AnalyticsGoalRiskItemPayload = {
  object_type: "goal";
  object_id: string;
  title: string;
  level: string;
  risk_status: string;
  status: string;
  progress: number;
};

export type AnalyticsGoalRiskPayload = {
  total_goals: number;
  by_risk_status: CountBucketPayload[];
  risky_goals: AnalyticsGoalRiskItemPayload[];
};

export type WeakNodePayload = {
  object_type: "knowledge_node";
  object_id: string;
  label: string;
  subject_id: string | null;
  latest_stage: number;
  evidence_count: number;
  repeat_error_rate: number | null;
  blocking_reasons: string[];
};

export type WeakGraphPayload = {
  items: WeakNodePayload[];
  total: number;
};

export type AssetPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  sha256: string;
  original_name: string;
  storage_path: string;
  mime_type: "image/png" | "image/jpeg" | "application/pdf";
  size_bytes: number;
  state: "inbox" | "organized" | "archived" | "deleted";
  reference_count: number;
};

export type ResourcePayload = {
  id: string;
  resource_type: "asset";
  asset: AssetPayload;
};

export type ResourceListPayload = {
  items: ResourcePayload[];
  total: number;
};

export type KnowledgeNodePayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  is_deleted: boolean;
  deleted_at: string | null;
  subject_id: string;
  parent_id: string | null;
  code: string;
  name: string;
  node_type: "subject" | "module" | "chapter" | "knowledge";
  importance: number | null;
  exam_frequency: number | null;
  description: string | null;
  status: string;
};

export type KnowledgeNodeListPayload = {
  items: KnowledgeNodePayload[];
  total: number;
};

export type WrongbookCandidatePayload = {
  id: string;
  title: string;
  subject_id: string;
  estimated_minutes: number;
  cognitive_load: "low" | "medium" | "high";
  source_type: string;
  source_id: string | null;
  task_type: string;
  difficulty: string | null;
  review_due: number;
  knowledge_importance: number;
  weakness: number;
  repeat_error: number;
};

export type WrongbookCandidateListPayload = {
  items: WrongbookCandidatePayload[];
  total: number;
};

export type WrongbookAttemptType =
  | "original_redo"
  | "no_hint_redo"
  | "variant"
  | "interval_test"
  | "transfer_test";

export type WrongbookStatus =
  | "pending_analysis"
  | "pending_no_hint_redo"
  | "pending_variant"
  | "pending_interval"
  | "stable_corrected"
  | "regressed";

export type WrongbookAttemptResultCreatePayload = {
  is_correct: boolean;
  attempted_at?: string | null;
  answer_text?: string | null;
  score?: number | null;
  duration_seconds?: number | null;
  hint_level?: number | null;
  confidence?: number | null;
};

export type WrongbookRecordPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  question_id: string;
  knowledge_node_id: string | null;
  surface_cause: string | null;
  deep_cause: string | null;
  prerequisite_gap: string | null;
  error_count: number;
  redo_count: number;
  current_status: WrongbookStatus;
  next_review_at: string | null;
  resolved_at: string | null;
};

export type WrongbookVerificationPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  wrong_record_id: string;
  original_redo_passed: boolean;
  no_hint_redo_passed: boolean;
  variant_passed: boolean;
  interval_test_passed: boolean;
  transfer_test_passed: boolean;
  last_attempt_id: string | null;
};

export type WrongbookAttemptPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  question_id: string;
  wrong_record_id: string;
  idempotency_key: string | null;
  attempt_type: WrongbookAttemptType;
  attempted_at: string;
  answer_text: string | null;
  is_correct: boolean;
  score: number | null;
  duration_seconds: number | null;
  hint_level: number | null;
  confidence: number | null;
  request_id: string | null;
};

export type WrongbookAttemptSubmitPayload = {
  attempt: WrongbookAttemptPayload;
  record: WrongbookRecordPayload;
  verification: WrongbookVerificationPayload;
  created: boolean;
};

export type ReviewResultType = "pass" | "fail";

export type ReviewSchedulePayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  knowledge_node_id: string;
  subject_id: string | null;
  current_stage: number;
  status: "active" | "paused" | "completed" | "archived";
  due_at: string;
  interval_days: number;
  pass_streak: number;
  fail_streak: number;
  last_reviewed_at: string | null;
  last_result_id: string | null;
  source_snapshot_id: string | null;
  rule_version: "review-v1.0.0";
  next_reason: string;
};

export type ReviewCandidatePayload = {
  id: string;
  title: string;
  subject_id: string;
  estimated_minutes: number;
  cognitive_load: "low" | "medium" | "high";
  source_type: string;
  source_id: string | null;
  task_type: string;
  review_due: number;
  knowledge_importance: number;
};

export type DueReviewPayload = {
  schedule: ReviewSchedulePayload;
  knowledge_node_name: string;
  candidate: ReviewCandidatePayload;
};

export type DueReviewListPayload = {
  date: string;
  items: DueReviewPayload[];
  total: number;
};

export type ReviewResultCreatePayload = {
  result_type: ReviewResultType;
  score?: number | null;
  sample_count?: number;
  correct_count?: number | null;
  accuracy?: number | null;
  occurred_at?: string | null;
};

export type ReviewResultPayload = {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  schedule_id: string;
  knowledge_node_id: string;
  result_type: ReviewResultType;
  score: number | null;
  sample_count: number;
  correct_count: number | null;
  accuracy: number | null;
  occurred_at: string;
  independent_timepoint: boolean;
  evidence_id: string | null;
  snapshot_id: string | null;
};

export type ReviewResultSubmitPayload = {
  result: ReviewResultPayload;
  schedule: ReviewSchedulePayload;
  created: boolean;
  evaluation_new_stage: number | null;
  evaluation_reason: string | null;
  rule_version: "review-v1.0.0";
};
