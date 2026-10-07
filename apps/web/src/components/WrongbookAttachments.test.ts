import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";
import WrongbookAttachments from "./WrongbookAttachments.vue";

afterEach(() => vi.restoreAllMocks());
describe("wrongbook attachments", () => {
  async function setup(type: string) {
    vi.spyOn(ApiClient.prototype, "wrongbookAttachments").mockResolvedValue({ data: { items: [], total: 0 } } as never);
    const wrapper = mount(WrongbookAttachments, { props: { recordId: "wrong-1" } });
    const input = wrapper.get('input[type="file"]');
    Object.defineProperty(input.element, "files", { value: [new File(["test"], "proof.png", { type })] });
    await input.trigger("change");
    await flushPromises();
    return wrapper;
  }
  it("rejects unsupported files without uploading", async () => {
    const upload = vi.spyOn(ApiClient.prototype, "uploadAsset");
    const wrapper = await setup("text/plain");
    await wrapper.get("form").trigger("submit");
    expect(upload).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请选择 PNG");
  });
  it("reuses an uploaded asset when linking is retried", async () => {
    const upload = vi.spyOn(ApiClient.prototype, "uploadAsset").mockResolvedValue({ data: { id: "asset-1" } } as never);
    const link = vi.spyOn(ApiClient.prototype, "linkWrongbookAttachment").mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({} as never);
    const wrapper = await setup("image/png");
    await wrapper.get("select").setValue("my_answer");
    await wrapper.get("form").trigger("submit");
    await vi.waitFor(() => expect(wrapper.text()).toContain("文件已保留"));
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(upload).toHaveBeenCalledTimes(1);
    expect(link).toHaveBeenLastCalledWith("wrong-1", { asset_id: "asset-1", asset_role: "my_answer", page_order: 0 });
    expect(wrapper.text()).toContain("附件已保存");
  });
});
