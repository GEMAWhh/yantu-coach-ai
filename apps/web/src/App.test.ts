import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import App from "./App.vue";

describe("App", () => {
  it("renders the five primary product entries", () => {
    const wrapper = mount(App);

    expect(wrapper.get('[data-testid="app-title"]').text()).toBe("研途教练");
    expect(wrapper.findAll(".nav-label").map((item) => item.text())).toEqual([
      "今日",
      "规划",
      "学习",
      "进度",
      "设置",
    ]);
  });
});
