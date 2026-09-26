import type {
  ApiErrorBody,
  ApiErrorResponse,
  ApiMetaPayload,
  ApiResponse,
  AssetContentPayload,
  AuthStatusPayload,
  AnalyticsErrorsPayload,
  AnalyticsGoalRiskPayload,
  AnalyticsMasteryPayload,
  AnalyticsOverviewPayload,
  AnalyticsTimePayload,
  AssetPayload,
  AssetUploadCreatePayload,
  DueReviewListPayload,
  EvidenceAnalyzeCreatePayload,
  EvidenceAnalyzePayload,
  EvidenceConfirmPayload,
  EvidenceDeletePayload,
  EvidenceDraftPayload,
  EvidenceHistoryPayload,
  EvidenceRejectCreatePayload,
  EvidenceUploadCreatePayload,
  EvidenceUploadPayload,
  GoalTreeListPayload,
  GoalCreatePayload,
  GoalPayload,
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
  TaskPayload,
  TaskCreatePayload,
  TaskListPayload,
  TaskUpdatePayload,
  TaskResultCreatePayload,
  TaskResultSubmitPayload,
  TodayPayload,
  WeakGraphPayload,
  WrongbookAttemptResultCreatePayload,
  WrongbookAttemptSubmitPayload,
  WrongbookAnalyzeCreatePayload,
  WrongbookAnalyzePayload,
  WrongbookCandidateListPayload,
  WrongbookConfirmPayload,
  WrongbookDraftHistoryPayload,
} from "./contracts";
import { demoApiRequest, isDemoApiEnabled } from "./demoClient";
import { getPersonalAccessKey } from "./auth";

export class ApiClientError extends Error {
  constructor(
    readonly status: number,
    readonly error: ApiErrorBody,
  ) {
    super(error.message);
    this.name = "ApiClientError";
  }
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function configuredApiBaseUrl(): string {
  const rawBaseUrl = String(import.meta.env.VITE_YANTU_API_BASE_URL ?? "").trim();
  if (!rawBaseUrl) {
    return "";
  }

  const parsed = new URL(rawBaseUrl);
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error("VITE_YANTU_API_BASE_URL must be an HTTP(S) URL without credentials");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("VITE_YANTU_API_BASE_URL must not include a path, query, or fragment");
  }
  return parsed.origin;
}

export class ApiClient {
  constructor(
    private readonly baseUrl = configuredApiBaseUrl(),
    private readonly fetcher: FetchLike = fetch,
  ) {}

  health(): Promise<ApiResponse<HealthPayload>> {
    return this.get<HealthPayload>("/health");
  }

  meta(): Promise<ApiResponse<ApiMetaPayload>> {
    return this.get<ApiMetaPayload>("/api/v1/meta");
  }

  authStatus(): Promise<ApiResponse<AuthStatusPayload>> {
    return this.get<AuthStatusPayload>("/api/v1/auth/status");
  }

  today(date: string): Promise<ApiResponse<TodayPayload>> {
    return this.get<TodayPayload>(`/api/v1/today?date=${encodeURIComponent(date)}`);
  }

  goalsTree(): Promise<ApiResponse<GoalTreeListPayload>> {
    return this.get<GoalTreeListPayload>("/api/v1/goals/tree");
  }

  tasks(): Promise<ApiResponse<TaskListPayload>> {
    return this.get<TaskListPayload>("/api/v1/tasks");
  }

  settingsProfile(): Promise<ApiResponse<SettingsProfilePayload>> {
    return this.get<SettingsProfilePayload>("/api/v1/settings/profile");
  }

  updateSettingsProfile(
    payload: SettingsProfileUpdatePayload,
  ): Promise<ApiResponse<SettingsProfilePayload>> {
    return this.patch<SettingsProfilePayload, SettingsProfileUpdatePayload>(
      "/api/v1/settings/profile",
      payload,
    );
  }

  createGoal(payload: GoalCreatePayload): Promise<ApiResponse<GoalPayload>> {
    return this.post<GoalPayload, GoalCreatePayload>("/api/v1/goals", payload);
  }

  updateGoal(
    goalId: string,
    version: number,
    payload: GoalUpdatePayload,
  ): Promise<ApiResponse<GoalPayload>> {
    return this.patch<GoalPayload, GoalUpdatePayload>(
      `/api/v1/goals/${encodeURIComponent(goalId)}`,
      payload,
      { "If-Match": String(version) },
    );
  }

  deleteGoal(goalId: string): Promise<ApiResponse<GoalPayload>> {
    return this.delete<GoalPayload>(`/api/v1/goals/${encodeURIComponent(goalId)}`);
  }

