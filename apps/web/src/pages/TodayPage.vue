<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type {
  EvidenceAssetPayload,
  EvidenceDraftPayload,
  EvidenceFileUploadPayload,
  EvidenceHistoryItemPayload,
  EvidenceRecordPayload,
  TaskPayload,
  TaskResultCreatePayload,
  TodayPayload,
} from "../api/contracts";
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type TodayTask, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiToday = ref<TodayPayload | null>(null);
const actionInFlight = ref<string | null>(null);
const actionError = ref<string | null>(null);
const openResultTaskId = ref<string | null>(null);
const resultDrafts = ref<Record<string, TaskResultDraft>>({});
const evidenceRecord = ref<EvidenceRecordPayload | null>(null);
const evidenceDraft = ref<EvidenceDraftPayload | null>(null);
const evidenceFileInput = ref<HTMLInputElement | null>(null);
const selectedEvidenceFiles = ref<File[]>([]);
const evidenceSubjectId = ref("math");
const evidenceHistory = ref<EvidenceHistoryItemPayload[] | null>(null);
const evidenceAssets = ref<EvidenceAssetPayload[]>([]);
const evidenceActionInFlight = ref<"upload" | "analyze" | "confirm" | "reject" | "delete" | null>(null);
const openingEvidenceAssetId = ref<string | null>(null);
const evidenceActionError = ref<string | null>(null);
const evidenceHistoryError = ref<string | null>(null);
const taskSourceLabel = computed(() => (apiToday.value ? "正式数据" : "模拟数据"));
const taskSourceTone = computed<Tone>(() => (apiToday.value ? "green" : "cyan"));
const todayTasks = computed<TodayTaskView[]>(() =>
  apiToday.value
    ? apiToday.value.tasks.map(mapTask)
    : study.todayTasks.map((task) => ({
        ...task,
        version: null,
        apiBacked: false,
      })),
);
const todayMetrics = computed(() => [
  {
    label: "今日任务",
    value: `${apiToday.value?.total_tasks ?? 4} 项`,
    detail: `预计 ${apiToday.value?.estimated_minutes ?? 125} 分钟`,
    tone: "blue" as Tone,
  },
  {
    label: "机动时间",
    value: apiToday.value ? "按计划规则保留" : "35 分钟",
    detail: "计划不排满全天",
    tone: "green" as Tone,
  },
  {
    label: "待确认草稿",
    value: `${pendingEvidenceDraftCount.value} 份`,
    detail: evidenceRecord.value
      ? `证据记录 ${evidenceRecordStatusLabel(evidenceRecord.value.status)}`
      : "确认前不写正式记录",
    tone: "yellow" as Tone,
  },
]);
const evidenceSourceLabel = computed(() => (evidenceRecord.value ? "记录详情" : "新建证据"));
const evidenceSourceTone = computed<Tone>(() => (evidenceRecord.value ? "green" : "blue"));
const pendingEvidenceDraftCount = computed(() =>
  evidenceHistory.value
    ? evidenceHistory.value.filter((item) => item.draft?.status === "draft").length
    : evidenceDraft.value?.status === "draft"
      ? 1
      : 0,
);
const evidenceCardTitle = computed(() =>
  evidenceDraft.value
    ? evidenceDraftTitle(evidenceDraft.value)
    : evidenceRecord.value
      ? `${formatEvidenceHistoryDate(evidenceRecord.value.study_date)} 证据记录`
      : "上传学习证据",
);
const evidenceCardBody = computed(() => {
  if (!evidenceDraft.value) {
    if (evidenceRecord.value) {
      return `已保存 ${evidenceRecord.value.asset_count} 个原始附件，尚未分析。`;
    }
    if (selectedEvidenceFiles.value.length > 0) {
      return `已选择 ${selectedEvidenceFiles.value.length} 个证据文件，上传分析前不会写入正式学习记录。`;
    }
    return "上传图片或 PDF 后生成待确认草稿；确认前不更新掌握判定和后续计划。";
  }
  return evidenceDraftSummary(evidenceDraft.value);
});
const evidenceAnalysisSections = computed(() => {
  if (!evidenceDraft.value) {
    return [];
  }
  const structured = evidenceDraft.value.structured_json;
  return [
    {
      key: "confirmed_facts",
      title: "可见事实",
      description: "模型从原始证据中直接读取的内容，确认前仍不是正式记录。",
      items: evidenceObjectItems(structured.confirmed_facts),
    },
    {
      key: "inferences",
      title: "推断",
      description: "模型的解释或归纳，可能需要你修正。",
      items: evidenceObjectItems(structured.inferences),
    },
    {
      key: "uncertain_fields",
      title: "不确定项",
      description: "图片遮挡、内容冲突或置信度不足的字段。",
      items: evidenceListItems(structured.uncertain_fields),
    },
    {
      key: "teaching_judgment",
      title: "教学判断",
      description: "基于证据形成的诊断、依据与风险。",
      items: evidenceObjectItems(structured.teaching_judgment),
    },
    {
      key: "suggested_actions",
      title: "建议动作",
      description: "仅供确认，不会自动修改计划或掌握状态。",
      items: evidenceListItems(structured.suggested_actions),
    },
  ];
});
const evidenceValidationMessages = computed(() =>
  (evidenceDraft.value?.validation_errors ?? []).map((error) => ({
    code: error,
    message: evidenceValidationMessage(error),
  })),
);

