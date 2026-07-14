import { describe, expect, it } from "vitest";

import { ApiClient } from "./client";
import type { ApiResponse, HealthPayload } from "./contracts";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient", () => {
  it("calls health with typed response data", async () => {
    const payload: ApiResponse<HealthPayload> = {
      data: {
        status: "ok",
        service: "yantu-coach-api",
        environment: "test",
        data_root: "data/test",
      },
      meta: { request_id: "client-health" },
    };
    const calls: string[] = [];
    const client = new ApiClient("http://127.0.0.1:8000", async (input) => {
      calls.push(String(input));
      return jsonResponse(payload);
    });

    await expect(client.health()).resolves.toEqual(payload);
    expect(calls).toEqual(["http://127.0.0.1:8000/health"]);
  });

  it("raises typed errors from the unified error envelope", async () => {
    const client = new ApiClient("", async () =>
      jsonResponse(
        {
          error: {
            code: "VERSION_CONFLICT",
            message: "Resource version conflict",
            details: { expected: "contract-v1", received: "old-contract" },
            request_id: "client-409",
          },
        },
        409,
      ),
    );

    await expect(client.meta()).rejects.toMatchObject({
      status: 409,
      error: {
        code: "VERSION_CONFLICT",
        request_id: "client-409",
      },
    });
  });
});