  createTask(payload: TaskCreatePayload): Promise<ApiResponse<TaskPayload>> {
    return this.post<TaskPayload, TaskCreatePayload>("/api/v1/tasks", payload);
  }

  updateTask(
    taskId: string,
    version: number,
    payload: TaskUpdatePayload,
  ): Promise<ApiResponse<TaskPayload>> {
    return this.patch<TaskPayload, TaskUpdatePayload>(
      `/api/v1/tasks/${encodeURIComponent(taskId)}`,
      payload,
      { "If-Match": String(version) },
    );
  }

  deleteTask(taskId: string): Promise<ApiResponse<TaskPayload>> {
    return this.delete<TaskPayload>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
  }

  settingsRules(): Promise<ApiResponse<SettingsRulesPayload>> {
    return this.get<SettingsRulesPayload>("/api/v1/settings/rules");
  }

  analyticsOverview(): Promise<ApiResponse<AnalyticsOverviewPayload>> {
    return this.get<AnalyticsOverviewPayload>("/api/v1/analytics/overview");
  }

  analyticsTime(): Promise<ApiResponse<AnalyticsTimePayload>> {
    return this.get<AnalyticsTimePayload>("/api/v1/analytics/time");
  }

  analyticsErrors(): Promise<ApiResponse<AnalyticsErrorsPayload>> {
    return this.get<AnalyticsErrorsPayload>("/api/v1/analytics/errors");
  }

  analyticsMastery(): Promise<ApiResponse<AnalyticsMasteryPayload>> {
    return this.get<AnalyticsMasteryPayload>("/api/v1/analytics/mastery");
  }

  analyticsGoalRisk(): Promise<ApiResponse<AnalyticsGoalRiskPayload>> {
    return this.get<AnalyticsGoalRiskPayload>("/api/v1/analytics/goal-risk");
  }

  weakGraph(): Promise<ApiResponse<WeakGraphPayload>> {
    return this.get<WeakGraphPayload>("/api/v1/graph/weak");
  }

  resources(): Promise<ApiResponse<ResourceListPayload>> {
    return this.get<ResourceListPayload>("/api/v1/resources");
  }

  uploadAsset(payload: AssetUploadCreatePayload): Promise<ApiResponse<AssetPayload>> {
    return this.post<AssetPayload, AssetUploadCreatePayload>("/api/v1/assets", payload);
  }

  createResource(payload: ResourceCreatePayload): Promise<ApiResponse<ResourcePayload>> {
    return this.post<ResourcePayload, ResourceCreatePayload>("/api/v1/resources", payload);
  }

  deleteAsset(assetId: string): Promise<ApiResponse<AssetPayload>> {
    return this.delete<AssetPayload>(`/api/v1/assets/${encodeURIComponent(assetId)}`);
  }

  knowledgeNodes(): Promise<ApiResponse<KnowledgeNodeListPayload>> {
    return this.get<KnowledgeNodeListPayload>("/api/v1/knowledge/nodes");
  }

  createKnowledgeNode(
    payload: KnowledgeNodeCreatePayload,
  ): Promise<ApiResponse<KnowledgeNodePayload>> {
    return this.post<KnowledgeNodePayload, KnowledgeNodeCreatePayload>(
      "/api/v1/knowledge/nodes",
      payload,
    );
  }

  updateKnowledgeNode(
    nodeId: string,
    payload: KnowledgeNodeUpdatePayload,
  ): Promise<ApiResponse<KnowledgeNodePayload>> {
    return this.patch<KnowledgeNodePayload, KnowledgeNodeUpdatePayload>(
      `/api/v1/knowledge/nodes/${encodeURIComponent(nodeId)}`,
      payload,
    );
  }

  deleteKnowledgeNode(nodeId: string): Promise<ApiResponse<KnowledgeNodePayload>> {
    return this.delete<KnowledgeNodePayload>(
      `/api/v1/knowledge/nodes/${encodeURIComponent(nodeId)}`,
    );
  }

  wrongbookPlanningCandidates(): Promise<ApiResponse<WrongbookCandidateListPayload>> {
    return this.get<WrongbookCandidateListPayload>("/api/v1/wrongbook/planning-candidates");
  }

  wrongbookDraftHistory(limit = 20): Promise<ApiResponse<WrongbookDraftHistoryPayload>> {
    return this.get<WrongbookDraftHistoryPayload>(`/api/v1/wrongbook/history?limit=${limit}`);
  }

  analyzeWrongbookRecord(
    wrongRecordId: string,
    payload: WrongbookAnalyzeCreatePayload = {},
  ): Promise<ApiResponse<WrongbookAnalyzePayload>> {
    return this.post<WrongbookAnalyzePayload>(
      `/api/v1/wrongbook/${encodeURIComponent(wrongRecordId)}/analyze`,
      payload,
    );
  }

