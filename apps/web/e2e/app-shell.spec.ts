import { expect, test } from "@playwright/test";

const pages = [
  { name: "today", path: "/today", label: "今日", heading: "今日行动" },
  { name: "planning", path: "/planning", label: "规划", heading: "五层规划" },
  { name: "learning", path: "/learning", label: "学习", heading: "资料与知识单元" },
  { name: "progress", path: "/progress", label: "进度", heading: "掌握与风险" },
  { name: "settings", path: "/settings", label: "设置", heading: "规则与数据安全" },
];

test.describe("Vue prototype shell", () => {
  for (const pageSpec of pages) {
    test(`${pageSpec.label} route renders desktop and mobile baselines`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(pageSpec.path);
      await expect(page.getByRole("heading", { name: pageSpec.heading, level: 1 })).toBeVisible();
      const activeNavLink = page.locator(`[data-testid="primary-nav-link"][href="${pageSpec.path}"]`);
      await expect(activeNavLink).toHaveAttribute("aria-current", "page");
      await page.screenshot({
        path: testInfo.outputPath(`${pageSpec.name}-desktop-baseline.png`),
        fullPage: true,
      });

      await page.setViewportSize({ width: 360, height: 800 });
      await page.goto(pageSpec.path);
      await expect(page.getByRole("heading", { name: pageSpec.heading, level: 1 })).toBeVisible();
      await page.screenshot({
        path: testInfo.outputPath(`${pageSpec.name}-mobile-360-baseline.png`),
        fullPage: true,
      });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      expect(overflow).toBe(false);
    });
  }

  test("supports basic keyboard navigation across primary entries", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/today");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await expect(page.locator(".nav-link").first()).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/today$/);
  });
});