type TodayTaskView = TodayTask & {
  version: number | null;
  apiBacked: boolean;
};

type TaskResultDraft = {
  completionRatio: number;
  actualMinutes: number;
  questionCount: number | null;
  correctCount: number | null;
  confidence: number | null;
  problemDescription: string;
};

function toneForStatus(status: TaskPayload["status"]): Tone {
  if (status === "completed") {
    return "green";
  }
  if (status === "skipped" || status === "withdrawn") {
    return "red";
  }
  if (status === "in_progress") {
    return "blue";
  }
  return "neutral";
}

function mapTask(task: TaskPayload): TodayTaskView {
  return {
    id: task.id,
    version: task.version,
    apiBacked: true,
    subject: task.subject_id ?? task.task_type,
    title: task.title,
    source: `${task.source_type}${task.source_id ? ` / ${task.source_id}` : ""}`,
    reason: task.reason ?? task.completion_standard ?? "待补充执行理由",
    estimateMinutes: task.estimated_minutes,
    status: task.status,
    tone: toneForStatus(task.status),
  };
}

function isActionRunning(task: TodayTaskView, action: string): boolean {
  return actionInFlight.value === `${task.id}:${action}`;
}

function canStart(task: TodayTaskView): boolean {
  return task.apiBacked && task.status === "pending";
}

function canSkip(task: TodayTaskView): boolean {
  return task.apiBacked && (task.status === "pending" || task.status === "in_progress");
}

function canWithdraw(task: TodayTaskView): boolean {
  return task.apiBacked && task.status !== "completed" && task.status !== "withdrawn";
}

function canComplete(task: TodayTaskView): boolean {
  return task.apiBacked && (task.status === "pending" || task.status === "in_progress");
}

function isResultFormOpen(task: TodayTaskView): boolean {
  return openResultTaskId.value === task.id;
}

function updateTask(updatedTask: TaskPayload): void {
  if (!apiToday.value) {
    return;
  }
  apiToday.value = {
    ...apiToday.value,
    tasks: apiToday.value.tasks.map((task) => (task.id === updatedTask.id ? updatedTask : task)),
  };
}

async function runTaskAction(
  task: TodayTaskView,
  action: "start" | "skip" | "withdraw" | "complete",
): Promise<void> {
  if (!task.apiBacked || task.version === null) {
    return;
  }
  const actionKey = `${task.id}:${action}`;
  const client = new ApiClient();
  actionInFlight.value = actionKey;
  actionError.value = null;
  try {
    if (action === "start") {
      updateTask((await client.startTask(task.id, task.version)).data);
    } else if (action === "skip") {
      updateTask((await client.skipTask(task.id, task.version)).data);
    } else if (action === "withdraw") {
      updateTask((await client.withdrawTask(task.id, task.version)).data);
    } else {
      await client.submitTaskResult(task.id, taskResultPayload(task), resultIdempotencyKey(task));
      updateTask((await client.completeTask(task.id, task.version)).data);
      openResultTaskId.value = null;
    }
  } catch {
    actionError.value = "任务状态更新失败，请刷新后重试。";
  } finally {
    if (actionInFlight.value === actionKey) {
      actionInFlight.value = null;
    }
  }
}

function openResultForm(task: TodayTaskView): void {
  if (!canComplete(task)) {
    return;
  }
  resultDrafts.value = {
    ...resultDrafts.value,
    [task.id]: resultDrafts.value[task.id] ?? defaultTaskResultDraft(task),
  };
  openResultTaskId.value = task.id;
  actionError.value = null;
}

function closeResultForm(): void {
  openResultTaskId.value = null;
}

