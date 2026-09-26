import type {
  AnalyticsErrorsPayload,
  AnalyticsGoalRiskPayload,
  AnalyticsMasteryPayload,
  AnalyticsOverviewPayload,
  AnalyticsTimePayload,
  ApiMetaPayload,
  ApiResponse,
  AssetContentPayload,
  AssetPayload,
  AssetUploadCreatePayload,
  DueReviewListPayload,
  EvidenceAIJobPayload,
  EvidenceAnalyzePayload,
  EvidenceConfirmPayload,
  EvidenceDraftPayload,
  EvidenceFileUploadPayload,
  EvidenceHistoryPayload,
  EvidenceRecordPayload,
  EvidenceUploadCreatePayload,
  EvidenceUploadPayload,
  GoalCreatePayload,
  GoalPayload,
  GoalTreePayload,
  GoalTreeListPayload,
  GoalUpdatePayload,
  HealthPayload,
  KnowledgeNodeListPayload,
  KnowledgeNodeCreatePayload,
  KnowledgeNodePayload,
  KnowledgeNodeUpdatePayload,
  ResourceCreatePayload,
  ResourcePayload,
  ResourceListPayload,
  ReviewResultCreatePayload,
  ReviewResultSubmitPayload,
  SettingsProfilePayload,
  SettingsProfileUpdatePayload,
  SettingsRulesPayload,
  TaskCreatePayload,
  TaskListPayload,
  TaskPayload,
  TaskUpdatePayload,
  TaskResultCreatePayload,
  TaskResultSubmitPayload,
  TodayPayload,
  WeakGraphPayload,
  WrongbookAIJobPayload,
  WrongbookAnalyzePayload,
  WrongbookAttemptResultCreatePayload,
  WrongbookAttemptSubmitPayload,
  WrongbookCandidateListPayload,
  WrongbookConfirmPayload,
  WrongbookDraftHistoryPayload,
  WrongbookDraftPayload,
  WrongbookRecordPayload,
  WrongbookVerificationPayload,
} from "./contracts";

type DemoMethod = "GET" | "POST" | "PATCH" | "DELETE";

type DemoRequest = {
  method: DemoMethod;
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
};

const now = "2026-07-15T09:00:00Z";
const tomorrow = "2026-07-16T09:00:00Z";
let demoSequence = 100;

let demoTasks: TaskPayload[] = [
  {
    id: "demo-task-1",
    version: 1,
    goal_id: "goal-week-math",
    subject_id: "数学一",
    knowledge_node_id: "node-derivative",
    title: "导数应用闭卷回忆",
    task_type: "closed_book_recall",
    priority: "must",
    source_type: "goal",
    source_id: "goal-week-math",
    planned_date: "2026-07-15",
    estimated_minutes: 35,
    current_stage: 2,
    target_stage: 3,
    reason: "基础理解后需要闭卷证据，不能只靠阅读推进掌握状态。",
    completion_standard: "不看笔记复述极值、单调性和切线题的判定步骤。",
    prerequisite_status: "satisfied",
    status: "pending",
  },
  {
    id: "demo-task-2",
    version: 1,
    goal_id: "goal-week-math",
    subject_id: "数学一",
    knowledge_node_id: "node-series",
    title: "级数判敛错题变式",
    task_type: "wrongbook_variant",
    priority: "high",
    source_type: "wrong_record",
    source_id: "wrong-derivative-1",
    planned_date: "2026-07-15",
    estimated_minutes: 25,
    current_stage: 3,
    target_stage: 4,
    reason: "重复错因来自条件遗漏，先用变式验证是否真正脱离原题记忆。",
    completion_standard: "完成 3 道同类变式并记录错因是否复现。",
    prerequisite_status: "satisfied",
    status: "pending",
  },
  {
    id: "demo-task-3",
    version: 1,
    goal_id: "goal-week-english",
    subject_id: "英语一",
    knowledge_node_id: "node-reading",
    title: "阅读长难句证据整理",
    task_type: "evidence_review",
    priority: "normal",
    source_type: "evidence_draft",
    source_id: "evidence-demo-1",
    planned_date: "2026-07-15",
    estimated_minutes: 20,
    current_stage: 1,
    target_stage: 2,
    reason: "把截图和手写笔记整理成可确认事实，确认前不推进掌握。",
    completion_standard: "确认草稿或驳回重拍。",
    prerequisite_status: "satisfied",
    status: "in_progress",
  },
];

let evidenceRecords: EvidenceRecordPayload[] = [
  {
    id: "evidence-demo-1",
    version: 1,
    created_at: "2026-07-14T20:00:00Z",
    updated_at: "2026-07-14T20:01:00Z",
    created_by: "user",
    study_date: "2026-07-14",
    subject_id: "数学一",
    status: "pending",
    asset_count: 2,
    confirmed_facts: null,
    inferences: null,
    uncertain_fields: null,
    teaching_judgment: null,
    suggested_actions: null,
    confirmed_at: null,
    rejected_at: null,
  },
];

let evidenceDrafts: EvidenceDraftPayload[] = [
  {
    id: "evidence-draft-demo-1",
    version: 1,
    created_at: "2026-07-14T20:02:00Z",
    updated_at: "2026-07-14T20:02:00Z",
    evidence_record_id: "evidence-demo-1",
    ai_job_id: "evidence-job-demo-1",
    status: "draft",
    schema_version: "evidence-analysis-v1",
    structured_json: {
      confirmed_facts: {
        asset_count: 2,
        subject: "数学一",
        activity: "导数应用闭卷回忆",
      },
      inferences: {
        likely_issue: "判定步骤能复述，但对参数范围变化不稳定。",
      },
      teaching_judgment: {
        mastery_limit: "基础理解",
        reason: "缺少独立做题结果，不能推进到稳定掌握。",
      },
      suggested_actions: [
        { type: "closed_book_recall", title: "隔日闭卷复述判定流程" },
        { type: "variant_practice", title: "补 2 道参数讨论变式" },
      ],
    },
    validation_errors: [],
    confirmed_at: null,
    rejected_at: null,
    rejection_reason: null,
    confirmed_once: false,
  },
];

const wrongRecord: WrongbookRecordPayload = {
  id: "wrong-derivative-1",
  version: 1,
  created_at: "2026-07-14T18:00:00Z",
  updated_at: "2026-07-14T18:01:00Z",
  created_by: "user",
  question_id: "question-derivative-12",
  knowledge_node_id: "node-derivative",
  surface_cause: null,
  deep_cause: null,
  prerequisite_gap: null,
  error_count: 2,
  redo_count: 1,
  current_status: "pending_analysis",
  next_review_at: null,
  resolved_at: null,
};

let wrongRecords: WrongbookRecordPayload[] = [wrongRecord];

let wrongVerifications: WrongbookVerificationPayload[] = [
  {
    id: "wrong-verification-1",
    version: 1,
    created_at: "2026-07-14T18:00:00Z",
    updated_at: "2026-07-14T18:01:00Z",
    wrong_record_id: "wrong-derivative-1",
    original_redo_passed: true,
    no_hint_redo_passed: false,
    variant_passed: false,
    interval_test_passed: false,
    transfer_test_passed: false,
    last_attempt_id: null,
  },
];

