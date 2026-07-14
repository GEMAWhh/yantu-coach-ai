import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
});