function resultDraft(task: TodayTaskView): TaskResultDraft {
  return resultDrafts.value[task.id] ?? defaultTaskResultDraft(task);
}

function updateResultDraft<K extends keyof TaskResultDraft>(
  task: TodayTaskView,
  key: K,
  value: TaskResultDraft[K],
): void {
  resultDrafts.value = {
    ...resultDrafts.value,
    [task.id]: {
      ...resultDraft(task),
      [key]: value,
    },
  };
}

function defaultTaskResultDraft(task: TodayTaskView): TaskResultDraft {
  return {
    completionRatio: 100,
    actualMinutes: task.estimateMinutes,
    questionCount: null,
    correctCount: null,
    confidence: null,
    problemDescription: "",
  };
}

function taskResultPayload(task: TodayTaskView): TaskResultCreatePayload {
  const draft = resultDraft(task);
  return {
    result_type: draft.completionRatio >= 100 ? "completed" : "partial",
    completion_ratio: clampPercent(draft.completionRatio),
    actual_minutes: Math.max(0, draft.actualMinutes),
    question_count: draft.questionCount,
    correct_count: draft.correctCount,
    accuracy: accuracyFromCounts(draft),
    confidence: draft.confidence,
    problem_description: draft.problemDescription.trim() || null,
    confirmed_at: new Date().toISOString(),
  };
}

function accuracyFromCounts(draft: TaskResultDraft): number | null {
  if (draft.questionCount === null || draft.correctCount === null || draft.questionCount <= 0) {
    return null;
  }
  return clampPercent(Math.round((draft.correctCount / draft.questionCount) * 100));
}