let wrongDrafts: WrongbookDraftPayload[] = [
  {
    id: "wrong-draft-demo-1",
    version: 1,
    created_at: "2026-07-14T18:02:00Z",
    updated_at: "2026-07-14T18:02:00Z",
    wrong_record_id: "wrong-derivative-1",
    ai_job_id: "wrong-job-demo-1",
    status: "draft",
    schema_version: "wrongbook-analysis-v1",
    structured_json: {
      surface_cause: "参数范围遗漏",
      deep_cause: "把导数符号表当成固定模板，遇到端点讨论时没有重新验证条件。",
      prerequisite_gap: "函数单调性与极值的充分必要条件边界",
      remediation_plan: [
        { action: "redo_without_hints", title: "无提示重做原题" },
        { action: "variant", title: "参数范围变式 2 道" },
      ],
      uncertain_fields: [],
    },
    validation_errors: [],
    confirmed_at: null,
    confirmed_once: false,
  },
];

let knowledgeNodes: KnowledgeNodeListPayload = {
  total: 4,
  items: [
    {
      id: "node-derivative",
      version: 1,
      created_at: now,
      updated_at: now,
      created_by: "user",
      is_deleted: false,
      deleted_at: null,
      subject_id: "数学一",
      parent_id: null,
      code: "MATH-A-01",
      name: "导数应用",
      node_type: "knowledge",
      importance: 95,
      exam_frequency: 92,
      description: "单调性、极值、切线与参数讨论。",
      status: "active",
    },
    {
      id: "node-series",
      version: 1,
      created_at: now,
      updated_at: now,
      created_by: "user",
      is_deleted: false,
      deleted_at: null,
      subject_id: "数学一",
      parent_id: null,
      code: "MATH-A-02",
      name: "级数判敛",
      node_type: "knowledge",
      importance: 88,
      exam_frequency: 86,
      description: "比较、比值、根值与交错级数。",
      status: "active",
    },
    {
      id: "node-reading",
      version: 1,
      created_at: now,
      updated_at: now,
      created_by: "user",
      is_deleted: false,
      deleted_at: null,
      subject_id: "英语一",
      parent_id: null,
      code: "ENG-R-01",
      name: "长难句定位",
      node_type: "knowledge",
      importance: 78,
      exam_frequency: 82,
      description: "主干、修饰和指代关系。",
      status: "active",
    },
    {
      id: "node-control",
      version: 1,
      created_at: now,
      updated_at: now,
      created_by: "user",
      is_deleted: false,
      deleted_at: null,
      subject_id: "841",
      parent_id: null,
      code: "CTRL-01",
      name: "状态空间模型",
      node_type: "knowledge",
      importance: 75,
      exam_frequency: 70,
      description: "系统矩阵、能控能观与响应。",
      status: "active",
    },
  ],
};

let resources: ResourceListPayload = {
  total: 2,
  items: [
    {
      id: "resource-demo-1",
      resource_type: "asset",
      asset: {
        id: "asset-demo-1",
        version: 1,
        created_at: now,
        updated_at: now,
        sha256: "a".repeat(64),
        original_name: "数学一_导数应用错题.pdf",
        storage_path: "files/original/math-derivative.pdf",
        mime_type: "application/pdf",
        size_bytes: 186240,
        state: "organized",
        reference_count: 3,
      },
    },
    {
      id: "resource-demo-2",
      resource_type: "asset",
      asset: {
        id: "asset-demo-2",
        version: 1,
        created_at: now,
        updated_at: now,
        sha256: "b".repeat(64),
        original_name: "英语阅读长难句截图.png",
        storage_path: "files/original/english-reading.png",
        mime_type: "image/png",
        size_bytes: 84212,
        state: "inbox",
        reference_count: 1,
      },
    },
  ],
};

const demoAssetContent = new Map<string, string>();

const settingsProfile: SettingsProfilePayload = {
  name: "研途用户",
  target_school: "大连理工大学",
  target_major: "控制科学与工程学硕",
  exam_date: "2026-12-20",
  current_phase: "强化阶段",
  coach_style: "balanced",
  timezone: "Asia/Shanghai",
  updated_at: now,
};

const settingsRules: SettingsRulesPayload = {
  total: 3,
  items: [
    {
      key: "mastery_rules",
      version: "mastery-v1.0.0",
      path: "config/mastery_rules.v1.yaml",
      sha256: "c".repeat(64),
      content: "stage_thresholds: governed",
    },
    {
      key: "planning_rules",
      version: "planning-v1.0.0",
      path: "config/planning_rules.v1.yaml",
      sha256: "d".repeat(64),
      content: "daily_capacity: governed",
    },
    {
      key: "quality_gates",
      version: "quality-gates-v1.0.0",
      path: "config/quality_gates.v1.yaml",
      sha256: "e".repeat(64),
      content: "checks: required",
    },
  ],
};

export function isDemoApiEnabled(): boolean {
  return String(import.meta.env.VITE_YANTU_DEMO_API).toLowerCase() === "true";
}

export async function demoApiRequest<TData>(request: DemoRequest): Promise<ApiResponse<TData>> {
  const url = new URL(request.path, "https://demo.yantu.local");
  const path = url.pathname;

  if (request.method === "GET") {
    return routeDemoGet<TData>(path, url.searchParams);
  }
  if (request.method === "POST") {
    return routeDemoPost<TData>(path, request.body, request.headers ?? {});
  }
  if (request.method === "DELETE") {
    return routeDemoDelete<TData>(path);
  }
  return routeDemoPatch<TData>(path, request.body);
}

