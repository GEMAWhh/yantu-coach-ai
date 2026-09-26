import type { TaskCreatePayload, WeakNodePayload } from "../../api/contracts";

export type RemediationDraft = {
  title: string;
  plannedDate: string;
  estimatedMinutes: number;
  priority: string;
  reason: string;
  completionStandard: string;
};

export function remediationDraft(
  node: WeakNodePayload,
  plannedDate: string,
): RemediationDraft {
  const blockerText =
    node.blocking_reasons.length > 0
      ? node.blocking_reasons.join("；")
      : "现有证据不足，需要补充独立练习结果";
  return {
    title: `补救：${node.label}`,
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
  if (!draft.reason.trim()) return "请保留可追溯的补救原因。";
  if (!draft.completionStandard.trim()) return "请填写可验证的完成标准。";
  return null;
}