function clampPercent(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function numberOrNull(value: string): number | null {
  if (value.trim() === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : null;
}

function percentOrNull(value: string): number | null {
  const parsed = numberOrNull(value);
  return parsed === null ? null : clampPercent(parsed);
}

function numberOrZero(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0;
}

function resultIdempotencyKey(task: TodayTaskView): string {
  const draft = resultDraft(task);
  return [
    task.id,
    "complete",
    task.version ?? "mock",
    draft.completionRatio,
    draft.actualMinutes,
    draft.questionCount ?? "na",
    draft.correctCount ?? "na",
  ].join(":");
}

function selectEvidenceFiles(event: Event): void {
  const input = (event.currentTarget ?? event.target) as HTMLInputElement;
  selectedEvidenceFiles.value = Array.from(input.files ?? []);
  evidenceActionError.value = null;
}

async function createEvidenceDraft(): Promise<void> {
  const filesToUpload =
    selectedEvidenceFiles.value.length > 0
      ? selectedEvidenceFiles.value
      : Array.from(evidenceFileInput.value?.files ?? []);
  if (filesToUpload.length === 0) {
    evidenceActionError.value = "请先选择图片或 PDF 证据文件。";
    return;
  }
  const client = new ApiClient();
  evidenceActionInFlight.value = "upload";
  evidenceActionError.value = null;
  try {
    const files = await Promise.all(filesToUpload.map(evidenceFilePayload));
    const upload = await client.uploadEvidence({
      study_date: todayString(),
      subject_id: evidenceSubjectId.value.trim() || null,
      files,
    });
    const analyzed = await client.analyzeEvidence(upload.data.record.id, {
      provider_mode: "valid",
    });
    evidenceRecord.value = upload.data.record;
    evidenceDraft.value = analyzed.data.draft;
    evidenceAssets.value = upload.data.assets;
    selectedEvidenceFiles.value = [];
    await loadEvidenceHistory();
  } catch {
    evidenceActionError.value = "证据草稿生成失败，请刷新后重试。";
  } finally {
    if (evidenceActionInFlight.value === "upload") {
      evidenceActionInFlight.value = null;
    }
  }
}

async function analyzeSelectedEvidence(): Promise<void> {
  if (!evidenceRecord.value) {
    return;
  }
  evidenceActionInFlight.value = "analyze";
  evidenceActionError.value = null;
  try {
    const analyzed = await new ApiClient().analyzeEvidence(evidenceRecord.value.id, {
      provider_mode: "valid",
    });
    evidenceDraft.value = analyzed.data.draft;
    await loadEvidenceHistory();
  } catch {
    evidenceActionError.value = "证据分析失败，请稍后重试。";
  } finally {
    if (evidenceActionInFlight.value === "analyze") {
      evidenceActionInFlight.value = null;
    }
  }
}

async function openEvidenceAsset(asset: EvidenceAssetPayload): Promise<void> {
  openingEvidenceAssetId.value = asset.id;
  evidenceActionError.value = null;
  try {
    const response = await new ApiClient().evidenceAssetContent(asset.id);
    const binary = atob(response.data.content_base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    const url = URL.createObjectURL(new Blob([bytes], { type: asset.mime_type }));
    const opened = window.open(url, "_blank", "noopener,noreferrer");
    if (!opened) {
      URL.revokeObjectURL(url);
      evidenceActionError.value = "浏览器阻止了附件窗口，请允许弹出窗口后重试。";
      return;
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch {
    evidenceActionError.value = "附件读取失败，请稍后重试。";
  } finally {
    openingEvidenceAssetId.value = null;
  }
}

async function deleteEvidenceHistory(item: EvidenceHistoryItemPayload): Promise<void> {
  if (item.record.status === "confirmed") {
    return;
  }
  if (!window.confirm("删除这条证据记录及其未被其他记录使用的附件？此操作无法撤销。")) {
    return;
  }
  evidenceActionInFlight.value = "delete";
  evidenceActionError.value = null;
  try {
    await new ApiClient().deleteEvidence(item.record.id);
    if (evidenceRecord.value?.id === item.record.id) {
      resetEvidenceSelection();
    }
    await loadEvidenceHistory();
  } catch {
    evidenceActionError.value = "证据记录删除失败，请刷新后重试。";
  } finally {
    if (evidenceActionInFlight.value === "delete") {
      evidenceActionInFlight.value = null;
    }
  }
}

function resetEvidenceSelection(): void {
  evidenceRecord.value = null;
  evidenceDraft.value = null;
  evidenceAssets.value = [];
  evidenceActionError.value = null;
}

async function confirmEvidenceDraft(): Promise<void> {
  if (!evidenceDraft.value) {
    return;
  }
  const client = new ApiClient();
  evidenceActionInFlight.value = "confirm";
  evidenceActionError.value = null;
  try {
    const confirmed = await client.confirmEvidenceDraft(evidenceDraft.value.evidence_record_id);
    evidenceRecord.value = confirmed.data.record;
    evidenceDraft.value = confirmed.data.draft;
    await loadEvidenceHistory();
  } catch {
    evidenceActionError.value = "证据草稿确认失败，请刷新后重试。";
  } finally {
    if (evidenceActionInFlight.value === "confirm") {
      evidenceActionInFlight.value = null;
    }
  }
}

async function rejectEvidenceDraft(): Promise<void> {
  if (!evidenceDraft.value) {
    return;
  }
  const client = new ApiClient();
  evidenceActionInFlight.value = "reject";
  evidenceActionError.value = null;
  try {
    const rejected = await client.rejectEvidenceDraft(evidenceDraft.value.evidence_record_id, {
      reason: "用户要求重新整理证据",
    });
    evidenceDraft.value = rejected.data;
    if (evidenceRecord.value) {
      evidenceRecord.value = {
        ...evidenceRecord.value,
        status: "rejected",
        rejected_at: rejected.data.rejected_at,
      };
    }
    await loadEvidenceHistory();
  } catch {
    evidenceActionError.value = "证据草稿驳回失败，请刷新后重试。";
  } finally {
    if (evidenceActionInFlight.value === "reject") {
      evidenceActionInFlight.value = null;
    }
  }
}

function canConfirmEvidence(): boolean {
  return evidenceDraft.value?.status === "draft";
}

function canRejectEvidence(): boolean {
  return evidenceDraft.value?.status === "draft" || evidenceDraft.value?.status === "needs_correction";
}

function evidenceRecordStatusLabel(status: EvidenceRecordPayload["status"]): string {
  const labels: Record<EvidenceRecordPayload["status"], string> = {
    pending: "待确认",
    confirmed: "已确认",
    rejected: "已驳回",
  };
  return labels[status];
}

function evidenceDraftTitle(draft: EvidenceDraftPayload): string {
  if (draft.status === "confirmed") {
    return "证据草稿已确认";
  }
  if (draft.status === "rejected") {
    return "证据草稿已驳回";
  }
  if (draft.status === "needs_correction") {
    return "证据草稿需修正";
  }
  return "待确认证据草稿";
}

function evidenceDraftSummary(draft: EvidenceDraftPayload): string {
  const facts = draft.structured_json.confirmed_facts as Record<string, unknown> | undefined;
  const suggested = draft.structured_json.suggested_actions as Array<Record<string, unknown>> | undefined;
  const assetCount = Number(facts?.asset_count ?? evidenceRecord.value?.asset_count ?? 0);
  const actionCount = Array.isArray(suggested) ? suggested.length : 0;
  if (draft.validation_errors.length > 0) {
    return `草稿存在 ${draft.validation_errors.length} 个结构问题，需要人工修正后才能确认。`;
  }
  return `草稿已关联 ${assetCount} 个证据附件，生成 ${actionCount} 条建议动作；确认前不写入正式学习记录。`;
}

type EvidenceResultItem = {
  label: string;
  value: string;
};

function evidenceObjectItems(value: unknown): EvidenceResultItem[] {
  if (!isPlainRecord(value)) {
    return [];
  }
  return Object.entries(value).map(([key, item]) => ({
    label: evidenceFieldLabel(key),
    value: formatEvidenceValue(item),
  }));
}

function evidenceListItems(value: unknown): EvidenceResultItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item, index) => ({
    label: `第 ${index + 1} 项`,
    value: formatEvidenceValue(item),
  }));
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatEvidenceValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.map(formatEvidenceValue).join("；") : "无";
  }
  if (isPlainRecord(value)) {
    const entries = Object.entries(value);
    return entries.length > 0
      ? entries
          .map(([key, item]) => `${evidenceFieldLabel(key)}：${formatEvidenceValue(item)}`)
          .join("；")
      : "无";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return String(value);
}

function evidenceFieldLabel(key: string): string {
  const labels: Record<string, string> = {
    asset_count: "附件数",
    study_date: "学习日期",
    visible_text: "识别文字",
    ocr_text: "识别文字",
    ocr_performed: "已执行图像识别",
    provider: "模型服务",
    topic: "主题",
    field: "字段",
    reason: "原因",
    confidence: "置信度",
    diagnosis: "诊断",
    evidence_basis: "证据依据",
    risk: "风险",
    type: "动作",
    priority: "优先级",
  };
  return labels[key] ?? key.replaceAll("_", " ");
}

function evidenceValidationMessage(error: string): string {
  const code = error.startsWith("provider:") ? error.slice("provider:".length) : error;
  const messages: Record<string, string> = {
    AI_PROVIDER_AUTH_FAILED: "DeepSeek API Key 无效、已过期或没有当前模型权限。",
    AI_PROVIDER_RATE_LIMITED: "模型服务当前限流，请稍后重新分析。",
    AI_PROVIDER_TIMEOUT: "模型服务响应超时，请稍后重试。",
    AI_PROVIDER_UNAVAILABLE: "模型服务暂时不可用，请稍后重试。",
    AI_PROVIDER_RESPONSE_INVALID: "模型返回的内容格式不符合证据草稿要求。",
    AI_EVIDENCE_TYPE_UNSUPPORTED: "真实模型当前只支持 PNG 和 JPEG，暂不分析 PDF。",
    AI_EVIDENCE_ASSET_UNAVAILABLE: "后端无法读取证据原件，请检查存储服务。",
    AI_IMAGE_REQUIRED: "没有可供模型分析的图片。",
    AI_PROVIDER_MODE_INVALID: "当前模型不支持测试分析模式。",
  };
  return messages[code] ?? "模型输出结构不完整，需要重新分析或人工修正。";
}

async function loadEvidenceHistory(): Promise<void> {
  try {
    const history = await new ApiClient().evidenceHistory(10);
    evidenceHistory.value = history.data.items;
    if (evidenceRecord.value) {
      const selected = history.data.items.find(
        (item) => item.record.id === evidenceRecord.value?.id,
      );
      if (selected) {
        evidenceRecord.value = selected.record;
        evidenceDraft.value = selected.draft;
        evidenceAssets.value = selected.assets;
      }
    }
    evidenceHistoryError.value = null;
  } catch {
    evidenceHistory.value = null;
    evidenceHistoryError.value = "证据历史加载失败，请稍后重试。";
  }
}

function selectEvidenceHistory(item: EvidenceHistoryItemPayload): void {
  evidenceRecord.value = item.record;
  evidenceDraft.value = item.draft;
  evidenceAssets.value = item.assets;
  evidenceActionError.value = null;
}

function evidenceDraftStatusLabel(draft: EvidenceDraftPayload | null): string {
  if (!draft) {
    return "未分析";
  }
  const labels: Record<EvidenceDraftPayload["status"], string> = {
    draft: "待确认",
    needs_correction: "需修正",
    confirmed: "已确认",
    rejected: "已驳回",
  };
  return labels[draft.status];
}

function evidenceHistoryTone(item: EvidenceHistoryItemPayload): Tone {
  if (item.draft?.status === "confirmed" || item.record.status === "confirmed") {
    return "green";
  }
  if (item.draft?.status === "rejected" || item.record.status === "rejected") {
    return "red";
  }
  if (item.draft?.status === "needs_correction") {
    return "yellow";
  }
  return "blue";
}

function formatEvidenceHistoryDate(value: string): string {
  return value.slice(0, 10);
}

async function evidenceFilePayload(file: File): Promise<EvidenceFileUploadPayload> {
  if (!isEvidenceMime(file.type)) {
    throw new Error("unsupported evidence file type");
  }
  return {
    original_name: file.name,
    mime_type: file.type,
    content_base64: await fileToBase64(file),
  };
}

function isEvidenceMime(value: string): value is EvidenceFileUploadPayload["mime_type"] {
  return value === "image/png" || value === "image/jpeg" || value === "application/pdf";
}

async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const [, base64 = ""] = result.split(",", 2);
      resolve(base64);
    });
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsDataURL(file);
  });
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

