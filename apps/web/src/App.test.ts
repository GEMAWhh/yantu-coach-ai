import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import { primaryNavItems } from "./app/navigation";
import { createAppRouter } from "./router";

async function mountApp(path = "/today") {
  const router = createAppRouter(createMemoryHistory());
  await router.push(path);
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [createPinia(), router],
    },
  });

  await flushPromises();
  return wrapper;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function emptyEvidenceHistoryResponse(): Response {
  return jsonResponse({
    data: { total: 0, items: [] },
    meta: { request_id: "evidence-history" },
  });
}

function evidenceHistoryWithDraftResponse(): Response {
  return jsonResponse({
    data: {
      total: 1,
      items: [
        {
          record: {
            id: "history-evidence-1",
            study_date: "2026-07-14",
            subject_id: "english",
            status: "pending",
            asset_count: 2,
          },
          assets: [
            {
              id: "history-asset-1",
              original_name: "proof.png",
              mime_type: "image/png",
              size_bytes: 1024,
              page_order: 0,
            },
          ],
          draft: {
            id: "history-draft-1",
            evidence_record_id: "history-evidence-1",
            status: "draft",
            structured_json: {
              confirmed_facts: { asset_count: 2, visible_text: "二次函数求最值" },
              inferences: { topic: "二次函数" },
              uncertain_fields: [
                { field: "answer", reason: "图片右侧被裁切", confidence: 0.4 },
              ],
              teaching_judgment: {
                diagnosis: "配方法步骤需要复核",
                evidence_basis: ["草稿第 2 行"],
                risk: "符号可能抄错",
              },
              suggested_actions: [{ type: "redo_without_hints", priority: "high" }],
            },
            validation_errors: [],
          },
        },
      ],
    },
    meta: { request_id: "evidence-history" },
  });
}

function evidenceHistoryWithoutDraftResponse(): Response {
  return jsonResponse({
    data: {
      total: 1,
      items: [
        {
          record: {
            id: "history-evidence-1",
            study_date: "2026-07-14",
            subject_id: "math",
            status: "pending",
            asset_count: 1,
          },
          assets: [
            {
              id: "history-asset-1",
              original_name: "proof.png",
              mime_type: "image/png",
              size_bytes: 1024,
              page_order: 0,
            },
          ],
          draft: null,
        },
      ],
    },
    meta: { request_id: "evidence-history" },
  });
}

function evidenceHistoryWithProviderFailureResponse(): Response {
  return jsonResponse({
    data: {
      total: 1,
      items: [
        {
          record: {
            id: "failed-evidence-1",
            study_date: "2026-09-24",
            subject_id: "math",
            status: "pending",
            asset_count: 1,
          },
          assets: [
            {
              id: "failed-asset-1",
              original_name: "proof.png",
              mime_type: "image/png",
              size_bytes: 1024,
              page_order: 0,
            },
          ],
          draft: {
            id: "failed-draft-1",
            evidence_record_id: "failed-evidence-1",
            status: "needs_correction",
            structured_json: {},
            validation_errors: ["provider:AI_PROVIDER_AUTH_FAILED"],
          },
        },
      ],
    },
    meta: { request_id: "evidence-history" },
  });
}

function emptyWrongbookDraftHistoryResponse(): Response {
  return jsonResponse({
    data: { total: 0, items: [] },
    meta: { request_id: "wrongbook-history" },
  });
}

function wrongbookDraftHistoryWithDraftResponse(status: "draft" | "confirmed" = "draft"): Response {
  return jsonResponse({
    data: {
      total: 1,
      items: [
        {
          record: {
            id: "wrong-history-1",
            updated_at: "2026-07-14T10:00:00Z",
            knowledge_node_id: "node-1",
            current_status: status === "confirmed" ? "pending_no_hint_redo" : "pending_analysis",
            error_count: 1,
          },
          verification: {
            wrong_record_id: "wrong-history-1",
            variant_passed: false,
            interval_test_passed: false,
          },
          draft: {
            id: "wrong-draft-1",
            wrong_record_id: "wrong-history-1",
            status,
            structured_json: {
              surface_cause: "sign error",
              deep_cause: "chain rule retrieval failed",
              prerequisite_gap: "derivative chain rule",
              remediation_plan: [{ action: "redo_without_hints" }],
            },
            validation_errors: [],
          },
        },
      ],
    },
    meta: { request_id: "wrongbook-history" },
  });
}

