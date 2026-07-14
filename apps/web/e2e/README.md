# Playwright baselines

`npm run test:e2e` opens each primary route at 1280px desktop and 360px mobile widths. The test writes a desktop and mobile PNG per page into Playwright `test-results` using `*-baseline.png` names, then checks that the 360px viewport has no horizontal overflow.

The planning route also checks that the mobile UI exposes the buffer-time signal and the single-subject constraint text, so PLAN-004 and PLAN-005 remain visible in the prototype shell.

The `baselines/` directory stores the current accepted reference PNGs for human review. The E2E test intentionally generates fresh screenshots instead of doing strict pixel comparison because local Windows and CI Linux font rasterization can differ before the design system is stable.