  confirmWrongbookDraft(wrongRecordId: string): Promise<ApiResponse<WrongbookConfirmPayload>> {
    return this.post<WrongbookConfirmPayload>(
      `/api/v1/wrongbook/${encodeURIComponent(wrongRecordId)}/confirm`,
    );
  }

  submitWrongbookVariantResult(
    wrongRecordId: string,
    payload: WrongbookAttemptResultCreatePayload,
    idempotencyKey: string,
  ): Promise<ApiResponse<WrongbookAttemptSubmitPayload>> {
    return this.post<WrongbookAttemptSubmitPayload>(
      `/api/v1/wrongbook/${encodeURIComponent(wrongRecordId)}/variant-results`,
      payload,
      {
        "Idempotency-Key": idempotencyKey,
      },
    );
  }

  submitWrongbookIntervalResult(
    wrongRecordId: string,
    payload: WrongbookAttemptResultCreatePayload,
    idempotencyKey: string,
  ): Promise<ApiResponse<WrongbookAttemptSubmitPayload>> {
    return this.post<WrongbookAttemptSubmitPayload>(
      `/api/v1/wrongbook/${encodeURIComponent(wrongRecordId)}/interval-results`,
      payload,
      {
        "Idempotency-Key": idempotencyKey,
      },
    );
  }

  dueReviews(date: string): Promise<ApiResponse<DueReviewListPayload>> {
    return this.get<DueReviewListPayload>(`/api/v1/reviews/due?date=${encodeURIComponent(date)}`);
  }

  submitReviewResult(
    scheduleId: string,
    payload: ReviewResultCreatePayload,
    idempotencyKey: string,
  ): Promise<ApiResponse<ReviewResultSubmitPayload>> {
    return this.post<ReviewResultSubmitPayload>(
      `/api/v1/reviews/${encodeURIComponent(scheduleId)}/results`,
      payload,
      {
        "Idempotency-Key": idempotencyKey,
      },
    );
  }

  uploadEvidence(
    payload: EvidenceUploadCreatePayload,
  ): Promise<ApiResponse<EvidenceUploadPayload>> {
    return this.post<EvidenceUploadPayload>("/api/v1/evidence/uploads", payload);
  }

  evidenceHistory(limit = 20): Promise<ApiResponse<EvidenceHistoryPayload>> {
    return this.get<EvidenceHistoryPayload>(`/api/v1/evidence/history?limit=${limit}`);
  }

  evidenceAssetContent(assetId: string): Promise<ApiResponse<AssetContentPayload>> {
    return this.get<AssetContentPayload>(
      `/api/v1/assets/${encodeURIComponent(assetId)}/content`,
    );
  }

  deleteEvidence(recordId: string): Promise<ApiResponse<EvidenceDeletePayload>> {
    return this.delete<EvidenceDeletePayload>(
      `/api/v1/evidence/${encodeURIComponent(recordId)}`,
    );
  }

  analyzeEvidence(
    recordId: string,
    payload: EvidenceAnalyzeCreatePayload = {},
  ): Promise<ApiResponse<EvidenceAnalyzePayload>> {
    return this.post<EvidenceAnalyzePayload>(
      `/api/v1/evidence/${encodeURIComponent(recordId)}/analyze`,
      payload,
    );
  }

  confirmEvidenceDraft(recordId: string): Promise<ApiResponse<EvidenceConfirmPayload>> {
    return this.post<EvidenceConfirmPayload>(
      `/api/v1/evidence/${encodeURIComponent(recordId)}/confirm`,
    );
  }

  rejectEvidenceDraft(
    recordId: string,
    payload: EvidenceRejectCreatePayload,
  ): Promise<ApiResponse<EvidenceDraftPayload>> {
    return this.post<EvidenceDraftPayload>(
      `/api/v1/evidence/${encodeURIComponent(recordId)}/reject`,
      payload,
    );
  }

  startTask(taskId: string, version: number): Promise<ApiResponse<TaskPayload>> {
    return this.post<TaskPayload>(`/api/v1/tasks/${encodeURIComponent(taskId)}/start`, undefined, {
      "If-Match": String(version),
    });
  }

  skipTask(taskId: string, version: number): Promise<ApiResponse<TaskPayload>> {
    return this.post<TaskPayload>(`/api/v1/tasks/${encodeURIComponent(taskId)}/skip`, undefined, {
      "If-Match": String(version),
    });
  }