describe("App", () => {
  beforeEach(() => {
    window.scrollTo = vi.fn();
  });

  afterEach(() => {
    window.sessionStorage.clear();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("requires the personal access key when cloud authentication is enabled", async () => {
    vi.stubEnv("VITE_YANTU_AUTH_REQUIRED", "true");

    const wrapper = await mountApp();

    expect(wrapper.get("#access-title").text()).toBe("进入研途教练");
    expect(wrapper.find('[data-testid="app-title"]').exists()).toBe(false);
  });

  it("renders the five primary product entries", async () => {
    const wrapper = await mountApp();

    expect(wrapper.get('[data-testid="app-title"]').text()).toBe("研途教练");
    expect(wrapper.findAll(".nav-link strong").map((item) => item.text())).toEqual(
      primaryNavItems.map((item) => item.label),
    );
  });

  it("renders route content for a non-default page", async () => {
    const wrapper = await mountApp("/planning");

    expect(wrapper.get('[data-testid="page-title"]').text()).toBe("五层规划");
  });

  it("renders today's tasks and metrics from the API when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v1/evidence/history?limit=10") {
          return evidenceHistoryWithDraftResponse();
        }
        expect(path).toMatch(/^\/api\/v1\/today\?date=/);
        return new Response(
          JSON.stringify({
            data: {
              date: "2026-07-15",
              total_tasks: 1,
              estimated_minutes: 45,
              tasks: [
                {
                  id: "task-api-1",
                  version: 1,
                  goal_id: "goal-week",
                  subject_id: "math",
                  knowledge_node_id: "node-1",
                  title: "API 今日任务",
                  task_type: "practice",
                  priority: "high",
                  source_type: "goal",
                  source_id: "goal-week",
                  planned_date: "2026-07-15",
                  estimated_minutes: 45,
                  current_stage: 2,
                  target_stage: 3,
                  reason: "后端计划生成",
                  completion_standard: "提交练习结果",
                  prerequisite_status: "satisfied",
                  status: "pending",
                },
              ],
            },
            meta: { request_id: "today" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/today");

    expect(wrapper.text()).toContain("API 今日任务");
    expect(wrapper.text()).toContain("1 项");
    expect(wrapper.text()).toContain("预计 45 分钟");
    expect(wrapper.text()).toContain("证据草稿历史");
    expect(wrapper.text()).toContain("2026-07-14");
    expect(wrapper.text()).toContain("english · 2 个附件");

    await wrapper.get(".evidence-history-actions .task-action-button.secondary").trigger("click");

    expect(wrapper.text()).toContain("待确认证据草稿");
    expect(wrapper.text()).toContain("草稿已关联 2 个证据附件");
    expect(wrapper.text()).toContain("proof.png");
    expect(wrapper.text()).toContain("分析结果");
    expect(wrapper.text()).toContain("二次函数求最值");
    expect(wrapper.text()).toContain("图片右侧被裁切");
    expect(wrapper.text()).toContain("配方法步骤需要复核");
    expect(wrapper.text()).toContain("redo_without_hints");
  });

  it("shows explicit evidence history actions and deletes an unconfirmed record", async () => {
    const calls: Array<{ path: string; method: string }> = [];
    let deleted = false;
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        const method = init?.method ?? "GET";
        calls.push({ path, method });
        if (path === "/api/v1/evidence/history?limit=10") {
          return deleted ? emptyEvidenceHistoryResponse() : evidenceHistoryWithDraftResponse();
        }
        if (path === "/api/v1/evidence/history-evidence-1" && method === "DELETE") {
          deleted = true;
          return jsonResponse({
            data: {
              record_id: "history-evidence-1",
              deleted_asset_ids: ["history-asset-1"],
              retained_asset_ids: [],
            },
            meta: { request_id: "evidence-delete" },
          });
        }
        return jsonResponse({ data: { date: "2026-07-15", tasks: [], total_tasks: 0, estimated_minutes: 0 }, meta: { request_id: "today" } });
      }),
    );

    const wrapper = await mountApp("/today");
    const actions = wrapper.findAll(".evidence-history-actions button");
    expect(actions.map((button) => button.text())).toEqual(["查看", "删除"]);

    await actions[1].trigger("click");
    await flushPromises();

    expect(calls).toContainEqual({ path: "/api/v1/evidence/history-evidence-1", method: "DELETE" });
    expect(wrapper.text()).toContain("还没有历史证据草稿");
  });

  it("shows a sanitized provider failure instead of an empty analysis", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v1/evidence/history?limit=10") {
          return evidenceHistoryWithProviderFailureResponse();
        }
        return jsonResponse({
          data: { date: "2026-09-24", tasks: [], total_tasks: 0, estimated_minutes: 0 },
          meta: { request_id: "today" },
        });
      }),
    );

    const wrapper = await mountApp("/today");
    await wrapper.get(".evidence-history-actions .task-action-button.secondary").trigger("click");

    expect(wrapper.text()).toContain("DeepSeek API Key 无效、已过期或没有当前模型权限");
    expect(wrapper.text()).toContain("provider:AI_PROVIDER_AUTH_FAILED");
    expect(wrapper.text()).toContain("可见事实");
    expect(wrapper.text()).toContain("暂无内容");
  });

  it("analyzes a previously uploaded evidence record from history", async () => {
    const calls: string[] = [];
    let analyzed = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        calls.push(path);
        if (path === "/api/v1/evidence/history?limit=10") {
          return analyzed ? evidenceHistoryWithDraftResponse() : evidenceHistoryWithoutDraftResponse();
        }
        if (path === "/api/v1/evidence/history-evidence-1/analyze") {
          analyzed = true;
          return jsonResponse({
            data: {
              draft: {
                id: "history-draft-1",
                evidence_record_id: "history-evidence-1",
                status: "draft",
                structured_json: {
                  confirmed_facts: { asset_count: 1 },
                  suggested_actions: [{ type: "confirm_or_reject" }],
                },
                validation_errors: [],
              },
              ai_job: { id: "history-job-1", status: "succeeded" },
            },
            meta: { request_id: "evidence-analyze" },
          });
        }
        return jsonResponse({ data: { date: "2026-07-15", tasks: [], total_tasks: 0, estimated_minutes: 0 }, meta: { request_id: "today" } });
      }),
    );

    const wrapper = await mountApp("/today");
    await wrapper.get(".evidence-history-actions .task-action-button.secondary").trigger("click");
    expect(wrapper.text()).toContain("尚未分析");
    expect(wrapper.text()).toContain("开始分析");

    await wrapper.get(".evidence-detail > .task-actions .task-action-button").trigger("click");
    await flushPromises();

    expect(calls).toContain("/api/v1/evidence/history-evidence-1/analyze");
    expect(wrapper.text()).toContain("待确认证据草稿");
  });

  it("starts a today task through the guarded task action API", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        if (path === "/api/v1/evidence/history?limit=10") {
          return emptyEvidenceHistoryResponse();
        }
        if (path.startsWith("/api/v1/today")) {
          return new Response(
            JSON.stringify({
              data: {
                date: "2026-07-15",
                total_tasks: 1,
                estimated_minutes: 45,
                tasks: [
                  {
                    id: "task-api-1",
                    version: 1,
                    goal_id: "goal-week",
                    subject_id: "math",
                    knowledge_node_id: "node-1",
                    title: "API 今日任务",
                    task_type: "practice",
                    priority: "high",
                    source_type: "goal",
                    source_id: "goal-week",
                    planned_date: "2026-07-15",
                    estimated_minutes: 45,
                    current_stage: 2,
                    target_stage: 3,
                    reason: "后端计划生成",
                    completion_standard: "提交练习结果",
                    prerequisite_status: "satisfied",
                    status: "pending",
                  },
                ],
              },
              meta: { request_id: "today" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              id: "task-api-1",
              version: 2,
              goal_id: "goal-week",
              subject_id: "math",
              knowledge_node_id: "node-1",
              title: "API 今日任务",
              task_type: "practice",
              priority: "high",
              source_type: "goal",
              source_id: "goal-week",
              planned_date: "2026-07-15",
              estimated_minutes: 45,
              current_stage: 2,
              target_stage: 3,
              reason: "后端计划生成",
              completion_standard: "提交练习结果",
              prerequisite_status: "satisfied",
              status: "in_progress",
            },
            meta: { request_id: "task-start" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/today");
    const startButton = wrapper.findAll("button").find((button) => button.text() === "开始");

    await startButton?.trigger("click");
    await flushPromises();

    expect(calls.map((call) => call.path)).toEqual([
      "/api/v1/evidence/history?limit=10",
      expect.stringMatching(/^\/api\/v1\/today\?date=/),
      "/api/v1/tasks/task-api-1/start",
    ]);
    expect(calls[2].init?.headers).toMatchObject({ "If-Match": "1" });
    expect(wrapper.text()).toContain("in_progress");
  });

  it("submits a filled result form and marks a today task completed", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        if (path === "/api/v1/evidence/history?limit=10") {
          return emptyEvidenceHistoryResponse();
        }
        if (path.startsWith("/api/v1/today")) {
          return new Response(
            JSON.stringify({
              data: {
                date: "2026-07-15",
                total_tasks: 1,
                estimated_minutes: 45,
                tasks: [
                  {
                    id: "task-api-1",
                    version: 1,
                    goal_id: "goal-week",
                    subject_id: "math",
                    knowledge_node_id: "node-1",
                    title: "API 今日任务",
                    task_type: "practice",
                    priority: "high",
                    source_type: "goal",
                    source_id: "goal-week",
                    planned_date: "2026-07-15",
                    estimated_minutes: 45,
                    current_stage: 2,
                    target_stage: 3,
                    reason: "后端计划生成",
                    completion_standard: "提交练习结果",
                    prerequisite_status: "satisfied",
                    status: "pending",
                  },
                ],
              },
              meta: { request_id: "today" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (path === "/api/v1/tasks/task-api-1/results") {
          return new Response(
            JSON.stringify({
              data: {
                created: true,
                result: {
                  id: "result-1",
                  version: 1,
                  created_at: "2026-07-15T00:00:00Z",
                  updated_at: "2026-07-15T00:00:00Z",
                  task_id: "task-api-1",
                  result_type: "partial",
                  completion_ratio: 80,
                  actual_minutes: 40,
                  question_count: 5,
                  correct_count: 4,
                  accuracy: 80,
                  confidence: 70,
                  hint_level: null,
                  focus_level: null,
                  difficulty_rating: null,
                  problem_description: "漏看条件",
                  confirmed_at: "2026-07-15T00:00:00Z",
                },
              },
              meta: { request_id: "task-result" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              id: "task-api-1",
              version: 2,
              goal_id: "goal-week",
              subject_id: "math",
              knowledge_node_id: "node-1",
              title: "API 今日任务",
              task_type: "practice",
              priority: "high",
              source_type: "goal",
              source_id: "goal-week",
              planned_date: "2026-07-15",
              estimated_minutes: 45,
              current_stage: 2,
              target_stage: 3,
              reason: "后端计划生成",
              completion_standard: "提交练习结果",
              prerequisite_status: "satisfied",
              status: "completed",
            },
            meta: { request_id: "task-complete" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/today");
    const completeButton = wrapper.findAll("button").find((button) => button.text() === "完成");

    await completeButton?.trigger("click");
    const inputs = wrapper.findAll(".task-result-form input");
    await inputs[0].setValue("40");
    await inputs[1].setValue("80");
    await inputs[2].setValue("5");
    await inputs[3].setValue("4");
    await inputs[4].setValue("70");
    await wrapper.find(".task-result-form textarea").setValue("漏看条件");
    await wrapper.find(".task-result-form").trigger("submit");
    await flushPromises();

    expect(calls.map((call) => call.path)).toEqual([
      "/api/v1/evidence/history?limit=10",
      expect.stringMatching(/^\/api\/v1\/today\?date=/),
      "/api/v1/tasks/task-api-1/results",
      "/api/v1/tasks/task-api-1",
    ]);
    expect(calls[2].init?.headers).toMatchObject({
      "Idempotency-Key": "task-api-1:complete:1:80:40:5:4",
    });
    expect(JSON.parse(String(calls[2].init?.body))).toMatchObject({
      result_type: "partial",
      completion_ratio: 80,
      actual_minutes: 40,
      question_count: 5,
      correct_count: 4,
      accuracy: 80,
      confidence: 70,
      problem_description: "漏看条件",
    });
    expect(calls[3].init?.method).toBe("PATCH");
    expect(calls[3].init?.headers).toMatchObject({ "If-Match": "1" });
    expect(wrapper.text()).toContain("completed");
  });

  it("generates and confirms an evidence draft from the today page", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        if (path === "/api/v1/evidence/history?limit=10") {
          return emptyEvidenceHistoryResponse();
        }
        if (path.startsWith("/api/v1/today")) {
          return new Response(
            JSON.stringify({
              data: {
                date: "2026-07-15",
                total_tasks: 0,
                estimated_minutes: 0,
                tasks: [],
              },
              meta: { request_id: "today" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (path === "/api/v1/evidence/uploads") {
          return new Response(
            JSON.stringify({
              data: {
                record: {
                  id: "evidence-1",
                  version: 1,
                  created_at: "2026-07-15T09:00:00Z",
                  updated_at: "2026-07-15T09:00:00Z",
                  created_by: "user",
                  study_date: "2026-07-15",
                  subject_id: "math",
                  status: "pending",
                  asset_count: 1,
                  confirmed_facts: null,
                  inferences: null,
                  uncertain_fields: null,
                  teaching_judgment: null,
                  suggested_actions: null,
                  confirmed_at: null,
                  rejected_at: null,
                },
                assets: [
                  {
                    id: "asset-1",
                    version: 1,
                    created_at: "2026-07-15T09:00:00Z",
                    updated_at: "2026-07-15T09:00:00Z",
                    original_name: "daily-evidence.png",
                    storage_path: "files/original/daily-evidence.png",
                    mime_type: "image/png",
                    size_bytes: 24,
                    state: "inbox",
                    reference_count: 1,
                    page_order: 0,
                  },
                ],
              },
              meta: { request_id: "evidence-upload" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (path === "/api/v1/evidence/evidence-1/analyze") {
          return new Response(
            JSON.stringify({
              data: {
                draft: {
                  id: "draft-1",
                  version: 1,
                  created_at: "2026-07-15T09:01:00Z",
                  updated_at: "2026-07-15T09:01:00Z",
                  evidence_record_id: "evidence-1",
                  ai_job_id: "job-1",
                  status: "draft",
                  schema_version: "evidence-analysis-v1",
                  structured_json: {
                    confirmed_facts: { asset_count: 1 },
                    suggested_actions: [{ type: "confirm_or_reject" }],
                  },
                  validation_errors: [],
                  confirmed_at: null,
                  rejected_at: null,
                  rejection_reason: null,
                  confirmed_once: false,
                },
                ai_job: {
                  id: "job-1",
                  version: 1,
                  created_at: "2026-07-15T09:01:00Z",
                  updated_at: "2026-07-15T09:01:00Z",
                  job_type: "evidence_analysis",
                  provider: "fake",
                  model_name: "fake",
                  prompt_version: "evidence-draft-fake-v1",
                  status: "succeeded",
                  attempts: 1,
                  input_json: { record_id: "evidence-1" },
                  output_json: null,
                  error_code: null,
                  error_message: null,
                  started_at: "2026-07-15T09:01:00Z",
                  completed_at: "2026-07-15T09:01:01Z",
                },
              },
              meta: { request_id: "evidence-analyze" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              created: true,
              record: {
                id: "evidence-1",
                version: 2,
                created_at: "2026-07-15T09:00:00Z",
                updated_at: "2026-07-15T09:02:00Z",
                created_by: "user",
                study_date: "2026-07-15",
                subject_id: "math",
                status: "confirmed",
                asset_count: 1,
                confirmed_facts: { asset_count: 1 },
                inferences: { provider: "fake" },
                uncertain_fields: [],
                teaching_judgment: { risk: "low" },
                suggested_actions: [{ type: "confirm_or_reject" }],
                confirmed_at: "2026-07-15T09:02:00Z",
                rejected_at: null,
              },
              draft: {
                id: "draft-1",
                version: 2,
                created_at: "2026-07-15T09:01:00Z",
                updated_at: "2026-07-15T09:02:00Z",
                evidence_record_id: "evidence-1",
                ai_job_id: "job-1",
                status: "confirmed",
                schema_version: "evidence-analysis-v1",
                structured_json: {
                  confirmed_facts: { asset_count: 1 },
                  suggested_actions: [{ type: "confirm_or_reject" }],
                },
                validation_errors: [],
                confirmed_at: "2026-07-15T09:02:00Z",
                rejected_at: null,
                rejection_reason: null,
                confirmed_once: true,
              },
            },
            meta: { request_id: "evidence-confirm" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/today");
    const fileInput = wrapper.find('input[type="file"]');
    const evidenceFile = new File(["evidence-demo-png"], "daily-proof.png", {
      type: "image/png",
    });
    Object.defineProperty(fileInput.element, "files", {
      configurable: true,
      value: [evidenceFile],
    });
    await fileInput.trigger("change");

    await wrapper.get(".evidence-upload-form").trigger("submit");
    await vi.waitFor(() => {
      expect(calls).toHaveLength(5);
    });

    expect(calls.map((call) => call.path)).toEqual([
      "/api/v1/evidence/history?limit=10",
      expect.stringMatching(/^\/api\/v1\/today\?date=/),
      "/api/v1/evidence/uploads",
      "/api/v1/evidence/evidence-1/analyze",
      "/api/v1/evidence/history?limit=10",
    ]);
    expect(JSON.parse(String(calls[2].init?.body))).toMatchObject({
      study_date: expect.any(String),
      subject_id: "math",
      files: [
        {
          original_name: "daily-proof.png",
          mime_type: "image/png",
          content_base64: expect.any(String),
        },
      ],
    });
    expect(JSON.parse(String(calls[3].init?.body))).toEqual({ provider_mode: "valid" });
    expect(wrapper.text()).toContain("待确认证据草稿");

    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "确认");
    await confirmButton?.trigger("click");
    await flushPromises();

    expect(calls[5].path).toBe("/api/v1/evidence/evidence-1/confirm");
    expect(calls[5].init?.body).toBeUndefined();
    expect(calls[6].path).toBe("/api/v1/evidence/history?limit=10");
    expect(wrapper.text()).toContain("证据草稿已确认");
    expect(wrapper.text()).toContain("证据记录 已确认");
  });

  it("renders planning goal tree from the API when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        expect(String(input)).toBe("/api/v1/goals/tree");
        return new Response(
          JSON.stringify({
            data: {
              total: 1,
              items: [
                {
                  id: "goal-semester",
                  version: 1,
                  parent_id: null,
                  level: "semester",
                  subject_id: "math",
                  title: "API 学期目标",
                  description: null,
                  start_date: "2026-07-01",
                  end_date: "2026-12-20",
                  estimated_minutes: 1000,
                  actual_minutes: 250,
                  completion_standard: "完成闭环",
                  progress: 25,
                  risk_status: "normal",
                  status: "active",
                  adjustment_reason: null,
                  children: [],
                },
              ],
            },
            meta: { request_id: "goals" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/planning");

    expect(wrapper.text()).toContain("API 学期目标");
    expect(wrapper.text()).toContain("25% · 250/1000 min");
  });

  it("renders settings profile and rules from the API when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v1/settings/profile") {
          return new Response(
            JSON.stringify({
              data: {
                name: "hvv",
                target_school: "DUT",
                target_major: "control",
                exam_date: "2026-12-20",
                current_phase: "强化",
                coach_style: "strict",
                timezone: "Asia/Shanghai",
                updated_at: "2026-07-15T00:00:00Z",
              },
              meta: { request_id: "profile" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              total: 1,
              items: [
                {
                  key: "mastery",
                  version: "mastery-v1.0.0",
                  path: "config/mastery_rules.v1.yaml",
                  sha256: "b".repeat(64),
                  content: "version: mastery-v1.0.0",
                },
              ],
            },
            meta: { request_id: "rules" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/settings");

    expect(wrapper.text()).toContain("DUT");
    expect(wrapper.text()).toContain("control");
    expect(wrapper.text()).toContain("mastery-v1.0.0");
  });

  it("renders progress analytics from the API when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        const dataByPath: Record<string, unknown> = {
          "/api/v1/analytics/mastery": {
            latest_snapshot_count: 2,
            weak_node_count: 1,
            stage_distribution: [
              { key: "2", count: 1 },
              { key: "5", count: 1 },
            ],
          },
          "/api/v1/analytics/errors": {
            total_wrong_records: 1,
            by_status: [{ key: "regressed", count: 1 }],
            by_knowledge_node: [{ knowledge_node_id: "node-weak", count: 1 }],
          },
          "/api/v1/analytics/time": {
            estimated_minutes: 50,
            actual_minutes: 70,
            by_subject: [{ subject_id: "math", estimated_minutes: 50, actual_minutes: 70 }],
          },
          "/api/v1/analytics/goal-risk": {
            total_goals: 2,
            by_risk_status: [
              { key: "normal", count: 1 },
              { key: "high", count: 1 },
            ],
            risky_goals: [
              {
                object_type: "goal",
                object_id: "goal-risk",
                title: "本周导数应用",
                level: "week",
                risk_status: "high",
                status: "delayed",
                progress: 40,
              },
            ],
          },
          "/api/v1/graph/weak": {
            total: 1,
            items: [
              {
                object_type: "knowledge_node",
                object_id: "node-weak",
                label: "导数应用",
                subject_id: "math",
                latest_stage: 2,
                evidence_count: 1,
                repeat_error_rate: 40,
                blocking_reasons: ["needs_variant"],
              },
            ],
          },
        };
        return new Response(
          JSON.stringify({
            data: dataByPath[path],
            meta: { request_id: `progress-${path}` },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/progress");

    expect(wrapper.text()).toContain("导数应用");
    expect(wrapper.text()).toContain("错因率 40%");
    expect(wrapper.text()).toContain("本周导数应用");
    expect(wrapper.text()).toContain("实际用时比预估多 20 分钟");
  });

  it("renders learning resources, knowledge nodes, and wrongbook candidates from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v1/wrongbook/history?limit=10") {
          return wrongbookDraftHistoryWithDraftResponse();
        }
        const dataByPath: Record<string, unknown> = {
          "/api/v1/resources": {
            total: 1,
            items: [
              {
                id: "asset-lecture",
                resource_type: "asset",
                asset: {
                  id: "asset-lecture",
                  version: 1,
                  created_at: "2026-07-15T00:00:00Z",
                  updated_at: "2026-07-15T00:00:00Z",
                  sha256: "d".repeat(64),
                  original_name: "lecture.pdf",
                  storage_path: "files/original/lecture.pdf",
                  mime_type: "application/pdf",
                  size_bytes: 2048,
                  state: "organized",
                  reference_count: 2,
                },
              },
            ],
          },
          "/api/v1/knowledge/nodes": {
            total: 1,
            items: [
              {
                id: "node-1",
                version: 1,
                created_at: "2026-07-15T00:00:00Z",
                updated_at: "2026-07-15T00:00:00Z",
                created_by: "user",
                is_deleted: false,
                deleted_at: null,
                subject_id: "math",
                parent_id: null,
                code: "MATH-001",
                name: "导数应用",
                node_type: "knowledge",
                importance: 90,
                exam_frequency: 90,
                description: null,
                status: "active",
              },
            ],
          },
          "/api/v1/wrongbook/planning-candidates": {
            total: 1,
            items: [
              {
                id: "candidate-1",
                title: "导数错题无提示重做",
                subject_id: "math",
                estimated_minutes: 25,
                cognitive_load: "medium",
                source_type: "wrongbook",
                source_id: "wrong-1",
                task_type: "wrongbook_variant",
                difficulty: "medium",
                review_due: 1,
                knowledge_importance: 90,
                weakness: 80,
                repeat_error: 50,
              },
            ],
          },
        };
        if (path.startsWith("/api/v1/reviews/due?date=")) {
          return new Response(
            JSON.stringify({
              data: {
                date: "2026-07-15",
                total: 1,
                items: [
                  {
                    knowledge_node_name: "导数应用",
                    schedule: {
                      id: "review-1",
                      version: 1,
                      created_at: "2026-07-14T00:00:00Z",
                      updated_at: "2026-07-14T00:00:00Z",
                      knowledge_node_id: "node-1",
                      subject_id: "math",
                      current_stage: 3,
                      status: "active",
                      due_at: "2026-07-15T00:00:00Z",
                      interval_days: 3,
                      pass_streak: 0,
                      fail_streak: 0,
                      last_reviewed_at: null,
                      last_result_id: null,
                      source_snapshot_id: "snapshot-1",
                      rule_version: "review-v1.0.0",
                      next_reason: "base_interval:closed_book_recall",
                    },
                    candidate: {
                      id: "review:review-1",
                      title: "复习：导数应用",
                      subject_id: "math",
                      estimated_minutes: 20,
                      cognitive_load: "medium",
                      source_type: "review_schedule",
                      source_id: "review-1",
                      task_type: "review",
                      review_due: 100,
                      knowledge_importance: 90,
                    },
                  },
                ],
              },
              meta: { request_id: `learning-${path}` },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: dataByPath[path],
            meta: { request_id: `learning-${path}` },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/learning");

    expect(wrapper.text()).toContain("lecture.pdf");
    expect(wrapper.text()).toContain("导数应用");
    expect(wrapper.text()).toContain("导数错题无提示重做");
    expect(wrapper.text()).toContain("复习：导数应用");
    expect(wrapper.text()).toContain("错题草稿历史");
    expect(wrapper.text()).toContain("待确认错题草稿");
    expect(wrapper.text()).toContain("sign error");
  });

  it("confirms a wrongbook draft from the learning page history entry", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    let historyCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        const emptyList = { total: 0, items: [] };
        if (path === "/api/v1/wrongbook/history?limit=10") {
          historyCalls += 1;
          return wrongbookDraftHistoryWithDraftResponse(
            historyCalls > 1 ? "confirmed" : "draft",
          );
        }
        if (path === "/api/v1/resources" || path === "/api/v1/knowledge/nodes") {
          return jsonResponse({ data: emptyList, meta: { request_id: path } });
        }
        if (path === "/api/v1/wrongbook/planning-candidates") {
          return jsonResponse({ data: emptyList, meta: { request_id: path } });
        }
        if (path.startsWith("/api/v1/reviews/due?date=")) {
          return jsonResponse({
            data: { date: "2026-07-15", ...emptyList },
            meta: { request_id: path },
          });
        }
        return jsonResponse({
          data: {
            created: true,
            record: {
              id: "wrong-history-1",
              version: 2,
              created_at: "2026-07-14T10:00:00Z",
              updated_at: "2026-07-15T10:00:00Z",
              created_by: "user",
              question_id: "question-1",
              knowledge_node_id: "node-1",
              surface_cause: "sign error",
              deep_cause: "chain rule retrieval failed",
              prerequisite_gap: "derivative chain rule",
              error_count: 1,
              redo_count: 0,
              current_status: "pending_no_hint_redo",
              next_review_at: null,
              resolved_at: null,
            },
            draft: {
              id: "wrong-draft-1",
              version: 2,
              created_at: "2026-07-14T10:00:00Z",
              updated_at: "2026-07-15T10:00:00Z",
              wrong_record_id: "wrong-history-1",
              ai_job_id: "job-1",
              status: "confirmed",
              schema_version: "wrongbook-analysis-v1",
              structured_json: {
                surface_cause: "sign error",
                deep_cause: "chain rule retrieval failed",
                prerequisite_gap: "derivative chain rule",
                remediation_plan: [{ action: "redo_without_hints" }],
              },
              validation_errors: [],
              confirmed_at: "2026-07-15T10:00:00Z",
              confirmed_once: true,
            },
          },
          meta: { request_id: "wrongbook-confirm" },
        });
      }),
    );
    const wrapper = await mountApp("/learning");
    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "确认草稿");

    await confirmButton?.trigger("click");
    await flushPromises();

    expect(calls.some((call) => call.path === "/api/v1/wrongbook/history?limit=10")).toBe(true);
    const confirmCall = calls.find(
      (call) => call.path === "/api/v1/wrongbook/wrong-history-1/confirm",
    );
    expect(confirmCall).toBeDefined();
    expect(confirmCall?.init?.body).toBeUndefined();
    expect(wrapper.text()).toContain("错题草稿已确认");
    expect(wrapper.text()).toContain("待无提示重做");
  });

  it("submits a due review result from the learning page", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        const emptyList = { total: 0, items: [] };
        if (path === "/api/v1/wrongbook/history?limit=10") {
          return emptyWrongbookDraftHistoryResponse();
        }
        if (path === "/api/v1/resources" || path === "/api/v1/knowledge/nodes") {
          return new Response(JSON.stringify({ data: emptyList, meta: { request_id: path } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (path === "/api/v1/wrongbook/planning-candidates") {
          return new Response(JSON.stringify({ data: emptyList, meta: { request_id: path } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (path.startsWith("/api/v1/reviews/due?date=")) {
          return new Response(
            JSON.stringify({
              data: {
                date: "2026-07-15",
                total: 1,
                items: [
                  {
                    knowledge_node_name: "导数应用",
                    schedule: {
                      id: "review-1",
                      version: 1,
                      created_at: "2026-07-14T00:00:00Z",
                      updated_at: "2026-07-14T00:00:00Z",
                      knowledge_node_id: "node-1",
                      subject_id: "math",
                      current_stage: 3,
                      status: "active",
                      due_at: "2026-07-15T00:00:00Z",
                      interval_days: 3,
                      pass_streak: 0,
                      fail_streak: 0,
                      last_reviewed_at: null,
                      last_result_id: null,
                      source_snapshot_id: "snapshot-1",
                      rule_version: "review-v1.0.0",
                      next_reason: "base_interval:closed_book_recall",
                    },
                    candidate: {
                      id: "review:review-1",
                      title: "复习：导数应用",
                      subject_id: "math",
                      estimated_minutes: 20,
                      cognitive_load: "medium",
                      source_type: "review_schedule",
                      source_id: "review-1",
                      task_type: "review",
                      review_due: 100,
                      knowledge_importance: 90,
                    },
                  },
                ],
              },
              meta: { request_id: "due-reviews" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              created: true,
              evaluation_new_stage: 3,
              evaluation_reason: "review_passed",
              rule_version: "review-v1.0.0",
              result: {
                id: "result-1",
                version: 1,
                created_at: "2026-07-15T10:00:00Z",
                updated_at: "2026-07-15T10:00:00Z",
                schedule_id: "review-1",
                knowledge_node_id: "node-1",
                result_type: "pass",
                score: 90,
                sample_count: 0,
                correct_count: null,
                accuracy: null,
                occurred_at: "2026-07-15T10:00:00Z",
                independent_timepoint: true,
                evidence_id: "evidence-1",
                snapshot_id: "snapshot-2",
              },
              schedule: {
                id: "review-1",
                version: 2,
                created_at: "2026-07-14T00:00:00Z",
                updated_at: "2026-07-15T10:00:00Z",
                knowledge_node_id: "node-1",
                subject_id: "math",
                current_stage: 3,
                status: "active",
                due_at: "2026-07-21T10:00:00Z",
                interval_days: 6,
                pass_streak: 1,
                fail_streak: 0,
                last_reviewed_at: "2026-07-15T10:00:00Z",
                last_result_id: "result-1",
                source_snapshot_id: "snapshot-1",
                rule_version: "review-v1.0.0",
                next_reason: "passed_independent_review:1",
              },
            },
            meta: { request_id: "review-result" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/learning");
    const passButton = wrapper.findAll("button").find((button) => button.text() === "通过");

    await passButton?.trigger("click");
    await flushPromises();

    const resultCall = calls.find((call) => call.path === "/api/v1/reviews/review-1/results");
    expect(resultCall).toBeDefined();
    expect(resultCall?.init?.headers).toMatchObject({
      "Idempotency-Key": "review-1:pass:1",
    });
    expect(JSON.parse(String(resultCall?.init?.body))).toMatchObject({
      result_type: "pass",
      score: 90,
    });
    expect(wrapper.text()).toContain("已通过");
    expect(wrapper.text()).toContain("下次间隔 6 天");
  });

  it("submits a wrongbook shortcut result from the learning page", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
        const emptyList = { total: 0, items: [] };
        if (path === "/api/v1/wrongbook/history?limit=10") {
          return emptyWrongbookDraftHistoryResponse();
        }
        if (path === "/api/v1/resources" || path === "/api/v1/knowledge/nodes") {
          return new Response(JSON.stringify({ data: emptyList, meta: { request_id: path } }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (path.startsWith("/api/v1/reviews/due?date=")) {
          return new Response(
            JSON.stringify({ data: { date: "2026-07-15", ...emptyList }, meta: { request_id: path } }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (path === "/api/v1/wrongbook/planning-candidates") {
          return new Response(
            JSON.stringify({
              data: {
                total: 1,
                items: [
                  {
                    id: "candidate-1",
                    title: "导数错题变式验证",
                    subject_id: "math",
                    estimated_minutes: 25,
                    cognitive_load: "medium",
                    source_type: "wrong_record",
                    source_id: "wrong-1",
                    task_type: "wrongbook_variant",
                    difficulty: "medium",
                    review_due: 80,
                    knowledge_importance: 90,
                    weakness: 80,
                    repeat_error: 50,
                  },
                ],
              },
              meta: { request_id: "wrongbook-candidates" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        return new Response(
          JSON.stringify({
            data: {
              created: true,
              attempt: {
                id: "attempt-1",
                version: 1,
                created_at: "2026-07-15T10:00:00Z",
                updated_at: "2026-07-15T10:00:00Z",
                created_by: "user",
                question_id: "question-1",
                wrong_record_id: "wrong-1",
                idempotency_key: "wrong-1:variant:pass:wrongbook_variant",
                attempt_type: "variant",
                attempted_at: "2026-07-15T10:00:00Z",
                answer_text: null,
                is_correct: true,
                score: 96,
                duration_seconds: null,
                hint_level: null,
                confidence: 80,
                request_id: "wrongbook-result",
              },
              record: {
                id: "wrong-1",
                version: 2,
                created_at: "2026-07-14T00:00:00Z",
                updated_at: "2026-07-15T10:00:00Z",
                created_by: "user",
                question_id: "question-1",
                knowledge_node_id: "node-1",
                surface_cause: "calculation slip",
                deep_cause: "derivative rule not automatic",
                prerequisite_gap: "power rule",
                error_count: 1,
                redo_count: 2,
                current_status: "pending_interval",
                next_review_at: "2026-07-18T10:00:00Z",
                resolved_at: null,
              },
              verification: {
                id: "verification-1",
                version: 2,
                created_at: "2026-07-14T00:00:00Z",
                updated_at: "2026-07-15T10:00:00Z",
                wrong_record_id: "wrong-1",
                original_redo_passed: false,
                no_hint_redo_passed: true,
                variant_passed: true,
                interval_test_passed: false,
                transfer_test_passed: false,
                last_attempt_id: "attempt-1",
              },
            },
            meta: { request_id: "wrongbook-result" },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    const wrapper = await mountApp("/learning");
    const variantPassButton = wrapper
      .findAll("button")
      .find((button) => button.text() === "变式通过");

    await variantPassButton?.trigger("click");
    await flushPromises();

    const resultCall = calls.find(
      (call) => call.path === "/api/v1/wrongbook/wrong-1/variant-results",
    );
    expect(resultCall).toBeDefined();
    expect(resultCall?.init?.headers).toMatchObject({
      "Idempotency-Key": "wrong-1:variant:pass:wrongbook_variant",
    });
    expect(JSON.parse(String(resultCall?.init?.body))).toMatchObject({
      is_correct: true,
      score: 96,
      confidence: 80,
    });
    expect(wrapper.text()).toContain("待间隔复测");
    expect(wrapper.text()).toContain("变式 · 正确");
  });
});