function routeDemoGet<TData>(path: string, params: URLSearchParams): ApiResponse<TData> {
  if (path === "/health") {
    return respond<TData>(
      {
        status: "ok",
        service: "yantu-coach-api",
        environment: "prod",
        data_root: "demo-memory",
      } satisfies HealthPayload,
      "health",
    );
  }
  if (path === "/api/v1/meta") {
    return respond<TData>(
      {
        service: "yantu-coach-api",
        api_version: "v1",
        contract_version: "contract-v1",
        environment: "prod",
        features: ["hosted-demo", "evidence-drafts", "wrongbook-drafts"],
      } satisfies ApiMetaPayload,
      "meta",
    );
  }
  if (path === "/api/v1/today") {
    return respond<TData>(todayPayload(params.get("date") ?? "2026-07-15"), "today");
  }
  if (path === "/api/v1/goals/tree") {
    return respond<TData>(goalTree(), "goals-tree");
  }
  if (path === "/api/v1/tasks") {
    return respond<TData>(
      {
        items: demoTasks,
        total: demoTasks.length,
      } satisfies TaskListPayload,
      "tasks",
    );
  }
  if (path === "/api/v1/settings/profile") {
    return respond<TData>(settingsProfile, "settings-profile");
  }
  if (path === "/api/v1/settings/rules") {
    return respond<TData>(settingsRules, "settings-rules");
  }
  if (path === "/api/v1/analytics/overview") {
    return respond<TData>(analyticsOverview(), "analytics-overview");
  }
  if (path === "/api/v1/analytics/time") {
    return respond<TData>(
      {
        estimated_minutes: 180,
        actual_minutes: 205,
        by_subject: [
          { subject_id: "数学一", estimated_minutes: 110, actual_minutes: 135 },
          { subject_id: "英语一", estimated_minutes: 40, actual_minutes: 38 },
          { subject_id: "841", estimated_minutes: 30, actual_minutes: 32 },
        ],
      } satisfies AnalyticsTimePayload,
      "analytics-time",
    );
  }
  if (path === "/api/v1/analytics/errors") {
    return respond<TData>(
      {
        total_wrong_records: wrongRecords.length,
        by_status: [
          { key: "pending_analysis", count: countWrongStatus("pending_analysis") },
          { key: "pending_no_hint_redo", count: countWrongStatus("pending_no_hint_redo") },
          { key: "pending_interval", count: countWrongStatus("pending_interval") },
          { key: "regressed", count: countWrongStatus("regressed") },
        ],
        by_knowledge_node: [{ knowledge_node_id: "node-derivative", count: 2 }],
      } satisfies AnalyticsErrorsPayload,
      "analytics-errors",
    );
  }
  if (path === "/api/v1/analytics/mastery") {
    return respond<TData>(
      {
        latest_snapshot_count: 24,
        weak_node_count: 3,
        stage_distribution: [
          { key: "1", count: 4 },
          { key: "2", count: 6 },
          { key: "3", count: 7 },
          { key: "4", count: 4 },
          { key: "5", count: 3 },
        ],
      } satisfies AnalyticsMasteryPayload,
      "analytics-mastery",
    );
  }
  if (path === "/api/v1/analytics/goal-risk") {
    return respond<TData>(
      {
        total_goals: 5,
        by_risk_status: [
          { key: "normal", count: 3 },
          { key: "slow", count: 1 },
          { key: "blocked", count: 1 },
        ],
        risky_goals: [
          {
            object_type: "goal",
            object_id: "goal-week-math",
            title: "本周数学一导数与级数补强",
            level: "week",
            risk_status: "slow",
            status: "active",
            progress: 62,
          },
        ],
      } satisfies AnalyticsGoalRiskPayload,
      "analytics-goal-risk",
    );
  }
  if (path === "/api/v1/graph/weak") {
    return respond<TData>(
      {
        total: 3,
        items: [
          {
            object_type: "knowledge_node",
            object_id: "node-derivative",
            label: "导数应用",
            subject_id: "数学一",
            latest_stage: 2,
            evidence_count: 4,
            repeat_error_rate: 40,
            blocking_reasons: ["缺少变式通过", "参数范围遗漏复现"],
          },
          {
            object_type: "knowledge_node",
            object_id: "node-series",
            label: "级数判敛",
            subject_id: "数学一",
            latest_stage: 3,
            evidence_count: 3,
            repeat_error_rate: 25,
            blocking_reasons: ["间隔复测未完成"],
          },
          {
            object_type: "knowledge_node",
            object_id: "node-reading",
            label: "长难句定位",
            subject_id: "英语一",
            latest_stage: 4,
            evidence_count: 5,
            repeat_error_rate: null,
            blocking_reasons: [],
          },
        ],
      } satisfies WeakGraphPayload,
      "weak-graph",
    );
  }
  if (path === "/api/v1/resources") {
    return respond<TData>(resources, "resources");
  }
  const assetContentMatch = path.match(/^\/api\/v1\/assets\/([^/]+)\/content$/);
  if (assetContentMatch) {
    const assetId = decodeURIComponent(assetContentMatch[1]);
    const resource = resources.items.find((item) => item.asset.id === assetId);
    if (!resource) throw new Error(`Demo asset not found: ${assetId}`);
    return respond<TData>(
      { metadata: resource.asset, content_base64: demoAssetContent.get(assetId) ?? "" } satisfies AssetContentPayload,
      "asset-content",
    );
  }
  if (path === "/api/v1/knowledge/nodes") {
    return respond<TData>(knowledgeNodes, "knowledge-nodes");
  }
  if (path === "/api/v1/wrongbook/planning-candidates") {
    return respond<TData>(wrongbookCandidates(), "wrongbook-candidates");
  }
  if (path === "/api/v1/wrongbook/history") {
    return respond<TData>(wrongbookHistory(limitParam(params)), "wrongbook-history");
  }
  if (path === "/api/v1/reviews/due") {
    return respond<TData>(dueReviews(params.get("date") ?? "2026-07-15"), "due-reviews");
  }
  if (path === "/api/v1/evidence/history") {
    return respond<TData>(evidenceHistory(limitParam(params)), "evidence-history");
  }

  throw new Error(`Demo API route is not implemented: GET ${path}`);
}