  withdrawTask(taskId: string, version: number): Promise<ApiResponse<TaskPayload>> {
    return this.post<TaskPayload>(
      `/api/v1/tasks/${encodeURIComponent(taskId)}/withdraw`,
      undefined,
      {
        "If-Match": String(version),
      },
    );
  }

  completeTask(taskId: string, version: number): Promise<ApiResponse<TaskPayload>> {
    return this.patch<TaskPayload, { status: TaskPayload["status"] }>(
      `/api/v1/tasks/${encodeURIComponent(taskId)}`,
      { status: "completed" },
      {
        "If-Match": String(version),
      },
    );
  }

  submitTaskResult(
    taskId: string,
    payload: TaskResultCreatePayload,
    idempotencyKey: string,
  ): Promise<ApiResponse<TaskResultSubmitPayload>> {
    return this.post<TaskResultSubmitPayload>(
      `/api/v1/tasks/${encodeURIComponent(taskId)}/results`,
      payload,
      {
        "Idempotency-Key": idempotencyKey,
      },
    );
  }

  private async get<TData>(path: string): Promise<ApiResponse<TData>> {
    if (this.shouldUseDemoApi()) {
      return demoApiRequest<TData>({ method: "GET", path });
    }
    const response = await this.fetcher.call(globalThis, this.url(path), {
      headers: {
        Accept: "application/json",
        ...this.authHeaders(),
      },
    });
    let body: ApiResponse<TData> | ApiErrorResponse;
    try {
      body = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;
    } catch (error) {
      if (!response.ok) {
        throw new ApiClientError(response.status, {
          code: "HTTP_ERROR",
          message: `Request failed with status ${response.status}`,
          details: null,
          request_id: response.headers.get("x-request-id") ?? "unavailable",
        });
      }
      throw error;
    }

    if (!response.ok) {
      const errorBody = body as ApiErrorResponse;
      throw new ApiClientError(response.status, errorBody.error);
    }

    return body as ApiResponse<TData>;
  }

  private async post<TData, TBody = unknown>(
    path: string,
    body?: TBody,
    headers: Record<string, string> = {},
  ): Promise<ApiResponse<TData>> {
    if (this.shouldUseDemoApi()) {
      return demoApiRequest<TData>({ method: "POST", path, body, headers });
    }
    const requestHeaders: Record<string, string> = {
      Accept: "application/json",
      ...this.authHeaders(),
      ...headers,
    };
    const init: RequestInit = {
      method: "POST",
      headers: requestHeaders,
    };
    if (body !== undefined) {
      requestHeaders["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await this.fetcher.call(globalThis, this.url(path), init);
    const responseBody = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;

    if (!response.ok) {
      const errorBody = responseBody as ApiErrorResponse;
      throw new ApiClientError(response.status, errorBody.error);
    }

    return responseBody as ApiResponse<TData>;
  }

  private async delete<TData>(path: string): Promise<ApiResponse<TData>> {
    if (this.shouldUseDemoApi()) {
      return demoApiRequest<TData>({ method: "DELETE", path });
    }
    const response = await this.fetcher.call(globalThis, this.url(path), {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        ...this.authHeaders(),
      },
    });
    const responseBody = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;

    if (!response.ok) {
      const errorBody = responseBody as ApiErrorResponse;
      throw new ApiClientError(response.status, errorBody.error);
    }

    return responseBody as ApiResponse<TData>;
  }

  private async patch<TData, TBody>(
    path: string,
    body: TBody,
    headers: Record<string, string> = {},
  ): Promise<ApiResponse<TData>> {
    return this.sendJson<TData, TBody>("PATCH", path, body, headers);
  }

  private async sendJson<TData, TBody>(
    method: "PATCH",
    path: string,
    body: TBody,
    headers: Record<string, string>,
  ): Promise<ApiResponse<TData>> {
    if (this.shouldUseDemoApi()) {
      return demoApiRequest<TData>({ method, path, body, headers });
    }
    const response = await this.fetcher.call(globalThis, this.url(path), {
      method,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...this.authHeaders(),
        ...headers,
      },
      body: JSON.stringify(body),
    });
    const responseBody = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;

    if (!response.ok) {
      const errorBody = responseBody as ApiErrorResponse;
      throw new ApiClientError(response.status, errorBody.error);
    }

    return responseBody as ApiResponse<TData>;
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private shouldUseDemoApi(): boolean {
    return this.baseUrl === "" && this.fetcher === fetch && isDemoApiEnabled();
  }

  private authHeaders(): Record<string, string> {
    const accessKey = getPersonalAccessKey();
    return accessKey ? { Authorization: `Bearer ${accessKey}` } : {};
  }
}
