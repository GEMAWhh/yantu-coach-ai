import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import LearningPage from "./LearningPage.vue";

describe("LearningPage management forms", () => {
  it("rejects unsupported learning resource files before upload", async () => {
    const wrapper = mount(LearningPage, { global: { plugins: [createPinia()] } });
    const input = wrapper.get<HTMLInputElement>('input[type="file"]');
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["text"], "notes.txt", { type: "text/plain" })],
    });
    await input.trigger("change");
    await wrapper.find(".learning-manager-form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("仅支持 PNG、JPEG 和 PDF 文件。");
  });

  it("requires user-facing knowledge fields before creating a node", async () => {
    const wrapper = mount(LearningPage, { global: { plugins: [createPinia()] } });
    await wrapper.find(".knowledge-editor").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("名称、编码和科目不能为空。");
  });
});
