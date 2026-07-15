import type {
  ApiErrorBody,
  ApiErrorResponse,
  ApiMetaPayload,
  ApiResponse,
  AnalyticsErrorsPayload,
  AnalyticsGoalRiskPayload,
  AnalyticsMasteryPayload,
  AnalyticsOverviewPayload,
  AnalyticsTimePayload,
  DueReviewListPayload,
  EvidenceAnalyzeCreatePayload,
  EvidenceAnalyzePayload,
  EvidenceConfirmPayload,
  EvidenceDraftPayload,
  EvidenceHistoryPayload,
  EvidenceRejectCreatePayload,
  EvidenceUploadCreatePayload,
  EvidenceUploadPayload,
  GoalTreeListPayload,
  HealthPayload,
  KnowledgeNodeListPayload,
  ResourceListPayload,
  ReviewResultCreatePayload,
  ReviewResultSubmitPayload,
  SettingsProfilePayload,
  SettingsRulesPayload,
  TaskPayload,
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

  today(date: string): Promise<ApiResponse<TodayPayload>> {
    return this.get<TodayPayload>(`/api/v1/today?date=${encodeURIComponent(date)}`);
  }

  goalsTree(): Promise<ApiResponse<GoalTreeListPayload>> {
    return this.get<GoalTreeListPayload>("/api/v1/goals/tree");
  }

  settingsProfile(): Promise<ApiResponse<SettingsProfilePayload>> {
    return this.get<SettingsProfilePayload>("/api/v1/settings/profile");
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

  knowledgeNodes(): Promise<ApiResponse<KnowledgeNodeListPayload>> {
    return this.get<KnowledgeNodeListPayload>("/api/v1/knowledge/nodes");
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
    const response = await this.fetcher(this.url(path), {
      headers: {
        Accept: "application/json",
      },
    });
    const body = (await response.json()) as ApiResponse<TData> | ApiErrorResponse;

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
    const response = await this.fetcher(this.url(path), init);
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
    const response = await this.fetcher(this.url(path), {
      method,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
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
}
