import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import PersonalAccessGate from "./PersonalAccessGate.vue";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("PersonalAccessGate", () => {
  afterEach(() => {
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("verifies and keeps a valid access key for the browser session", async () => {
    const accessKey = "personal-access-key-with-at-least-32-characters";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${accessKey}`);
        return jsonResponse({
          data: { authenticated: true, mode: "personal_token" },
          meta: { request_id: "auth-valid" },
        });
      }),
    );
    const wrapper = mount(PersonalAccessGate);

    await wrapper.get("input").setValue(accessKey);
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.emitted("unlocked")).toHaveLength(1);
    expect(window.sessionStorage.getItem("yantu.personalAccessKey")).toBe(accessKey);
  });

  it("clears an invalid access key and explains the failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          {
            error: {
              code: "AUTHENTICATION_REQUIRED",
              message: "A valid personal access key is required",
              details: null,
              request_id: "auth-invalid",
            },
          },
          401,
        ),
      ),
    );
    const wrapper = mount(PersonalAccessGate);

    await wrapper.get("input").setValue("wrong-access-key-with-at-least-32-characters");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.emitted("unlocked")).toBeUndefined();
    expect(wrapper.get('[role="alert"]').text()).toContain("访问密钥不正确");
    expect(window.sessionStorage.getItem("yantu.personalAccessKey")).toBeNull();
  });
});
