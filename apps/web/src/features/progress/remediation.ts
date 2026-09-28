import type { TaskCreatePayload, WeakNodePayload } from "../../api/contracts";

export type RemediationDraft = {
  title: string;
  plannedDate: string;
  estimatedMinutes: number;
  priority: string;
  reason: string;
  completionStandard: string;
};

const PLAIN_REASON_LABELS: Record<string, string> = {
  "缺少变式通过": "还需要做对同类题",
  "参数范围遗漏复现": "参数范围仍会遗漏",
  "间隔复测未完成": "之后复习还没完成",
  "缺少无提示练习": "还没有不看提示重做",
};

export function learningReasonLabel(reason: string): string {
  return PLAIN_REASON_LABELS[reason] ?? reason;
}

export function remediationDraft(
  node: WeakNodePayload,
  plannedDate: string,
): RemediationDraft {
  const blockerText =
    node.blocking_reasons.length > 0
      ? node.blocking_reasons.map(learningReasonLabel).join("；")
      : "现有证据不足，需要补充独立练习结果";
  return {
    title: `复习：${node.label}`,
    plannedDate,
    estimatedMinutes: node.blocking_reasons.length > 1 ? 40 : 30,
    priority: (node.repeat_error_rate ?? 0) >= 30 ? "high" : "normal",
    reason: `当前阶段：${node.latest_stage}；已有 ${node.evidence_count} 条证据；阻塞原因：${blockerText}。`,
    completionStandard: "完成一次无提示练习并提交真实结果；本任务完成不直接代表稳定掌握。",
  };
}

export function remediationTaskPayload(
  node: WeakNodePayload,
  draft: RemediationDraft,
): TaskCreatePayload {
  return {
    title: draft.title.trim(),
    planned_date: draft.plannedDate,
    estimated_minutes: draft.estimatedMinutes,
    source_type: "manual",
    source_id: node.object_id,
    subject_id: node.subject_id,
    knowledge_node_id: node.object_id,
    task_type: "remediation",
    priority: draft.priority,
    reason: draft.reason.trim(),
    completion_standard: draft.completionStandard.trim(),
    prerequisite_status: "unknown",
  };
}

export function validateRemediationDraft(
  draft: RemediationDraft,
  today: string,
): string | null {
  if (!draft.title.trim()) return "请填写任务名称。";
  if (!draft.plannedDate) return "请选择计划日期。";
  if (draft.plannedDate < today) return "计划日期不能早于今天。";
  if (!Number.isInteger(draft.estimatedMinutes) || draft.estimatedMinutes < 5 || draft.estimatedMinutes > 240) {
    return "预计时长应为 5 到 240 分钟的整数。";
  }
  if (!draft.reason.trim()) return "请说明为什么需要这次复习。";
  if (!draft.completionStandard.trim()) return "请填写可验证的完成标准。";
  return null;
}
