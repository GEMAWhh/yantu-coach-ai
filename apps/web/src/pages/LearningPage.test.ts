import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import LearningPage from "./LearningPage.vue";

describe("LearningPage management forms", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/learning");
  });

  it("opens with review work only and switches between focused workspaces", async () => {
    const wrapper = mount(LearningPage, { global: { plugins: [createPinia()] } });

    expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toContain("复习");
    expect(wrapper.get("#learning-panel-review").attributes("style") ?? "").not.toContain("display: none");
    expect(wrapper.get("#learning-panel-materials").attributes("style")).toContain("display: none");
    expect(wrapper.get("#learning-panel-prompt").attributes("style")).toContain("display: none");

    await wrapper.get("#learning-tab-materials").trigger("click");

    expect(wrapper.get("#learning-panel-review").attributes("style")).toContain("display: none");
    expect(wrapper.get("#learning-panel-materials").attributes("style") ?? "").not.toContain("display: none");
    expect(window.location.search).toBe("?section=materials");

    await wrapper.get<HTMLInputElement>('input[required][maxlength="200"]').setValue("未提交知识点");
    await wrapper.get("#learning-tab-prompt").trigger("click");
    await wrapper.get("#learning-tab-materials").trigger("click");

    expect(wrapper.get<HTMLInputElement>('input[required][maxlength="200"]').element.value).toBe(
      "未提交知识点",
    );
  });

  it("rejects unsupported learning resource files before upload", async () => {
    const wrapper = mount(LearningPage, { global: { plugins: [createPinia()] } });
    await wrapper.get("#learning-tab-materials").trigger("click");
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
    await wrapper.get("#learning-tab-materials").trigger("click");
    await wrapper.find(".knowledge-editor").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("名称、编码和科目不能为空。");
  });
});
