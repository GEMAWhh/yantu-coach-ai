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
