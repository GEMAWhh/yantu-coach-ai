import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PromptToolbox from "./PromptToolbox.vue";

const STORAGE_KEY = "yantu.studyPromptDraft.v1";
const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll("button").find((item) => item.text().includes(text));
  if (!button) throw new Error(`button not found: ${text}`);
  return button;
}

describe("PromptToolbox", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
    if (originalClipboard) {
      Object.defineProperty(navigator, "clipboard", originalClipboard);
    } else {
      Reflect.deleteProperty(navigator, "clipboard");
    }
  });

  it("generates an editable prompt and copies it", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const wrapper = mount(PromptToolbox);

    await buttonByText(wrapper, "错因诊断").trigger("click");
    await wrapper.findAll("input")[0].setValue("数学一 · 导数");
    await wrapper.findAll("textarea")[0].setValue("求函数极值，标准答案使用分类讨论。");
    await wrapper.findAll("textarea")[1].setValue("我直接令导数为零，没有讨论参数范围。");
    await wrapper.get("form").trigger("submit");

    const finalPrompt = wrapper.find<HTMLTextAreaElement>("#final-study-prompt");
    expect(finalPrompt.element.value).toContain("当前任务是：错因诊断");
    expect(finalPrompt.element.value).toContain("不得补造题干、公式、答案或学习事实");

    await buttonByText(wrapper, "复制 Prompt").trigger("click");
    await flushPromises();
    expect(writeText).toHaveBeenCalledWith(finalPrompt.element.value);
    expect(wrapper.text()).toContain("Prompt 已复制到剪贴板");
  });

  it("shows a recoverable message when clipboard access fails", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    const wrapper = mount(PromptToolbox);
    await wrapper.find("#final-study-prompt").setValue("手动编写的 Prompt");

    await buttonByText(wrapper, "复制 Prompt").trigger("click");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain("手动复制");
  });

  it("restores and clears the local draft", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        templateId: "daily-review",
        subject: "数学一",
        material: "今日完成 2 项任务",
        attempt: "级数题仍然出错",
        focus: "明天保留机动时间",
        finalPrompt: "已保存的最终 Prompt",
      }),
    );

    const wrapper = mount(PromptToolbox);
    await flushPromises();
    expect(wrapper.findAll("input")[0].element.value).toBe("数学一");
    expect(wrapper.find<HTMLTextAreaElement>("#final-study-prompt").element.value).toBe(
      "已保存的最终 Prompt",
    );

    await buttonByText(wrapper, "清空草稿").trigger("click");
    await flushPromises();
    expect(wrapper.find<HTMLTextAreaElement>("#final-study-prompt").element.value).toBe("");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("reports when an external chat window is blocked", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    const wrapper = mount(PromptToolbox);

    await buttonByText(wrapper, "DeepSeek").trigger("click");

    expect(window.open).toHaveBeenCalledWith("about:blank", "_blank");
    expect(wrapper.get('[role="alert"]').text()).toContain("浏览器阻止了新窗口");
  });

  it("opens an external chat without passing prompt content", async () => {
    const opened = {
      opener: window,
      location: { href: "about:blank" },
    } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(opened);
    const wrapper = mount(PromptToolbox);

    await buttonByText(wrapper, "Kimi").trigger("click");

    expect(opened.opener).toBeNull();
    expect(opened.location.href).toBe("https://www.kimi.ai/");
    expect(opened.location.href).not.toContain("prompt");
    expect(wrapper.text()).toContain("请手动粘贴 Prompt");
  });
});
