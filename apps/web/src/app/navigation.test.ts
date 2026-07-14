import { describe, expect, it } from "vitest";

import { primaryNavItems } from "./navigation";

describe("primaryNavItems", () => {
  it("keeps the five product routes reachable and unique", () => {
    expect(primaryNavItems.map((item) => item.label)).toEqual(["今日", "规划", "学习", "进度", "设置"]);
    expect(new Set(primaryNavItems.map((item) => item.path)).size).toBe(5);
  });
});
