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
