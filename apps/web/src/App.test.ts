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

describe("App", () => {
  beforeEach(() => {
    window.scrollTo = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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
  });

  it("starts a today task through the guarded task action API", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
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
      expect.stringMatching(/^\/api\/v1\/today\?date=/),
      "/api/v1/tasks/task-api-1/start",
    ]);
    expect(calls[1].init?.headers).toMatchObject({ "If-Match": "1" });
    expect(wrapper.text()).toContain("in_progress");
  });

  it("submits a default result and marks a today task completed", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        calls.push({ path, init });
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
    await flushPromises();

    expect(calls.map((call) => call.path)).toEqual([
      expect.stringMatching(/^\/api\/v1\/today\?date=/),
      "/api/v1/tasks/task-api-1/results",
      "/api/v1/tasks/task-api-1",
    ]);
    expect(calls[1].init?.headers).toMatchObject({
      "Idempotency-Key": "task-api-1:complete:1",
    });
    expect(JSON.parse(String(calls[1].init?.body))).toMatchObject({
      result_type: "completed",
      completion_ratio: 100,
      actual_minutes: 45,
    });
    expect(calls[2].init?.method).toBe("PATCH");
    expect(calls[2].init?.headers).toMatchObject({ "If-Match": "1" });
    expect(wrapper.text()).toContain("completed");
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
  });
});
