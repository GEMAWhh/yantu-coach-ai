import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";
import type { WrongbookDraftHistoryItemPayload } from "../api/contracts";
import WrongbookCauseEditor from "./WrongbookCauseEditor.vue";

const item = {
  record: { id: "wrong-1", surface_cause: null, deep_cause: null, prerequisite_gap: null },
  draft: null,
} as unknown as WrongbookDraftHistoryItemPayload;

afterEach(() => vi.restoreAllMocks());

describe("manual wrong-question causes", () => {
  it("rejects empty causes without saving", async () => {
    const save = vi.spyOn(ApiClient.prototype, "saveManualWrongbookDraft");
    const wrapper = mount(WrongbookCauseEditor, { props: { item } });
    await wrapper.get("form").trigger("submit");
    expect(save).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请填写三项错因");
  });

  it("saves only a manual draft and keeps input on failure", async () => {
    const save = vi.spyOn(ApiClient.prototype, "saveManualWrongbookDraft")
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { draft: { status: "draft" } } } as never);
    const confirm = vi.spyOn(ApiClient.prototype, "confirmWrongbookDraft");
    const wrapper = mount(WrongbookCauseEditor, { props: { item } });
    const inputs = wrapper.findAll("textarea");
    await inputs[0].setValue("漏情况");
    await inputs[1].setValue("未分类讨论");
    await inputs[2].setValue("暂无");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("输入已保留");
    expect(inputs[0].element.value).toBe("漏情况");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(save).toHaveBeenLastCalledWith("wrong-1", {
      surface_cause: "漏情况", deep_cause: "未分类讨论", prerequisite_gap: "暂无",
      remediation_plan: [], uncertain_fields: [],
    });
    expect(wrapper.emitted("saved")).toEqual([["wrong-1"]]);
    expect(confirm).not.toHaveBeenCalled();
  });
});
