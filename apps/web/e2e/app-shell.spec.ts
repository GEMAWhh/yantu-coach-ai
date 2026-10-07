import { expect, test } from "@playwright/test";

const pages = [
  { name: "today", path: "/today", label: "今日", heading: "今日行动" },
  { name: "planning", path: "/planning", label: "规划", heading: "目标与任务" },
  { name: "learning", path: "/learning", label: "学习", heading: "学习中心" },
  { name: "progress", path: "/progress", label: "进度", heading: "学习进展" },
  { name: "settings", path: "/settings", label: "设置", heading: "学习画像与规则" },
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

  test("returns to the top of a long page without manual swiping", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/today");
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    const scrollTopButton = page.getByRole("button", { name: "回到页面顶部" });
    await expect(scrollTopButton).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("scroll-top-mobile.png") });
    await scrollTopButton.click();

    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(10);
  });

  test("records a today outcome without requiring text input", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/today");
    const task = page.locator(".task-card").filter({ hasText: "阅读长难句证据整理" });

    await task.getByRole("button", { name: "完成", exact: true }).click();

    await expect(task.getByText("已完成", { exact: true })).toBeVisible();
    await expect(task.locator(".task-result-form")).toHaveCount(0);
    await task.screenshot({ path: testInfo.outputPath("today-quick-complete-mobile.png") });
  });

  test("exposes editable planning and profile actions on mobile", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/planning");
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    await expect(page.getByLabel("任务名称")).toBeVisible();
    await expect(page.getByLabel("计划日期")).toBeVisible();
    await page.getByRole("button", { name: "保存任务" }).scrollIntoViewIfNeeded();
    await page.screenshot({
      path: testInfo.outputPath("planning-editor-mobile.png"),
    });
    await page.getByLabel("任务名称").fill("E2E 新建任务");
    await page.getByRole("button", { name: "保存任务" }).click();
    await expect(page.getByText("任务已创建。")).toBeVisible();
    await expect(page.getByRole("heading", { name: "E2E 新建任务" })).toBeVisible();
    await page.goto("/settings");
    await page.getByRole("button", { name: "编辑学习画像" }).click();
    await expect(page.getByLabel("目标院校")).toBeVisible();
    await page.getByRole("button", { name: "保存", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({
      path: testInfo.outputPath("settings-editor-mobile.png"),
    });
    await page.getByLabel("目标院校").fill("E2E 目标院校");
    await page.getByRole("button", { name: "保存", exact: true }).click();
    await expect(page.getByText("学习画像已保存。")).toBeVisible();
    await expect(page.getByText("E2E 目标院校")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });

  test("builds, copies, restores, and clears a study prompt on mobile", async (
    { context, page },
    testInfo,
  ) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"], {
      origin: "http://127.0.0.1:5173",
    });
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/learning");
    await page.getByRole("tab", { name: /^提示词/ }).click();
    await page.getByRole("tab", { name: /错因诊断/ }).click();
    await page.getByLabel("科目或主题").fill("数学一 · 导数");
    await page
      .getByLabel("题目或学习材料")
      .fill("含参数函数求极值，标准答案要求分类讨论。");
    await page
      .getByLabel("我的作答或当前情况")
      .fill("我直接令导数为零，没有讨论参数范围。");
    await page.getByRole("button", { name: "生成 Prompt" }).click();

    const finalPrompt = page.getByLabel("最终 Prompt（可继续修改）");
    await expect(finalPrompt).toHaveValue(/当前任务是：错因诊断/);
    await page.getByRole("button", { name: "复制 Prompt" }).click();
    await expect(page.getByText("Prompt 已复制到剪贴板。")).toBeVisible();
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain("不得补造题干、公式、答案或学习事实");

    await page.getByRole("button", { name: "复制 Prompt" }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("prompt-toolbox-mobile.png") });
    await page.reload();
    await expect(page.getByLabel("题目或学习材料")).toHaveValue(
      "含参数函数求极值，标准答案要求分类讨论。",
    );
    await page.getByRole("button", { name: "清空草稿" }).click();
    await page.reload();
    await expect(page.getByLabel("题目或学习材料")).toHaveValue("");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });

  test("manages learning resources and knowledge nodes on mobile", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/learning");
    await page.getByRole("tab", { name: /^资料/ }).click();

    await page.getByLabel("添加资料").setInputFiles({
      name: "极限笔记.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("demo-pdf"),
    });
    await page.getByRole("button", { name: "上传资料" }).click();
    await expect(page.getByText("资料已上传，当前状态为待整理。")).toBeVisible();
    const resourceRow = page.locator(".resource-row").filter({ hasText: "极限笔记.pdf" });
    await expect(resourceRow).toBeVisible();

    await page.getByLabel("名称", { exact: true }).fill("函数极限");
    await page.getByLabel("科目", { exact: true }).fill("数学一");
    await page.getByLabel("编码", { exact: true }).fill("MATH-LIMIT-01");
    await page.getByLabel("说明", { exact: true }).fill("定义、性质与计算方法");
    await page.getByRole("button", { name: "添加知识点" }).click();
    await expect(page.getByText("知识点已添加。")).toBeVisible();

    const node = page.locator(".knowledge-node").filter({ hasText: "函数极限" });
    await node.getByRole("button", { name: "编辑" }).click();
    await page.getByLabel("名称", { exact: true }).fill("函数极限与连续");
    await page.getByRole("button", { name: "保存修改" }).click();
    await expect(page.getByText("知识点已更新。")).toBeVisible();

    await page.getByText("函数极限与连续").scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("learning-management-mobile.png") });
    const updatedNode = page.locator(".knowledge-node").filter({ hasText: "函数极限与连续" });
    await updatedNode.getByRole("button", { name: "删除" }).click();
    await expect(page.getByText("知识点已删除。")).toBeVisible();
    await resourceRow.getByRole("button", { name: "删除" }).click();
    await expect(page.getByText("已删除 极限笔记.pdf。")).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });

  test("creates a remediation task from a weak progress node on mobile", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/progress");

    await page.getByRole("button", { name: "安排复习" }).first().click();
    await expect(page.getByText(/条学习记录/).first()).toBeVisible();
    await page.getByLabel("任务名称").fill("E2E 函数错题复习");
    await page.getByLabel("预计分钟").fill("35");
    await page.getByLabel("完成标准").fill("完成两道无提示练习并提交真实结果。");
    await page.getByRole("button", { name: "确认创建任务" }).scrollIntoViewIfNeeded();
    await page.setViewportSize({ width: 360, height: 1100 });
    await page.screenshot({
      path: testInfo.outputPath("progress-remediation-editor-mobile.png"),
    });
    await page.getByRole("button", { name: "确认创建任务" }).click();

    await expect(page.getByText(/已创建「E2E 函数错题复习」/)).toBeVisible();
    await page.getByRole("link", { name: "查看规划" }).click();
    await expect(page.getByRole("heading", { name: "E2E 函数错题复习" })).toBeVisible();
    await page.locator('.bottom-nav-link[href="/today"]').click();
    await expect(page.getByRole("heading", { name: "E2E 函数错题复习" })).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });

  test("uses the wrongbook as a simple redo queue on mobile", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 900 });
    await page.goto("/learning?section=wrongbook");

    await expect(
      page.getByRole("heading", { name: /今天有 \d+ 道需要重做|今天的错题已经完成/ }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /待分析 1/ })).toBeVisible();
    await page.getByRole("button", { name: "记一道错题" }).click();
    await page.getByLabel("题目内容").fill("E2E：求数列极限并说明使用的判定方法。");
    await page.getByLabel("科目（可选）").fill("数学");
    await page.getByLabel("来源（可选）").fill("今日模拟题");
    await page.setViewportSize({ width: 360, height: 1200 });
    await page.locator(".wrongbook-capture-form").filter({ has: page.getByLabel("题目内容") }).scrollIntoViewIfNeeded();
    await page.screenshot({
      path: testInfo.outputPath("wrongbook-quick-capture-mobile.png"),
    });
    await page.getByRole("button", { name: "保存到错题本" }).click();

    await expect(page.getByText("已记入错题本，接下来分析错因。")).toBeVisible();
    await expect(page.getByRole("button", { name: /待分析 2/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "E2E：求数列极限并说明使用的判定方法。" })).toBeVisible();
    await page.getByLabel("选择图片或 PDF").setInputFiles({
      name: "wrong-question.png", mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3XkAAAAASUVORK5CYII=", "base64"),
    });
    await page.getByRole("button", { name: "保存附件", exact: true }).click();
    await expect(page.getByText("题目 · wrong-question.png")).toBeVisible();
    await page.locator(".attachments").getByRole("button", { name: "查看", exact: true }).click();
    await expect(page.getByAltText("错题附件预览")).toBeVisible();
    await expect.poll(() => page.getByAltText("错题附件预览").evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    await page.locator(".attachments").scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("wrongbook-attachments-mobile.png") });

    await page.getByLabel("哪里做错了").fill("漏掉参数为零的情况");
    await page.getByLabel("为什么会做错").fill("直接套公式，没有分类讨论");
    await page.getByLabel("需要补什么基础").fill("分类讨论");
    await page.getByRole("button", { name: "保存错因草稿" }).click();
    await expect(page.getByText("直接套公式，没有分类讨论", { exact: true })).toBeVisible();
    await page.getByLabel("为什么会做错").fill("没有先检查公式适用条件");
    await expect(page.getByRole("button", { name: "确认错因并安排重做" })).toBeDisabled();
    await page.getByRole("button", { name: "保存错因草稿" }).click();
    await expect(page.getByText("没有先检查公式适用条件", { exact: true })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("wrongbook-manual-causes-mobile.png") });

    await page.getByRole("button", { name: /已知函数 f\(x\)=x³-3ax/ }).click();
    await expect(page.getByText("参数范围遗漏", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "确认错因并安排重做" }).click();

    await expect(page.getByRole("button", { name: "这次做对了" })).toBeVisible();
    await expect(page.locator(".wrongbook-result-kind")).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("wrongbook-task-queue-mobile.png"), fullPage: true });
    await page.getByRole("button", { name: "这次做对了" }).click();
    await expect(page.getByText(/结果已保存/)).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });
});
