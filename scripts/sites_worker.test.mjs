import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import test from "node:test";

import { renderSitesWorker } from "./sites_worker.mjs";

const API_ORIGIN = "https://yantu-coach-api.onrender.com";

async function loadWorker() {
  const source = renderSitesWorker(API_ORIGIN);
  return import(`data:text/javascript,${encodeURIComponent(source)}#${randomUUID()}`);
}

test("proxies API requests to the fixed Render origin", async (context) => {
  const originalFetch = globalThis.fetch;
  let capturedRequest;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (request) => {
    capturedRequest = request;
    return new Response("proxied", { status: 200 });
  };
  const worker = await loadWorker();
  const request = new Request("https://study.example.com/api/v1/auth/status?probe=1", {
    method: "POST",
    headers: {
      Authorization: "Bearer test-access-key",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ check: true }),
  });

  const response = await worker.default.fetch(request, {
    ASSETS: { fetch: () => new Response(null, { status: 404 }) },
  });

  assert.equal(await response.text(), "proxied");
  assert.ok(capturedRequest instanceof Request);
  assert.equal(capturedRequest.url, `${API_ORIGIN}/api/v1/auth/status?probe=1`);
  assert.equal(capturedRequest.method, "POST");
  assert.equal(capturedRequest.headers.get("authorization"), "Bearer test-access-key");
  assert.equal(await capturedRequest.text(), JSON.stringify({ check: true }));
});

test("serves assets and SPA fallback without using the API proxy", async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () => {
    throw new Error("static routes must not use the API proxy");
  };
  const requestedPaths = [];
  const worker = await loadWorker();
  const response = await worker.default.fetch(new Request("https://study.example.com/today"), {
    ASSETS: {
      fetch(request) {
        requestedPaths.push(new URL(request.url).pathname);
        return requestedPaths.length === 1
          ? new Response(null, { status: 404 })
          : new Response("spa", { status: 200 });
      },
    },
  });

  assert.equal(await response.text(), "spa");
  assert.deepEqual(requestedPaths, ["/today", "/index.html"]);
});

test("rejects unsafe proxy origins", () => {
  assert.throws(() => renderSitesWorker("http://api.example.com"), /requires HTTPS/u);
  assert.throws(() => renderSitesWorker("https://api.example.com/path"), /without a path/u);
});
