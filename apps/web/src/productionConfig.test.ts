import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function productionEnvironment(): Map<string, string> {
  const source = readFileSync(".env.production", "utf8");
  const entries = source
    .split(/\r?\n/u)
    .filter((line) => line.trim() !== "")
    .map((line) => {
      const separator = line.indexOf("=");
      return [line.slice(0, separator), line.slice(separator + 1)] as const;
    });
  return new Map(entries);
}

describe("production deployment configuration", () => {
  it("uses the authenticated Render API instead of demo data", () => {
    const environment = productionEnvironment();

    expect(environment.get("VITE_YANTU_DEMO_API")).toBe("false");
    expect(environment.get("VITE_YANTU_AUTH_REQUIRED")).toBe("true");
    expect(environment.get("VITE_YANTU_API_BASE_URL")).toBe(
      "https://yantu-coach-api.onrender.com",
    );
    expect([...environment.keys()].some((key) => /token|secret|password/iu.test(key))).toBe(false);
  });
});
