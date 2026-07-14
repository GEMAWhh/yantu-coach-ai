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
});
