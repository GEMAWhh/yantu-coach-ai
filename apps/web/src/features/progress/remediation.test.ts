import { describe, expect, it } from "vitest";

import type { WeakNodePayload } from "../../api/contracts";
import {
  remediationDraft,
  remediationTaskPayload,
  validateRemediationDraft,
} from "./remediation";

const node: WeakNodePayload = {
  object_type: "knowledge_node",
  object_id: "node-limit",
  label: "函数极限",
  subject_id: "数学一",
  latest_stage: 2,
  evidence_count: 3,
  repeat_error_rate: 40,
  blocking_reasons: ["缺少无提示练习", "重复错因"],
};

describe("progress remediation task", () => {
  it("prefills a traceable task without changing mastery", () => {
    const draft = remediationDraft(node, "2026-09-26");
    const payload = remediationTaskPayload(node, draft);

    expect(draft.priority).toBe("high");
    expect(payload).toMatchObject({
      source_type: "manual",
      source_id: "node-limit",
      knowledge_node_id: "node-limit",
      task_type: "remediation",
      prerequisite_status: "unknown",
    });
    expect(payload.completion_standard).toContain("不直接代表稳定掌握");
  });

  it("rejects past dates and unsafe duration values", () => {
    const draft = remediationDraft(node, "2026-09-25");
    expect(validateRemediationDraft(draft, "2026-09-26")).toContain("不能早于今天");
    draft.plannedDate = "2026-09-26";
    draft.estimatedMinutes = 0;
    expect(validateRemediationDraft(draft, "2026-09-26")).toContain("5 到 240");
  });
});