function routeDemoPost<TData>(
  path: string,
  body: unknown,
  headers: Record<string, string>,
): ApiResponse<TData> {
  if (path === "/api/v1/tasks") {
    return respond<TData>(createDemoTask(body as TaskCreatePayload), "task-create");
  }
  if (path === "/api/v1/goals") {
    return respond<TData>(createDemoGoal(body as GoalCreatePayload), "goal-create");
  }
  if (path === "/api/v1/assets") {
    const payload = body as AssetUploadCreatePayload;
    const asset: AssetPayload = {
      id: `asset-demo-${++demoSequence}`, version: 1, created_at: now, updated_at: now,
      sha256: "d".repeat(64), original_name: payload.original_name,
      storage_path: `files/original/${payload.original_name}`, mime_type: payload.mime_type,
      size_bytes: Math.max(1, Math.round(payload.content_base64.length * 0.75)),
      state: payload.state ?? "inbox", reference_count: 0,
    };
    demoAssetContent.set(asset.id, payload.content_base64);
    resources = { ...resources, items: [...resources.items, { id: asset.id, resource_type: "asset", asset }], total: resources.total + 1 };
    return respond<TData>(asset, "asset-upload");
  }
  if (path === "/api/v1/resources") {
    const payload = body as ResourceCreatePayload;
    const resource = resources.items.find((item) => item.asset.id === payload.asset_id);
    if (!resource) throw new Error(`Demo asset not found: ${payload.asset_id}`);
    resource.asset.reference_count = Math.max(1, resource.asset.reference_count);
    return respond<TData>(resource satisfies ResourcePayload, "resource-create");
  }
  if (path === "/api/v1/knowledge/nodes") {
    const payload = body as KnowledgeNodeCreatePayload;
    const node: KnowledgeNodePayload = {
      id: `node-demo-${++demoSequence}`, version: 1, created_at: now, updated_at: now,
      created_by: "user", is_deleted: false, deleted_at: null,
      subject_id: payload.subject_id ?? `node-demo-${demoSequence}`, parent_id: payload.parent_id ?? null,
      code: payload.code, name: payload.name, node_type: payload.node_type,
      importance: payload.importance ?? null, exam_frequency: payload.exam_frequency ?? null,
      description: payload.description ?? null, status: payload.status ?? "active",
    };
    knowledgeNodes = { items: [...knowledgeNodes.items, node], total: knowledgeNodes.total + 1 };
    return respond<TData>(node, "knowledge-node-create");
  }
  const taskActionMatch = path.match(/^\/api\/v1\/tasks\/([^/]+)\/(start|skip|withdraw)$/);
  if (taskActionMatch) {
    const [, rawTaskId, action] = taskActionMatch;
    return respond<TData>(updateTaskStatus(decodeURIComponent(rawTaskId), action), `task-${action}`);
  }

  const taskResultMatch = path.match(/^\/api\/v1\/tasks\/([^/]+)\/results$/);
  if (taskResultMatch) {
    const [, rawTaskId] = taskResultMatch;
    return respond<TData>(
      taskResultSubmission(decodeURIComponent(rawTaskId), body as TaskResultCreatePayload),
      "task-result",
    );
  }

  const reviewResultMatch = path.match(/^\/api\/v1\/reviews\/([^/]+)\/results$/);
  if (reviewResultMatch) {
    const [, rawScheduleId] = reviewResultMatch;
    return respond<TData>(
      reviewSubmission(decodeURIComponent(rawScheduleId), body as ReviewResultCreatePayload),
      "review-result",
    );
  }

  const wrongbookMatch = path.match(
    /^\/api\/v1\/wrongbook\/([^/]+)\/(variant-results|interval-results|analyze|confirm)$/,
  );
  if (wrongbookMatch) {
    const [, rawWrongRecordId, action] = wrongbookMatch;
    const wrongRecordId = decodeURIComponent(rawWrongRecordId);
    if (action === "analyze") {
      return respond<TData>(analyzeWrongbook(wrongRecordId), "wrongbook-analyze");
    }
    if (action === "confirm") {
      return respond<TData>(confirmWrongbook(wrongRecordId), "wrongbook-confirm");
    }
    return respond<TData>(
      wrongbookSubmission(
        wrongRecordId,
        action === "variant-results" ? "variant" : "interval_test",
        body as WrongbookAttemptResultCreatePayload,
        headers["Idempotency-Key"] ?? null,
      ),
      "wrongbook-result",
    );
  }

  if (path === "/api/v1/evidence/uploads") {
    return respond<TData>(uploadEvidence(body as EvidenceUploadCreatePayload), "evidence-upload");
  }

  const evidenceMatch = path.match(/^\/api\/v1\/evidence\/([^/]+)\/(analyze|confirm|reject)$/);
  if (evidenceMatch) {
    const [, rawRecordId, action] = evidenceMatch;
    const recordId = decodeURIComponent(rawRecordId);
    if (action === "analyze") {
      return respond<TData>(analyzeEvidence(recordId), "evidence-analyze");
    }
    if (action === "confirm") {
      return respond<TData>(confirmEvidence(recordId), "evidence-confirm");
    }
    return respond<TData>(rejectEvidence(recordId, body), "evidence-reject");
  }

  throw new Error(`Demo API route is not implemented: POST ${path}`);
}

function routeDemoPatch<TData>(path: string, body: unknown): ApiResponse<TData> {
  if (path === "/api/v1/settings/profile") {
    Object.assign(settingsProfile, body as SettingsProfileUpdatePayload, {
      updated_at: new Date().toISOString(),
    });
    return respond<TData>(settingsProfile, "settings-profile-update");
  }

  const goalMatch = path.match(/^\/api\/v1\/goals\/([^/]+)$/);
  if (goalMatch) {
    return respond<TData>(
      updateDemoGoal(decodeURIComponent(goalMatch[1]), body as GoalUpdatePayload),
      "goal-update",
    );
  }

  const taskMatch = path.match(/^\/api\/v1\/tasks\/([^/]+)$/);
  if (taskMatch) {
    const [, rawTaskId] = taskMatch;
    return respond<TData>(
      updateDemoTask(decodeURIComponent(rawTaskId), body as TaskUpdatePayload),
      "task-patch",
    );
  }

  const knowledgeMatch = path.match(/^\/api\/v1\/knowledge\/nodes\/([^/]+)$/);
  if (knowledgeMatch) {
    const nodeId = decodeURIComponent(knowledgeMatch[1]);
    const payload = body as KnowledgeNodeUpdatePayload;
    let updated: KnowledgeNodePayload | null = null;
    knowledgeNodes = {
      ...knowledgeNodes,
      items: knowledgeNodes.items.map((node) => {
        if (node.id !== nodeId) return node;
        updated = { ...node, ...payload, version: node.version + 1, updated_at: now };
        return updated;
      }),
    };
    if (!updated) throw new Error(`Demo knowledge node not found: ${nodeId}`);
    return respond<TData>(updated, "knowledge-node-update");
  }

  throw new Error(`Demo API route is not implemented: PATCH ${path}`);
}

function todayPayload(date: string): TodayPayload {
  return {
    date,
    tasks: demoTasks,
    total_tasks: demoTasks.length,
    estimated_minutes: demoTasks.reduce((total, task) => total + task.estimated_minutes, 0),
  };
}

