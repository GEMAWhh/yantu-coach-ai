import { describe, expect, it } from "vitest";

import { ApiClient } from "./client";
import type { ApiResponse, HealthPayload, SettingsRulesPayload, TodayPayload } from "./contracts";

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
});
