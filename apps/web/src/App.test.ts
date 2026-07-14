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
});