function initialGoalTree(): GoalTreeListPayload {
  return {
    total: 1,
    items: [
      {
        id: "goal-semester",
        version: 1,
        parent_id: null,
        level: "semester",
        subject_id: null,
        title: "2026 考研总目标",
        description: "围绕数学一、英语一和 841 建立证据驱动闭环。",
        start_date: "2026-07-01",
        end_date: "2026-12-20",
        estimated_minutes: 36000,
        actual_minutes: 12840,
        completion_standard: "核心科目达到稳定掌握并完成模拟复盘。",
        progress: 36,
        risk_status: "slow",
        status: "active",
        adjustment_reason: "数学一错题变式通过率不足。",
        children: [
          {
            id: "goal-quarter",
            version: 1,
            parent_id: "goal-semester",
            level: "quarter",
            subject_id: "数学一",
            title: "强化阶段知识闭环",
            description: "高频模块完成闭卷回忆、变式和间隔复测。",
            start_date: "2026-07-01",
            end_date: "2026-09-30",
            estimated_minutes: 12000,
            actual_minutes: 4880,
            completion_standard: "薄弱节点低于 5 个。",
            progress: 41,
            risk_status: "normal",
            status: "active",
            adjustment_reason: null,
            children: [
              {
                id: "goal-month",
                version: 1,
                parent_id: "goal-quarter",
                level: "month",
                subject_id: "数学一",
                title: "7 月导数与级数补强",
                description: "把重复错因归档并完成无提示重做。",
                start_date: "2026-07-01",
                end_date: "2026-07-31",
                estimated_minutes: 4200,
                actual_minutes: 1760,
                completion_standard: "导数应用推进到阶段 4。",
                progress: 42,
                risk_status: "slow",
                status: "active",
                adjustment_reason: "导数应用存在参数讨论漏判。",
                children: [
                  {
                    id: "goal-week-math",
                    version: 1,
                    parent_id: "goal-month",
                    level: "week",
                    subject_id: "数学一",
                    title: "本周导数应用证据补齐",
                    description: "完成闭卷回忆、错题草稿确认和变式验证。",
                    start_date: "2026-07-13",
                    end_date: "2026-07-19",
                    estimated_minutes: 900,
                    actual_minutes: 560,
                    completion_standard: "至少 2 条独立证据。",
                    progress: 62,
                    risk_status: "slow",
                    status: "active",
                    adjustment_reason: "今日需先处理错题草稿。",
                    children: [
                      {
                        id: "goal-day",
                        version: 1,
                        parent_id: "goal-week-math",
                        level: "day",
                        subject_id: "数学一",
                        title: "今日闭环：任务、证据、错题",
                        description: "不排满时间，保留复盘和补救窗口。",
                        start_date: "2026-07-15",
                        end_date: "2026-07-15",
                        estimated_minutes: 125,
                        actual_minutes: 65,
                        completion_standard: "提交结果并确认草稿。",
                        progress: 52,
                        risk_status: "normal",
                        status: "active",
                        adjustment_reason: null,
                        children: [],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };
}

let demoGoals = initialGoalTree().items;

function goalTree(): GoalTreeListPayload {
  return { items: demoGoals, total: demoGoals.length };
}

function analyticsOverview(): AnalyticsOverviewPayload {
  return {
    knowledge_nodes: knowledgeNodes.total,
    goals: 5,
    tasks: demoTasks.length,
    task_results: 8,
    wrong_records: wrongRecords.length,
    mastery_snapshots: 24,
    average_goal_progress: 47,
    task_status: [
      { key: "pending", count: demoTasks.filter((task) => task.status === "pending").length },
      {
        key: "in_progress",
        count: demoTasks.filter((task) => task.status === "in_progress").length,
      },
      {
        key: "completed",
        count: demoTasks.filter((task) => task.status === "completed").length,
      },
    ],
    goal_risk: [
      { key: "normal", count: 3 },
      { key: "slow", count: 2 },
    ],
  };
}

function dueReviews(date: string): DueReviewListPayload {
  return {
    date,
    total: 1,
    items: [
      {
        knowledge_node_name: "导数应用",
        schedule: {
          id: "review-demo-1",
          version: 1,
          created_at: "2026-07-13T08:00:00Z",
          updated_at: "2026-07-13T08:00:00Z",
          knowledge_node_id: "node-derivative",
          subject_id: "数学一",
          current_stage: 3,
          status: "active",
          due_at: "2026-07-15T08:00:00Z",
          interval_days: 2,
          pass_streak: 0,
          fail_streak: 0,
          last_reviewed_at: null,
          last_result_id: null,
          source_snapshot_id: "snapshot-demo-1",
          rule_version: "review-v1.0.0",
          next_reason: "阶段 3 到期，需要独立时间点复习结果。",
        },
        candidate: {
          id: "review:review-demo-1",
          title: "复习：导数应用判定流程",
          subject_id: "数学一",
          estimated_minutes: 20,
          cognitive_load: "medium",
          source_type: "review_schedule",
          source_id: "review-demo-1",
          task_type: "review",
          review_due: 100,
          knowledge_importance: 95,
        },
      },
    ],
  };
}

function wrongbookCandidates(): WrongbookCandidateListPayload {
  return {
    total: 1,
    items: [
      {
        id: "wrong-candidate-1",
        title: "导数参数讨论错题验证",
        subject_id: "数学一",
        estimated_minutes: 25,
        cognitive_load: "medium",
        source_type: "wrong_record",
        source_id: "wrong-derivative-1",
        task_type: "wrongbook_variant",
        difficulty: "medium",
        review_due: 90,
        knowledge_importance: 95,
        weakness: 84,
        repeat_error: 67,
      },
    ],
  };
}

function evidenceHistory(limit: number): EvidenceHistoryPayload {
  const items = [...evidenceRecords]
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, limit)
    .map((record) => ({
      record,
      assets: [],
      draft:
        [...evidenceDrafts]
          .filter((draft) => draft.evidence_record_id === record.id)
          .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null,
    }));
  return { items, total: items.length };
}

function routeDemoDelete<TData>(path: string): ApiResponse<TData> {
  const assetMatch = path.match(/^\/api\/v1\/assets\/([^/]+)$/);
  if (assetMatch) {
    const assetId = decodeURIComponent(assetMatch[1]);
    const resource = resources.items.find((item) => item.asset.id === assetId);
    if (!resource) throw new Error(`Demo asset not found: ${assetId}`);
    resources = { items: resources.items.filter((item) => item.asset.id !== assetId), total: resources.total - 1 };
    demoAssetContent.delete(assetId);
    return respond<TData>({ ...resource.asset, state: "deleted" }, "asset-delete");
  }

  const knowledgeMatch = path.match(/^\/api\/v1\/knowledge\/nodes\/([^/]+)$/);
  if (knowledgeMatch) {
    const nodeId = decodeURIComponent(knowledgeMatch[1]);
    const node = knowledgeNodes.items.find((item) => item.id === nodeId);
    if (!node) throw new Error(`Demo knowledge node not found: ${nodeId}`);
    knowledgeNodes = { items: knowledgeNodes.items.filter((item) => item.id !== nodeId), total: knowledgeNodes.total - 1 };
    return respond<TData>({ ...node, is_deleted: true, deleted_at: now }, "knowledge-node-delete");
  }

  const taskMatch = path.match(/^\/api\/v1\/tasks\/([^/]+)$/);
  if (taskMatch) {
    const taskId = decodeURIComponent(taskMatch[1]);
    const task = demoTasks.find((item) => item.id === taskId);
    if (!task) {
      throw new Error(`Demo task not found: ${taskId}`);
    }
    demoTasks = demoTasks.filter((item) => item.id !== taskId);
    return respond<TData>({ ...task, status: "withdrawn" }, "task-delete");
  }

  const goalMatch = path.match(/^\/api\/v1\/goals\/([^/]+)$/);
  if (goalMatch) {
    const goalId = decodeURIComponent(goalMatch[1]);
    const removed = deleteDemoGoal(goalId);
    return respond<TData>({ ...removed, status: "cancelled" }, "goal-delete");
  }

  const evidenceMatch = path.match(/^\/api\/v1\/evidence\/([^/]+)$/);
  if (!evidenceMatch) {
    throw new Error(`Demo API route is not implemented: DELETE ${path}`);
  }
  const recordId = decodeURIComponent(evidenceMatch[1]);
  const record = evidenceRecordFor(recordId);
  if (record.status === "confirmed") {
    throw new Error("Confirmed demo evidence cannot be deleted");
  }
  evidenceRecords = evidenceRecords.filter((item) => item.id !== recordId);
  evidenceDrafts = evidenceDrafts.filter((item) => item.evidence_record_id !== recordId);
  return respond<TData>(
    { record_id: recordId, deleted_asset_ids: [], retained_asset_ids: [] },
    "evidence-delete",
  );
}

function wrongbookHistory(limit: number): WrongbookDraftHistoryPayload {
  const items = [...wrongRecords]
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, limit)
    .map((record) => ({
      record,
      verification: verificationFor(record.id),
      draft:
        [...wrongDrafts]
          .filter((draft) => draft.wrong_record_id === record.id)
          .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null,
    }));
  return { items, total: items.length };
}

function uploadEvidence(payload: EvidenceUploadCreatePayload): EvidenceUploadPayload {
  const recordId = `evidence-demo-${evidenceRecords.length + 1}`;
  const record: EvidenceRecordPayload = {
    id: recordId,
    version: 1,
    created_at: now,
    updated_at: now,
    created_by: "user",
    study_date: payload.study_date,
    subject_id: payload.subject_id ?? null,
    status: "pending",
    asset_count: payload.files.length,
    confirmed_facts: null,
    inferences: null,
    uncertain_fields: null,
    teaching_judgment: null,
    suggested_actions: null,
    confirmed_at: null,
    rejected_at: null,
  };
  evidenceRecords = [record, ...evidenceRecords];
  return {
    record,
    assets: payload.files.map((file, index) => evidenceAsset(recordId, file, index)),
  };
}

function evidenceAsset(recordId: string, file: EvidenceFileUploadPayload, index: number) {
  return {
    id: `${recordId}-asset-${index + 1}`,
    version: 1,
    created_at: now,
    updated_at: now,
    original_name: file.original_name,
    storage_path: `demo/${recordId}/${file.original_name}`,
    mime_type: file.mime_type,
    size_bytes: Math.max(24, Math.round(file.content_base64.length * 0.75)),
    state: "inbox" as const,
    reference_count: 1,
    page_order: index,
  };
}

function analyzeEvidence(recordId: string): EvidenceAnalyzePayload {
  const record = evidenceRecordFor(recordId);
  const draft: EvidenceDraftPayload = {
    id: `evidence-draft-${recordId}`,
    version: 1,
    created_at: now,
    updated_at: now,
    evidence_record_id: record.id,
    ai_job_id: `evidence-job-${record.id}`,
    status: "draft",
    schema_version: "evidence-analysis-v1",
    structured_json: {
      confirmed_facts: {
        asset_count: record.asset_count,
        subject: record.subject_id,
      },
      inferences: {
        likely_issue: "需要把输入证据转化成闭卷回忆或练习结果。",
      },
      teaching_judgment: {
        mastery_limit: "已接触",
        reason: "上传材料本身不能证明掌握。",
      },
      suggested_actions: [{ type: "confirm_or_reject", title: "确认后生成补救任务候选" }],
    },
    validation_errors: [],
    confirmed_at: null,
    rejected_at: null,
    rejection_reason: null,
    confirmed_once: false,
  };
  evidenceDrafts = [draft, ...evidenceDrafts.filter((item) => item.id !== draft.id)];
  return { draft, ai_job: evidenceJob(record.id, draft.structured_json) };
}

function confirmEvidence(recordId: string): EvidenceConfirmPayload {
  const record = evidenceRecordFor(recordId);
  const draft = latestEvidenceDraft(recordId);
  const updatedDraft: EvidenceDraftPayload = {
    ...draft,
    version: draft.version + 1,
    updated_at: now,
    status: "confirmed",
    confirmed_at: now,
    confirmed_once: true,
  };
  const updatedRecord: EvidenceRecordPayload = {
    ...record,
    version: record.version + 1,
    updated_at: now,
    status: "confirmed",
    confirmed_facts: draft.structured_json.confirmed_facts as Record<string, unknown>,
    inferences: draft.structured_json.inferences as Record<string, unknown>,
    uncertain_fields: [],
    teaching_judgment: draft.structured_json.teaching_judgment as Record<string, unknown>,
    suggested_actions: draft.structured_json.suggested_actions as Array<Record<string, unknown>>,
    confirmed_at: now,
  };
  evidenceDrafts = evidenceDrafts.map((item) => (item.id === draft.id ? updatedDraft : item));
  evidenceRecords = evidenceRecords.map((item) => (item.id === record.id ? updatedRecord : item));
  return { record: updatedRecord, draft: updatedDraft, created: true };
}

function rejectEvidence(recordId: string, body: unknown): EvidenceDraftPayload {
  const draft = latestEvidenceDraft(recordId);
  const reason = (body as { reason?: string }).reason ?? "用户要求重新整理证据";
  const updatedDraft: EvidenceDraftPayload = {
    ...draft,
    version: draft.version + 1,
    updated_at: now,
    status: "rejected",
    rejected_at: now,
    rejection_reason: reason,
  };
  evidenceDrafts = evidenceDrafts.map((item) => (item.id === draft.id ? updatedDraft : item));
  evidenceRecords = evidenceRecords.map((record) =>
    record.id === recordId
      ? { ...record, version: record.version + 1, updated_at: now, status: "rejected", rejected_at: now }
      : record,
  );
  return updatedDraft;
}

function analyzeWrongbook(wrongRecordId: string): WrongbookAnalyzePayload {
  const record = wrongRecordFor(wrongRecordId);
  const draft = maybeLatestWrongDraft(record.id);
  const nextDraft: WrongbookDraftPayload =
    draft ??
    {
      id: `wrong-draft-${record.id}`,
      version: 1,
      created_at: now,
      updated_at: now,
      wrong_record_id: record.id,
      ai_job_id: `wrong-job-${record.id}`,
      status: "draft",
      schema_version: "wrongbook-analysis-v1",
      structured_json: {
        surface_cause: "参数范围遗漏",
        deep_cause: "没有把端点和符号变化重新纳入判定。",
        prerequisite_gap: "导数符号表和极值条件",
        remediation_plan: [{ action: "redo_without_hints" }, { action: "variant" }],
        uncertain_fields: [],
      },
      validation_errors: [],
      confirmed_at: null,
      confirmed_once: false,
    };
  wrongDrafts = [nextDraft, ...wrongDrafts.filter((item) => item.id !== nextDraft.id)];
  return { draft: nextDraft, ai_job: wrongbookJob(record.id, nextDraft.structured_json) };
}

function confirmWrongbook(wrongRecordId: string): WrongbookConfirmPayload {
  const record = wrongRecordFor(wrongRecordId);
  const draft = latestWrongDraft(record.id);
  const updatedDraft: WrongbookDraftPayload = {
    ...draft,
    version: draft.version + 1,
    updated_at: now,
    status: "confirmed",
    confirmed_at: now,
    confirmed_once: true,
  };
  const updatedRecord: WrongbookRecordPayload = {
    ...record,
    version: record.version + 1,
    updated_at: now,
    surface_cause: stringField(draft.structured_json.surface_cause),
    deep_cause: stringField(draft.structured_json.deep_cause),
    prerequisite_gap: stringField(draft.structured_json.prerequisite_gap),
    current_status: "pending_no_hint_redo",
  };
  wrongDrafts = wrongDrafts.map((item) => (item.id === draft.id ? updatedDraft : item));
  wrongRecords = wrongRecords.map((item) => (item.id === record.id ? updatedRecord : item));
  return { record: updatedRecord, draft: updatedDraft, created: true };
}

function wrongbookSubmission(
  wrongRecordId: string,
  attemptType: "variant" | "interval_test",
  payload: WrongbookAttemptResultCreatePayload,
  idempotencyKey: string | null,
): WrongbookAttemptSubmitPayload {
  const record = wrongRecordFor(wrongRecordId);
  const verification = verificationFor(wrongRecordId);
  const attemptId = `attempt-${attemptType}-${payload.is_correct ? "pass" : "fail"}`;
  const attempt = {
    id: attemptId,
    version: 1,
    created_at: now,
    updated_at: now,
    created_by: "user",
    question_id: record.question_id,
    wrong_record_id: record.id,
    idempotency_key: idempotencyKey,
    attempt_type: attemptType,
    attempted_at: payload.attempted_at ?? now,
    answer_text: payload.answer_text ?? null,
    is_correct: payload.is_correct,
    score: payload.score ?? null,
    duration_seconds: payload.duration_seconds ?? null,
    hint_level: payload.hint_level ?? null,
    confidence: payload.confidence ?? null,
    request_id: "demo-wrongbook-result",
  } satisfies WrongbookAttemptSubmitPayload["attempt"];
  const updatedVerification: WrongbookVerificationPayload = {
    ...verification,
    version: verification.version + 1,
    updated_at: now,
    variant_passed:
      attemptType === "variant" ? payload.is_correct : verification.variant_passed && payload.is_correct,
    interval_test_passed:
      attemptType === "interval_test" ? payload.is_correct : verification.interval_test_passed,
    last_attempt_id: attempt.id,
  };
  const updatedRecord: WrongbookRecordPayload = {
    ...record,
    version: record.version + 1,
    updated_at: now,
    error_count: payload.is_correct ? record.error_count : record.error_count + 1,
    redo_count: record.redo_count + 1,
    current_status: nextWrongStatus(attemptType, payload.is_correct),
    next_review_at:
      attemptType === "variant" && payload.is_correct ? "2026-07-18T09:00:00Z" : record.next_review_at,
    resolved_at:
      attemptType === "interval_test" && payload.is_correct ? "2026-07-20T09:00:00Z" : record.resolved_at,
  };
  wrongRecords = wrongRecords.map((item) => (item.id === record.id ? updatedRecord : item));
  wrongVerifications = wrongVerifications.map((item) =>
    item.id === verification.id ? updatedVerification : item,
  );
  return {
    attempt,
    record: updatedRecord,
    verification: updatedVerification,
    created: true,
  };
}

function reviewSubmission(
  scheduleId: string,
  payload: ReviewResultCreatePayload,
): ReviewResultSubmitPayload {
  const passed = payload.result_type === "pass";
  const schedule = dueReviews("2026-07-15").items.find((item) => item.schedule.id === scheduleId)?.schedule;
  if (!schedule) {
    throw new Error(`Demo review schedule not found: ${scheduleId}`);
  }
  const updatedSchedule = {
    ...schedule,
    version: schedule.version + 1,
    updated_at: now,
    due_at: passed ? "2026-07-21T09:00:00Z" : tomorrow,
    interval_days: passed ? 6 : 1,
    pass_streak: passed ? schedule.pass_streak + 1 : 0,
    fail_streak: passed ? 0 : schedule.fail_streak + 1,
    last_reviewed_at: now,
    last_result_id: `review-result-${scheduleId}`,
    next_reason: passed ? "passed_independent_review:1" : "failed_review:rollback_and_short_interval",
  };
  return {
    result: {
      id: `review-result-${scheduleId}`,
      version: 1,
      created_at: now,
      updated_at: now,
      schedule_id: schedule.id,
      knowledge_node_id: schedule.knowledge_node_id,
      result_type: payload.result_type,
      score: payload.score ?? null,
      sample_count: payload.sample_count ?? 0,
      correct_count: payload.correct_count ?? null,
      accuracy: payload.accuracy ?? null,
      occurred_at: payload.occurred_at ?? now,
      independent_timepoint: true,
      evidence_id: passed ? "evidence-demo-1" : null,
      snapshot_id: passed ? "snapshot-demo-2" : null,
    },
    schedule: updatedSchedule,
    created: true,
    evaluation_new_stage: passed ? schedule.current_stage : Math.max(1, schedule.current_stage - 1),
    evaluation_reason: passed ? "review_passed" : "review_failed_rollback",
    rule_version: "review-v1.0.0",
  };
}

function taskResultSubmission(
  taskId: string,
  payload: TaskResultCreatePayload,
): TaskResultSubmitPayload {
  return {
    result: {
      id: `task-result-${taskId}`,
      version: 1,
      created_at: now,
      updated_at: now,
      task_id: taskId,
      result_type: payload.result_type,
      completion_ratio: payload.completion_ratio,
      actual_minutes: payload.actual_minutes,
      question_count: payload.question_count ?? null,
      correct_count: payload.correct_count ?? null,
      accuracy: payload.accuracy ?? null,
      confidence: payload.confidence ?? null,
      hint_level: payload.hint_level ?? null,
      focus_level: payload.focus_level ?? null,
      difficulty_rating: payload.difficulty_rating ?? null,
      problem_description: payload.problem_description ?? null,
      confirmed_at: payload.confirmed_at ?? now,
    },
    created: true,
  };
}

function updateTaskStatus(taskId: string, action: string): TaskPayload {
  const statusByAction: Record<string, TaskPayload["status"]> = {
    start: "in_progress",
    skip: "skipped",
    withdraw: "withdrawn",
  };
  return setTaskStatus(taskId, statusByAction[action] ?? "pending");
}

function createDemoTask(payload: TaskCreatePayload): TaskPayload {
  const task: TaskPayload = {
    id: `demo-task-${++demoSequence}`,
    version: 1,
    goal_id: payload.goal_id ?? null,
    subject_id: payload.subject_id ?? null,
    knowledge_node_id: payload.knowledge_node_id ?? null,
    title: payload.title,
    task_type: payload.task_type ?? "study",
    priority: payload.priority ?? "normal",
    source_type: payload.source_type,
    source_id: payload.source_id ?? null,
    planned_date: payload.planned_date,
    estimated_minutes: payload.estimated_minutes,
    current_stage: null,
    target_stage: null,
    reason: payload.reason ?? null,
    completion_standard: payload.completion_standard ?? null,
    prerequisite_status: payload.prerequisite_status ?? "unknown",
    status: "pending",
  };
  demoTasks = [...demoTasks, task];
  return task;
}

function updateDemoTask(taskId: string, payload: TaskUpdatePayload): TaskPayload {
  let updated: TaskPayload | null = null;
  demoTasks = demoTasks.map((task) => {
    if (task.id !== taskId) return task;
    updated = { ...task, ...payload, version: task.version + 1 };
    return updated;
  });
  if (!updated) throw new Error(`Demo task not found: ${taskId}`);
  return updated;
}

function createDemoGoal(payload: GoalCreatePayload): GoalPayload {
  const goal: GoalTreePayload = {
    id: `demo-goal-${++demoSequence}`,
    version: 1,
    parent_id: payload.parent_id ?? null,
    level: payload.level,
    subject_id: payload.subject_id ?? null,
    title: payload.title,
    description: payload.description ?? null,
    start_date: payload.start_date ?? null,
    end_date: payload.end_date ?? null,
    estimated_minutes: payload.estimated_minutes ?? 0,
    actual_minutes: 0,
    completion_standard: payload.completion_standard ?? null,
    progress: 0,
    risk_status: "normal",
    status: "active",
    adjustment_reason: null,
    children: [],
  };
  if (!goal.parent_id || !appendDemoGoal(demoGoals, goal.parent_id, goal)) {
    demoGoals = [...demoGoals, goal];
  }
  return goal;
}

function appendDemoGoal(
  goals: GoalTreePayload[],
  parentId: string,
  child: GoalTreePayload,
): boolean {
  for (const goal of goals) {
    if (goal.id === parentId) {
      goal.children = [...goal.children, child];
      return true;
    }
    if (appendDemoGoal(goal.children, parentId, child)) return true;
  }
  return false;
}

function updateDemoGoal(goalId: string, payload: GoalUpdatePayload): GoalPayload {
  const goal = findDemoGoal(demoGoals, goalId);
  if (!goal) throw new Error(`Demo goal not found: ${goalId}`);
  Object.assign(goal, payload, { version: goal.version + 1 });
  return goal;
}

function findDemoGoal(goals: GoalTreePayload[], goalId: string): GoalTreePayload | null {
  for (const goal of goals) {
    if (goal.id === goalId) return goal;
    const nested = findDemoGoal(goal.children, goalId);
    if (nested) return nested;
  }
  return null;
}

function deleteDemoGoal(goalId: string): GoalTreePayload {
  const removed = findDemoGoal(demoGoals, goalId);
  if (!removed) throw new Error(`Demo goal not found: ${goalId}`);
  const removedIds = new Set(flattenDemoGoalIds(removed));
  demoGoals = removeDemoGoal(demoGoals, goalId);
  demoTasks = demoTasks.filter((task) => !task.goal_id || !removedIds.has(task.goal_id));
  return removed;
}

function removeDemoGoal(goals: GoalTreePayload[], goalId: string): GoalTreePayload[] {
  return goals
    .filter((goal) => goal.id !== goalId)
    .map((goal) => ({ ...goal, children: removeDemoGoal(goal.children, goalId) }));
}

function flattenDemoGoalIds(goal: GoalTreePayload): string[] {
  return [goal.id, ...goal.children.flatMap(flattenDemoGoalIds)];
}

function setTaskStatus(taskId: string, status: TaskPayload["status"]): TaskPayload {
  let updated: TaskPayload | null = null;
  demoTasks = demoTasks.map((task) => {
    if (task.id !== taskId) {
      return task;
    }
    updated = { ...task, version: task.version + 1, status };
    return updated;
  });
  if (!updated) {
    throw new Error(`Demo task not found: ${taskId}`);
  }
  return updated;
}

function evidenceRecordFor(recordId: string): EvidenceRecordPayload {
  const record = evidenceRecords.find((item) => item.id === recordId);
  if (!record) {
    throw new Error(`Demo evidence record not found: ${recordId}`);
  }
  return record;
}

function latestEvidenceDraft(recordId: string): EvidenceDraftPayload {
  const draft = evidenceDrafts
    .filter((item) => item.evidence_record_id === recordId)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];
  if (!draft) {
    throw new Error(`Demo evidence draft not found: ${recordId}`);
  }
  return draft;
}

function wrongRecordFor(wrongRecordId: string): WrongbookRecordPayload {
  const record = wrongRecords.find((item) => item.id === wrongRecordId);
  if (!record) {
    throw new Error(`Demo wrongbook record not found: ${wrongRecordId}`);
  }
  return record;
}

function verificationFor(wrongRecordId: string): WrongbookVerificationPayload {
  const verification = wrongVerifications.find((item) => item.wrong_record_id === wrongRecordId);
  if (!verification) {
    throw new Error(`Demo wrongbook verification not found: ${wrongRecordId}`);
  }
  return verification;
}

function latestWrongDraft(wrongRecordId: string): WrongbookDraftPayload {
  const draft = maybeLatestWrongDraft(wrongRecordId);
  if (!draft) {
    throw new Error(`Demo wrongbook draft not found: ${wrongRecordId}`);
  }
  return draft;
}

function maybeLatestWrongDraft(wrongRecordId: string): WrongbookDraftPayload | null {
  const draft = wrongDrafts
    .filter((item) => item.wrong_record_id === wrongRecordId)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];
  return draft ?? null;
}

function evidenceJob(recordId: string, output: Record<string, unknown>): EvidenceAIJobPayload {
  return {
    id: `evidence-job-${recordId}`,
    version: 1,
    created_at: now,
    updated_at: now,
    job_type: "evidence_analysis",
    provider: "demo",
    model_name: "demo-rule-provider",
    prompt_version: "evidence-demo-v1",
    status: "succeeded",
    attempts: 1,
    input_json: { evidence_record_id: recordId },
    output_json: output,
    error_code: null,
    error_message: null,
    started_at: now,
    completed_at: now,
  };
}

function wrongbookJob(wrongRecordId: string, output: Record<string, unknown>): WrongbookAIJobPayload {
  return {
    id: `wrong-job-${wrongRecordId}`,
    version: 1,
    created_at: now,
    updated_at: now,
    job_type: "wrongbook_analysis",
    provider: "demo",
    model_name: "demo-rule-provider",
    prompt_version: "wrongbook-demo-v1",
    status: "succeeded",
    attempts: 1,
    input_json: { wrong_record_id: wrongRecordId },
    output_json: output,
    error_code: null,
    error_message: null,
    started_at: now,
    completed_at: now,
  };
}

function nextWrongStatus(
  attemptType: "variant" | "interval_test",
  passed: boolean,
): WrongbookRecordPayload["current_status"] {
  if (!passed) {
    return "regressed";
  }
  return attemptType === "variant" ? "pending_interval" : "stable_corrected";
}

function countWrongStatus(status: WrongbookRecordPayload["current_status"]): number {
  return wrongRecords.filter((record) => record.current_status === status).length;
}

function stringField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function limitParam(params: URLSearchParams): number {
  const parsed = Number(params.get("limit") ?? "20");
  return Number.isFinite(parsed) ? Math.max(1, Math.min(100, Math.round(parsed))) : 20;
}

function respond<TData>(data: unknown, requestId: string): ApiResponse<TData> {
  return {
    data: clone(data) as TData,
    meta: { request_id: `demo-${requestId}` },
  };
}

function clone<TValue>(value: TValue): TValue {
  return JSON.parse(JSON.stringify(value)) as TValue;
}
