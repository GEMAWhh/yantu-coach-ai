import { describe, expect, it } from "vitest";

import { ApiClient } from "./client";
import type {
  AnalyticsMasteryPayload,
  ApiResponse,
  HealthPayload,
  KnowledgeNodeListPayload,
  ResourceListPayload,
  SettingsRulesPayload,
  TaskPayload,
  TaskResultSubmitPayload,
  TodayPayload,
  WeakGraphPayload,
  WrongbookCandidateListPayload,
} from "./contracts";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient", () => {
  it("calls health with typed response data", async () => {
    const payload: ApiResponse<HealthPayload> = {
      data: {
        status: "ok",
        service: "yantu-coach-api",
        environment: "test",
        data_root: "data/test",
      },
      meta: { request_id: "client-health" },
    };
    const calls: string[] = [];
    const client = new ApiClient("http://127.0.0.1:8000", async (input) => {
      calls.push(String(input));
      return jsonResponse(payload);
    });

    await expect(client.health()).resolves.toEqual(payload);
    expect(calls).toEqual(["http://127.0.0.1:8000/health"]);
  });

  it("raises typed errors from the unified error envelope", async () => {
    const client = new ApiClient("", async () =>
      jsonResponse(
        {
          error: {
            code: "VERSION_CONFLICT",
            message: "Resource version conflict",
            details: { expected: "contract-v1", received: "old-contract" },
            request_id: "client-409",
          },
        },
        409,
      ),
    );

    await expect(client.meta()).rejects.toMatchObject({
      status: 409,
      error: {
        code: "VERSION_CONFLICT",
        request_id: "client-409",
      },
    });
  });

  it("loads today tasks through the planning API contract", async () => {
    const payload: ApiResponse<TodayPayload> = {
      data: {
        date: "2026-07-14",
        total_tasks: 1,
        estimated_minutes: 45,
        tasks: [
          {
            id: "task-1",
            version: 1,
            goal_id: "goal-1",
            subject_id: "math",
            knowledge_node_id: null,
            title: "Closed-book recall",
            task_type: "study",
            priority: "must",
            source_type: "goal",
            source_id: "goal-1",
            planned_date: "2026-07-14",
            estimated_minutes: 45,
            current_stage: 2,
            target_stage: 3,
            reason: "Traceable weekly goal",
            completion_standard: "Recall without hints",
            prerequisite_status: "satisfied",
            status: "pending",
          },
        ],
      },
      meta: { request_id: "client-today" },
    };
    const calls: string[] = [];
    const client = new ApiClient("", async (input) => {
      calls.push(String(input));
      return jsonResponse(payload);
    });

    await expect(client.today("2026-07-14")).resolves.toEqual(payload);
    expect(calls).toEqual(["/api/v1/today?date=2026-07-14"]);
  });

  it("loads governed settings rules through the settings API contract", async () => {
    const payload: ApiResponse<SettingsRulesPayload> = {
      data: {
        total: 1,
        items: [
          {
            key: "mastery",
            version: "mastery-v1.0.0",
            path: "config/mastery_rules.v1.yaml",
            sha256: "a".repeat(64),
            content: "version: mastery-v1.0.0",
          },
        ],
      },
      meta: { request_id: "client-settings-rules" },
    };
    const calls: string[] = [];
    const client = new ApiClient("", async (input) => {
      calls.push(String(input));
      return jsonResponse(payload);
    });

    await expect(client.settingsRules()).resolves.toEqual(payload);
    expect(calls).toEqual(["/api/v1/settings/rules"]);
  });

  it("loads progress analytics through stable insights API paths", async () => {
    const mastery: ApiResponse<AnalyticsMasteryPayload> = {
      data: {
        latest_snapshot_count: 2,
        weak_node_count: 1,
        stage_distribution: [
          { key: "2", count: 1 },
          { key: "5", count: 1 },
        ],
      },
      meta: { request_id: "client-analytics-mastery" },
    };
    const weakGraph: ApiResponse<WeakGraphPayload> = {
      data: {
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
      meta: { request_id: "client-weak-graph" },
    };
    const calls: string[] = [];
    const client = new ApiClient("", async (input) => {
      calls.push(String(input));
      return jsonResponse(calls.length === 1 ? mastery : weakGraph);
    });

    await expect(client.analyticsMastery()).resolves.toEqual(mastery);
    await expect(client.weakGraph()).resolves.toEqual(weakGraph);
    expect(calls).toEqual(["/api/v1/analytics/mastery", "/api/v1/graph/weak"]);
  });

  it("loads learning resources, knowledge nodes, and wrongbook candidates", async () => {
    const resources: ApiResponse<ResourceListPayload> = {
      data: {
        total: 1,
        items: [
          {
            id: "asset-1",
            resource_type: "asset",
            asset: {
              id: "asset-1",
              version: 1,
              created_at: "2026-07-15T00:00:00Z",
              updated_at: "2026-07-15T00:00:00Z",
              sha256: "c".repeat(64),
              original_name: "lecture.pdf",
              storage_path: "files/original/lecture.pdf",
              mime_type: "application/pdf",
              size_bytes: 2048,
              state: "inbox",
              reference_count: 0,
            },
          },
        ],
      },
      meta: { request_id: "client-resources" },
    };
    const knowledge: ApiResponse<KnowledgeNodeListPayload> = {
      data: {
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
            exam_frequency: 80,
            description: null,
            status: "active",
          },
        ],
      },
      meta: { request_id: "client-knowledge" },
    };
    const candidates: ApiResponse<WrongbookCandidateListPayload> = {
      data: {
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
      meta: { request_id: "client-wrongbook-candidates" },
    };
    const payloads = [resources, knowledge, candidates];
    const calls: string[] = [];
    const client = new ApiClient("", async (input) => {
      calls.push(String(input));
      return jsonResponse(payloads[calls.length - 1]);
    });

    await expect(client.resources()).resolves.toEqual(resources);
    await expect(client.knowledgeNodes()).resolves.toEqual(knowledge);
    await expect(client.wrongbookPlanningCandidates()).resolves.toEqual(candidates);
    expect(calls).toEqual([
      "/api/v1/resources",
      "/api/v1/knowledge/nodes",
      "/api/v1/wrongbook/planning-candidates",
    ]);
  });

  it("submits task status actions with version protection", async () => {
    const payload: ApiResponse<TaskPayload> = {
      data: {
        id: "task-1",
        version: 2,
        goal_id: "goal-1",
        subject_id: "math",
        knowledge_node_id: null,
        title: "Closed-book recall",
        task_type: "study",
        priority: "must",
        source_type: "goal",
        source_id: "goal-1",
        planned_date: "2026-07-14",
        estimated_minutes: 45,
        current_stage: 2,
        target_stage: 3,
        reason: "Traceable weekly goal",
        completion_standard: "Recall without hints",
        prerequisite_status: "satisfied",
        status: "in_progress",
      },
      meta: { request_id: "client-task-start" },
    };
    const calls: Array<{ input: string; init?: RequestInit }> = [];
    const client = new ApiClient("", async (input, init) => {
      calls.push({ input: String(input), init });
      return jsonResponse(payload);
    });

    await expect(client.startTask("task-1", 1)).resolves.toEqual(payload);
    expect(calls).toHaveLength(1);
    expect(calls[0].input).toBe("/api/v1/tasks/task-1/start");
    expect(calls[0].init?.method).toBe("POST");
    expect(calls[0].init?.headers).toMatchObject({
      Accept: "application/json",
      "If-Match": "1",
    });
    expect(calls[0].init?.body).toBeUndefined();
  });

  it("submits task results with an idempotency key", async () => {
    const payload: ApiResponse<TaskResultSubmitPayload> = {
      data: {
        created: true,
        result: {
          id: "result-1",
          version: 1,
          created_at: "2026-07-14T10:00:00Z",
          updated_at: "2026-07-14T10:00:00Z",
          task_id: "task-1",
          result_type: "completed",
          completion_ratio: 100,
          actual_minutes: 45,
          question_count: null,
          correct_count: null,
          accuracy: null,
          confidence: null,
          hint_level: null,
          focus_level: null,
          difficulty_rating: null,
          problem_description: null,
          confirmed_at: "2026-07-14T10:00:00Z",
        },
      },
      meta: { request_id: "client-task-result" },
    };
    const calls: Array<{ input: string; init?: RequestInit }> = [];
    const client = new ApiClient("", async (input, init) => {
      calls.push({ input: String(input), init });
      return jsonResponse(payload);
    });

    await expect(
      client.submitTaskResult(
        "task-1",
        {
          result_type: "completed",
          completion_ratio: 100,
          actual_minutes: 45,
          confirmed_at: "2026-07-14T10:00:00.000Z",
        },
        "task-1-completed-100-45",
      ),
    ).resolves.toEqual(payload);
    expect(calls).toHaveLength(1);
    expect(calls[0].input).toBe("/api/v1/tasks/task-1/results");
    expect(calls[0].init?.headers).toMatchObject({
      Accept: "application/json",
      "Content-Type": "application/json",
      "Idempotency-Key": "task-1-completed-100-45",
    });
    expect(JSON.parse(String(calls[0].init?.body))).toMatchObject({
      result_type: "completed",
      completion_ratio: 100,
      actual_minutes: 45,
    });
  });

  it("marks tasks completed through the guarded task update API", async () => {
    const payload: ApiResponse<TaskPayload> = {
      data: {
        id: "task-1",
        version: 3,
        goal_id: "goal-1",
        subject_id: "math",
        knowledge_node_id: null,
        title: "Closed-book recall",
        task_type: "study",
        priority: "must",
        source_type: "goal",
        source_id: "goal-1",
        planned_date: "2026-07-14",
        estimated_minutes: 45,
        current_stage: 2,
        target_stage: 3,
        reason: "Traceable weekly goal",
        completion_standard: "Recall without hints",
        prerequisite_status: "satisfied",
        status: "completed",
      },
      meta: { request_id: "client-task-complete" },
    };
    const calls: Array<{ input: string; init?: RequestInit }> = [];
    const client = new ApiClient("", async (input, init) => {
      calls.push({ input: String(input), init });
      return jsonResponse(payload);
    });

    await expect(client.completeTask("task-1", 2)).resolves.toEqual(payload);
    expect(calls).toHaveLength(1);
    expect(calls[0].input).toBe("/api/v1/tasks/task-1");
    expect(calls[0].init?.method).toBe("PATCH");
    expect(calls[0].init?.headers).toMatchObject({
      Accept: "application/json",
      "Content-Type": "application/json",
      "If-Match": "2",
    });
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ status: "completed" });
  });
});