onMounted(async () => {
  void loadEvidenceHistory();
  try {
    const response = await new ApiClient().today(todayString());
    apiToday.value = response.data;
  } catch {
    apiToday.value = null;
  }
});
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-today"
  >
    <PageHeader
      kicker="今日"
      title="今日行动"
      description="把周目标压到今天可执行的任务、证据确认和复盘动作；API 不可用时保留原型数据。"
      action-label="开始第一项"
    />

    <div class="metric-grid">
      <MetricCard
        v-for="metric in todayMetrics"
        :key="metric.label"
        :label="metric.label"
        :value="metric.value"
        :detail="metric.detail"
        :tone="metric.tone"
      />
    </div>

    <div class="content-grid two-columns">
      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              学习闭环
            </p>
            <h2>今日任务</h2>
          </div>
          <StatusTag
            :label="taskSourceLabel"
            :tone="taskSourceTone"
          />
        </div>
        <p
          v-if="actionError"
          class="task-action-error"
          role="status"
        >
          {{ actionError }}
        </p>

        <div class="task-list">
          <article
            v-for="task in todayTasks"
            :key="task.id"
            class="task-card"
          >
            <div class="task-card-header">
              <span class="subject-chip">{{ task.subject }}</span>
              <StatusTag
                :label="task.status"
                :tone="task.tone"
              />
            </div>
            <h3>{{ task.title }}</h3>
            <p>{{ task.reason }}</p>
            <dl class="detail-list">
              <div>
                <dt>来源</dt>
                <dd>{{ task.source }}</dd>
              </div>
              <div>
                <dt>预计</dt>
                <dd>{{ task.estimateMinutes }} 分钟</dd>
              </div>
            </dl>
            <div
              v-if="task.apiBacked"
              class="task-actions"
              aria-label="任务操作"
            >
              <button
                type="button"
                class="task-action-button"
                :disabled="!canStart(task) || isActionRunning(task, 'start')"
                @click="runTaskAction(task, 'start')"
              >
                开始
              </button>
              <button
                type="button"
                class="task-action-button"
                :disabled="!canComplete(task)"
                @click="openResultForm(task)"
              >
                完成
              </button>
              <button
                type="button"
                class="task-action-button secondary"
                :disabled="!canSkip(task) || isActionRunning(task, 'skip')"
                @click="runTaskAction(task, 'skip')"
              >
                跳过
              </button>
              <button
                type="button"
                class="task-action-button danger"
                :disabled="!canWithdraw(task) || isActionRunning(task, 'withdraw')"
                @click="runTaskAction(task, 'withdraw')"
              >
                撤回
              </button>
            </div>
            <form
              v-if="task.apiBacked && isResultFormOpen(task)"
              class="task-result-form"
              @submit.prevent="runTaskAction(task, 'complete')"
            >
              <label>
                <span>实际用时</span>
                <input
                  :value="resultDraft(task).actualMinutes"
                  type="number"
                  min="0"
                  inputmode="numeric"
                  @input="
                    updateResultDraft(
                      task,
                      'actualMinutes',
                      numberOrZero(($event.target as HTMLInputElement).value),
                    )
                  "
                >
              </label>
              <label>
                <span>完成度</span>
                <input
                  :value="resultDraft(task).completionRatio"
                  type="number"
                  min="0"
                  max="100"
                  inputmode="numeric"
                  @input="
                    updateResultDraft(
                      task,
                      'completionRatio',
                      clampPercent(numberOrZero(($event.target as HTMLInputElement).value)),
                    )
                  "
                >
              </label>
              <label>
                <span>题数</span>
                <input
                  :value="resultDraft(task).questionCount ?? ''"
                  type="number"
                  min="0"
                  inputmode="numeric"
                  @input="
                    updateResultDraft(
                      task,
                      'questionCount',
                      numberOrNull(($event.target as HTMLInputElement).value),
                    )
                  "
                >
              </label>
              <label>
                <span>正确数</span>
                <input
                  :value="resultDraft(task).correctCount ?? ''"
                  type="number"
                  min="0"
                  inputmode="numeric"
                  @input="
                    updateResultDraft(
                      task,
                      'correctCount',
                      numberOrNull(($event.target as HTMLInputElement).value),
                    )
                  "
                >
              </label>
              <label>
                <span>信心值</span>
                <input
                  :value="resultDraft(task).confidence ?? ''"
                  type="number"
                  min="0"
                  max="100"
                  inputmode="numeric"
                  @input="
                    updateResultDraft(
                      task,
                      'confidence',
                      percentOrNull(($event.target as HTMLInputElement).value),
                    )
                  "
                >
              </label>
              <label class="task-result-notes">
                <span>问题描述</span>
                <textarea
                  :value="resultDraft(task).problemDescription"
                  rows="3"
                  @input="
                    updateResultDraft(
                      task,
                      'problemDescription',
                      ($event.target as HTMLTextAreaElement).value,
                    )
                  "
                />
              </label>
              <div class="task-result-actions">
                <button
                  type="submit"
                  class="task-action-button"
                  :disabled="isActionRunning(task, 'complete')"
                >
                  提交结果
                </button>
                <button
                  type="button"
                  class="task-action-button secondary"
                  :disabled="isActionRunning(task, 'complete')"
                  @click="closeResultForm"
                >
                  取消
                </button>
              </div>
            </form>
          </article>
        </div>
      </section>

      <aside class="panel stacked-panel">
        <section class="notice-card ai-draft">
          <StatusTag
            :label="evidenceSourceLabel"
            :tone="evidenceSourceTone"
          />
          <h2>{{ evidenceCardTitle }}</h2>
          <p>{{ evidenceCardBody }}</p>
          <p
            v-if="evidenceActionError"
            class="task-action-error"
            role="status"
          >
            {{ evidenceActionError }}
          </p>
          <form
            v-if="!evidenceRecord"
            class="evidence-upload-form"
            @submit.prevent="createEvidenceDraft"
          >
            <label>
              <span>学科</span>
              <input
                :value="evidenceSubjectId"
                type="text"
                maxlength="80"
                @input="evidenceSubjectId = ($event.target as HTMLInputElement).value"
              >
            </label>
            <label>
              <span>证据文件</span>
              <input
                ref="evidenceFileInput"
                type="file"
                multiple
                accept="image/png,image/jpeg,application/pdf"
                @change="selectEvidenceFiles"
              >
            </label>
            <button
              type="submit"
              class="task-action-button"
              :disabled="evidenceActionInFlight === 'upload'"
            >
              上传并分析
            </button>
          </form>
          <div
            v-else
            class="evidence-detail"
          >
            <dl class="evidence-detail-meta">
              <div>
                <dt>学科</dt>
                <dd>{{ evidenceRecord.subject_id ?? "未分科" }}</dd>
              </div>
              <div>
                <dt>记录状态</dt>
                <dd>{{ evidenceRecordStatusLabel(evidenceRecord.status) }}</dd>
              </div>
            </dl>
            <div class="evidence-asset-list">
              <div
                v-for="asset in evidenceAssets"
                :key="asset.id"
                class="evidence-asset-row"
              >
                <span>
                  <strong>{{ asset.original_name }}</strong>
                  <small>{{ Math.max(1, Math.round(asset.size_bytes / 1024)) }} KB</small>
                </span>
                <button
                  type="button"
                  class="task-action-button secondary"
                  :disabled="openingEvidenceAssetId === asset.id"
                  @click="openEvidenceAsset(asset)"
                >
                  {{ openingEvidenceAssetId === asset.id ? "读取中" : "打开附件" }}
                </button>
              </div>
            </div>
            <section
              v-if="evidenceDraft"
              class="evidence-analysis"
              aria-label="证据分析结果"
            >
              <div class="evidence-analysis-heading">
                <h3>分析结果</h3>
                <StatusTag
                  :label="evidenceDraftStatusLabel(evidenceDraft)"
                  :tone="evidenceDraft.status === 'needs_correction' ? 'yellow' : 'blue'"
                />
              </div>
              <div
                v-if="evidenceValidationMessages.length > 0"
                class="evidence-analysis-errors"
                role="status"
              >
                <div
                  v-for="error in evidenceValidationMessages"
                  :key="error.code"
                >
                  <strong>{{ error.message }}</strong>
                  <code>{{ error.code }}</code>
                </div>
              </div>
              <section
                v-for="section in evidenceAnalysisSections"
                :key="section.key"
                class="evidence-analysis-section"
              >
                <div>
                  <h4>{{ section.title }}</h4>
                  <p>{{ section.description }}</p>
                </div>
                <dl v-if="section.items.length > 0">
                  <div
                    v-for="item in section.items"
                    :key="`${section.key}-${item.label}`"
                  >
                    <dt>{{ item.label }}</dt>
                    <dd>{{ item.value }}</dd>
                  </div>
                </dl>
                <p
                  v-else
                  class="evidence-analysis-empty"
                >
                  暂无内容
                </p>
              </section>
            </section>
            <div class="task-actions">
              <button
                v-if="!evidenceDraft"
                type="button"
                class="task-action-button"
                :disabled="evidenceActionInFlight === 'analyze'"
                @click="analyzeSelectedEvidence"
              >
                {{ evidenceActionInFlight === "analyze" ? "分析中" : "开始分析" }}
              </button>
              <button
                v-if="evidenceDraft"
                type="button"
                class="task-action-button"
                :disabled="!canConfirmEvidence() || evidenceActionInFlight === 'confirm'"
                @click="confirmEvidenceDraft"
              >
                确认
              </button>
              <button
                v-if="evidenceDraft"
                type="button"
                class="task-action-button danger"
                :disabled="!canRejectEvidence() || evidenceActionInFlight === 'reject'"
                @click="rejectEvidenceDraft"
              >
                驳回
              </button>
              <button
                type="button"
                class="task-action-button secondary"
                @click="resetEvidenceSelection"
              >
                上传新证据
              </button>
            </div>
          </div>
        </section>

        <section class="notice-card">
          <StatusTag
            label="历史入口"
            tone="blue"
          />
          <h2>证据草稿历史</h2>
          <p
            v-if="evidenceHistoryError"
            class="task-action-error"
            role="status"
          >
            {{ evidenceHistoryError }}
          </p>
          <div
            v-if="evidenceHistory && evidenceHistory.length > 0"
            class="evidence-history-list"
          >
            <div
              v-for="item in evidenceHistory"
              :key="item.record.id"
              class="evidence-history-item"
              :class="{ selected: evidenceRecord?.id === item.record.id }"
            >
              <span>
                <strong>{{ formatEvidenceHistoryDate(item.record.study_date) }}</strong>
                <small>
                  {{ item.record.subject_id ?? "未分科" }} · {{ item.record.asset_count }} 个附件
                </small>
              </span>
              <StatusTag
                :label="evidenceDraftStatusLabel(item.draft)"
                :tone="evidenceHistoryTone(item)"
              />
              <div class="evidence-history-actions">
                <button
                  type="button"
                  class="task-action-button secondary"
                  @click="selectEvidenceHistory(item)"
                >
                  查看
                </button>
                <button
                  type="button"
                  class="task-action-button danger"
                  :disabled="item.record.status === 'confirmed' || evidenceActionInFlight === 'delete'"
                  :title="item.record.status === 'confirmed' ? '已确认记录需保留审计，不能删除' : '删除记录'"
                  @click="deleteEvidenceHistory(item)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
          <p v-else-if="evidenceHistory && evidenceHistory.length === 0">
            还没有历史证据草稿；上传并分析后会出现在这里。
          </p>
          <p v-else-if="!evidenceHistoryError">
            正在加载证据历史。
          </p>
        </section>

        <section class="notice-card risk">
          <StatusTag
            label="风险提示"
            tone="red"
          />
          <h2>重复错因</h2>
          <p>
            “条件遗漏”连续两天出现，建议今天先完成无提示重做，再进入同类变式。
          </p>
        </section>

        <section class="notice-card">
          <StatusTag
            label="证据边界"
            tone="blue"
          />
          <h2>阅读不等于掌握</h2>
          <p>
            阅读、听课和拍照最多进入“已接触”；闭卷回忆和练习结果才支持继续推进。
          </p>
        </section>
      </aside>
    </div>
  </section>
</template>
