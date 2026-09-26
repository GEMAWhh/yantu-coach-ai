import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProgressPage from "./ProgressPage.vue";

const api = vi.hoisted(() => ({
  createTask: vi.fn(),
}));

vi.mock("../api/client", () => ({
  ApiClientError: class ApiClientError extends Error {},
  ApiClient: class ApiClient {
    analyticsMastery() {
      return Promise.resolve({ data: { latest_snapshot_count: 1, weak_node_count: 1, stage_distribution: [] } });
    }
    analyticsErrors() {
      return Promise.resolve({ data: { total_wrong_records: 0, by_status: [], by_knowledge_node: [] } });
    }
    analyticsTime() {
      return Promise.resolve({ data: { estimated_minutes: 30, actual_minutes: 30, by_subject: [] } });
    }
    analyticsGoalRisk() {
      return Promise.resolve({ data: { total_goals: 0, by_risk_status: [], risky_goals: [] } });
    }
    weakGraph() {
      return Promise.resolve({
        data: {
          total: 1,
          items: [{
            object_type: "knowledge_node", object_id: "node-1", label: "函数极限",
            subject_id: "数学一", latest_stage: 2, evidence_count: 2,
            repeat_error_rate: 50, blocking_reasons: ["重复错因"],
          }],
        },
      });
    }
    createTask(payload: unknown) {
      return api.createTask(payload);
    }
  },
}));

describe("ProgressPage remediation editor", () => {
  beforeEach(() => {
    api.createTask.mockReset();
  });

  it("keeps the form editable when task creation fails", async () => {
    api.createTask.mockRejectedValue(new Error("offline"));
    const wrapper = mount(ProgressPage, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: { template: "<a><slot /></a>" } },
      },
    });
    await flushPromises();

    const createButton = wrapper.findAll("button").find((button) => button.text() === "创建补救任务");
    if (!createButton) throw new Error("remediation action missing");
    await createButton.trigger("click");
    const title = wrapper.get<HTMLInputElement>('input[maxlength="240"]');
    await title.setValue("保留的补救任务");
    await wrapper.get(".remediation-editor").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("补救任务创建失败");
    expect(title.element.value).toBe("保留的补救任务");
    expect(api.createTask).toHaveBeenCalledTimes(1);
  });
});
