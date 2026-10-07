<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient, ApiClientError } from "../api/client";
import type {
  DueReviewPayload,
  KnowledgeNodePayload,
  KnowledgeNodeCreatePayload,
  ResourcePayload,
  ReviewResultSubmitPayload,
  ReviewResultType,
  WrongbookAttemptSubmitPayload,
  WrongbookAttemptType,
  WrongbookDraftHistoryItemPayload,
  WrongbookDraftPayload,
  WrongbookRecordPayload,
  WrongbookVerificationPayload,
} from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import PromptToolbox from "../components/PromptToolbox.vue";
import StatusTag from "../components/StatusTag.vue";
import WrongbookCauseEditor from "../components/WrongbookCauseEditor.vue";
import { useMockStudyStore, type LearningResource, type Tone } from "../stores/mockStudy";

type LearningSection = "review" | "wrongbook" | "materials" | "prompt";

const learningSections: Array<{
  id: LearningSection;
  label: string;
  description: string;
}> = [
  { id: "review", label: "复习", description: "完成今天该复习的内容" },
  { id: "wrongbook", label: "错题", description: "分析错因并重新做题" },
  { id: "materials", label: "资料", description: "上传资料和维护知识点" },
  { id: "prompt", label: "提示词", description: "生成内容后前往外部 Chat" },
];

function sectionFromLocation(): LearningSection {
  const section = new URLSearchParams(window.location.search).get("section");
  return learningSections.some((item) => item.id === section)
    ? (section as LearningSection)
    : "review";
}

const study = useMockStudyStore();
const activeSection = ref<LearningSection>(sectionFromLocation());
const apiResources = ref<ResourcePayload[] | null>(null);
const apiKnowledgeNodes = ref<KnowledgeNodePayload[] | null>(null);
const apiDueReviews = ref<DueReviewPayload[] | null>(null);
const reviewActionInFlight = ref<string | null>(null);
const reviewActionError = ref<string | null>(null);
const reviewSubmissions = ref<Record<string, ReviewResultSubmitPayload>>({});
const wrongbookActionInFlight = ref<string | null>(null);
const wrongbookActionError = ref<string | null>(null);
const wrongbookSubmissions = ref<Record<string, WrongbookAttemptSubmitPayload>>({});
const wrongbookDraftHistory = ref<WrongbookDraftHistoryItemPayload[] | null>(null);
const wrongbookDraftHistoryError = ref<string | null>(null);
const showWrongbookCapture = ref(false);
const wrongbookCaptureInFlight = ref(false);
const wrongbookCaptureMessage = ref<{ tone: "error" | "success"; text: string } | null>(null);
const wrongbookCaptureForm = ref({
  standard_text: "",
  subject_id: "",
  source: "",
});
const selectedWrongbookRecord = ref<WrongbookRecordPayload | null>(null);
const selectedWrongbookVerification = ref<WrongbookVerificationPayload | null>(null);
const selectedWrongbookDraft = ref<WrongbookDraftPayload | null>(null);
const selectedWrongbookId = ref<string | null>(null);
const wrongbookFilter = ref<"analysis" | "redo" | "completed">("redo");
const wrongbookCausesDirty = ref(false);
const resourceActionInFlight = ref(false);
const resourceMessage = ref<{ tone: "error" | "success"; text: string } | null>(null);
const selectedResourceFile = ref<File | null>(null);
const resourceFileInput = ref<HTMLInputElement | null>(null);
const knowledgeActionInFlight = ref(false);
const knowledgeMessage = ref<{ tone: "error" | "success"; text: string } | null>(null);
const editingKnowledgeNodeId = ref<string | null>(null);
const knowledgeForm = ref({
  code: "",
  name: "",
  subject_id: "",
  importance: 50,
  exam_frequency: 50,
  description: "",
});

function selectLearningSection(section: LearningSection): void {
  activeSection.value = section;
  const url = new URL(window.location.href);
  if (section === "review") url.searchParams.delete("section");
  else url.searchParams.set("section", section);
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

type KnowledgeChip = {
  id: string | null;
  label: string;
  className: "strong" | "active" | "weak" | "danger";
};

type ResourceRow = LearningResource & {
  asset: ResourcePayload["asset"] | null;
};

type ReviewCard = {
  id: string;
  title: string;
  subject: string;
  meta: string;
  reason: string;
  status: string;
  tone: Tone;
  apiBacked: boolean;
  scheduleId: string | null;
  scheduleVersion: number | null;
  resultNote: string | null;
};

const resourceSourceLabel = computed(() => (apiResources.value ? "正式资源" : "本地优先"));
const resourceSourceTone = computed<Tone>(() => (apiResources.value ? "green" : "cyan"));
const knowledgeSourceLabel = computed(() => (apiKnowledgeNodes.value ? "正式图谱" : "模拟"));
const knowledgeSourceTone = computed<Tone>(() => (apiKnowledgeNodes.value ? "green" : "yellow"));

const wrongbookCounts = computed(() => {
  const items = wrongbookDraftHistory.value ?? [];
  return {
    analysis: items.filter((item) => item.record.current_status === "pending_analysis").length,
    redo: items.filter(
      (item) => !["pending_analysis", "stable_corrected"].includes(item.record.current_status),
    ).length,
    completed: items.filter((item) => item.record.current_status === "stable_corrected").length,
  };
});

const dueWrongbookCount = computed(() =>
  (wrongbookDraftHistory.value ?? []).filter(
    (item) =>
      !["pending_analysis", "stable_corrected"].includes(item.record.current_status) &&
      isWrongbookDue(item.record),
  ).length,
);

const visibleWrongbookItems = computed(() => {
  const items = wrongbookDraftHistory.value ?? [];
  if (wrongbookFilter.value === "analysis") {
    return items.filter((item) => item.record.current_status === "pending_analysis");
  }
  if (wrongbookFilter.value === "completed") {
    return items.filter((item) => item.record.current_status === "stable_corrected");
  }
  return items.filter(
    (item) => !["pending_analysis", "stable_corrected"].includes(item.record.current_status),
  );
});

const selectedWrongbookItem = computed(() => {
  const items = wrongbookDraftHistory.value ?? [];
  return (
    items.find((item) => item.record.id === selectedWrongbookId.value) ??
    visibleWrongbookItems.value[0] ??
    null
  );
});

const wrongbookEmptyLabel = computed(() => {
  if (wrongbookFilter.value === "analysis") return "没有等待分析的错题。";
  if (wrongbookFilter.value === "completed") return "还没有完成归档的错题。";
  return "当前没有待重做错题。";
});
const reviewSourceLabel = computed(() => (apiDueReviews.value ? "正式复习" : "原型复习"));
const reviewSourceTone = computed<Tone>(() => (apiDueReviews.value ? "green" : "yellow"));

const resourceRows = computed<ResourceRow[]>(() => {
  if (!apiResources.value) {
    return study.resources.map((resource) => ({ ...resource, asset: null }));
  }
  if (apiResources.value.length === 0) {
    return [
      {
        title: "当前没有待处理材料",
        meta: "后端资源队列为空，可先上传讲义、题目截图或解析文件。",
        status: "空队列",
        tone: "neutral",
        asset: null,
      },
    ];
  }
  return apiResources.value.map((resource) => ({
    title: resource.asset.original_name,
    meta: `${resource.asset.mime_type} · ${formatBytes(resource.asset.size_bytes)} · 引用 ${resource.asset.reference_count}`,
    status: stateLabel(resource.asset.state),
    tone: toneForAssetState(resource.asset.state),
    asset: resource.asset,
  }));
});

const knowledgeChips = computed<KnowledgeChip[]>(() => {
  if (!apiKnowledgeNodes.value) {
    return [
      { id: null, label: "稳定掌握", className: "strong" },
      { id: null, label: "基础应用", className: "active" },
      { id: null, label: "待巩固", className: "weak" },
      { id: null, label: "薄弱/衰退", className: "danger" },
    ];
  }
  if (apiKnowledgeNodes.value.length === 0) {
    return [{ id: null, label: "暂无知识点", className: "weak" }];
  }
  return [...apiKnowledgeNodes.value]
    .sort((left, right) => scoreNode(right) - scoreNode(left))
    .slice(0, 6)
    .map((node) => ({
      id: node.id,
      label: node.name,
      className: classForNode(node),
    }));
});

function errorText(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) return error.error.message;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

async function reloadResources(): Promise<void> {
  const response = await new ApiClient().resources();
  apiResources.value = response.data.items;
}

function selectResourceFile(event: Event): void {
  selectedResourceFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
  resourceMessage.value = null;
}

async function fileToBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 8192) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  }
  return btoa(binary);
}

async function uploadLearningResource(): Promise<void> {
  const file = selectedResourceFile.value;
  if (!file) {
    resourceMessage.value = { tone: "error", text: "请先选择 PNG、JPEG 或 PDF 文件。" };
    return;
  }
  if (!["image/png", "image/jpeg", "application/pdf"].includes(file.type)) {
    resourceMessage.value = { tone: "error", text: "仅支持 PNG、JPEG 和 PDF 文件。" };
    return;
  }
  resourceActionInFlight.value = true;
  resourceMessage.value = null;
  try {
    const client = new ApiClient();
    const uploaded = await client.uploadAsset({
      original_name: file.name,
      mime_type: file.type as ResourcePayload["asset"]["mime_type"],
      content_base64: await fileToBase64(file),
      state: "inbox",
    });
    await client.createResource({ asset_id: uploaded.data.id });
    await reloadResources();
    selectedResourceFile.value = null;
    if (resourceFileInput.value) resourceFileInput.value.value = "";
    resourceMessage.value = { tone: "success", text: "资料已上传，当前状态为待整理。" };
  } catch (error) {
    resourceMessage.value = { tone: "error", text: errorText(error, "资料上传失败。") };
  } finally {
    resourceActionInFlight.value = false;
  }
}

async function openLearningResource(asset: ResourcePayload["asset"]): Promise<void> {
  resourceMessage.value = null;
  try {
    const response = await new ApiClient().evidenceAssetContent(asset.id);
    const source = `data:${asset.mime_type};base64,${response.data.content_base64}`;
    const opened = window.open(source, "_blank", "noopener,noreferrer");
    if (!opened) resourceMessage.value = { tone: "error", text: "浏览器阻止了新窗口，请允许弹窗后重试。" };
  } catch (error) {
    resourceMessage.value = { tone: "error", text: errorText(error, "资料打开失败。") };
  }
}

async function deleteLearningResource(asset: ResourcePayload["asset"]): Promise<void> {
  resourceActionInFlight.value = true;
  resourceMessage.value = null;
  try {
    await new ApiClient().deleteAsset(asset.id);
    await reloadResources();
    resourceMessage.value = { tone: "success", text: `已删除 ${asset.original_name}。` };
  } catch (error) {
    resourceMessage.value = { tone: "error", text: errorText(error, "资料删除失败。") };
  } finally {
    resourceActionInFlight.value = false;
  }
}

function resetKnowledgeForm(): void {
  editingKnowledgeNodeId.value = null;
  knowledgeForm.value = { code: "", name: "", subject_id: "", importance: 50, exam_frequency: 50, description: "" };
}

function editKnowledgeNode(nodeId: string | null): void {
  const node = apiKnowledgeNodes.value?.find((item) => item.id === nodeId);
  if (!node) return;
  editingKnowledgeNodeId.value = node.id;
  knowledgeForm.value = {
    code: node.code,
    name: node.name,
    subject_id: node.subject_id,
    importance: node.importance ?? 50,
    exam_frequency: node.exam_frequency ?? 50,
    description: node.description ?? "",
  };
  knowledgeMessage.value = null;
}

async function saveKnowledgeNode(): Promise<void> {
  const form = knowledgeForm.value;
  if (!form.name.trim() || (!editingKnowledgeNodeId.value && (!form.code.trim() || !form.subject_id.trim()))) {
    knowledgeMessage.value = { tone: "error", text: "名称、编码和科目不能为空。" };
    return;
  }
  knowledgeActionInFlight.value = true;
  knowledgeMessage.value = null;
  try {
    const client = new ApiClient();
    if (editingKnowledgeNodeId.value) {
      await client.updateKnowledgeNode(editingKnowledgeNodeId.value, {
        name: form.name.trim(),
        importance: form.importance,
        exam_frequency: form.exam_frequency,
        description: form.description.trim() || null,
      });
    } else {
      const payload: KnowledgeNodeCreatePayload = {
        code: form.code.trim(), name: form.name.trim(), node_type: "knowledge",
        subject_id: form.subject_id.trim(), importance: form.importance,
        exam_frequency: form.exam_frequency, description: form.description.trim() || null,
      };
      await client.createKnowledgeNode(payload);
    }
    const nodes = await client.knowledgeNodes();
    apiKnowledgeNodes.value = nodes.data.items;
    knowledgeMessage.value = { tone: "success", text: editingKnowledgeNodeId.value ? "知识点已更新。" : "知识点已添加。" };
    resetKnowledgeForm();
  } catch (error) {
    knowledgeMessage.value = { tone: "error", text: errorText(error, "知识点保存失败。") };
  } finally {
    knowledgeActionInFlight.value = false;
  }
}

async function deleteKnowledgeNode(nodeId: string | null): Promise<void> {
  if (!nodeId) return;
  knowledgeActionInFlight.value = true;
  knowledgeMessage.value = null;
  try {
    await new ApiClient().deleteKnowledgeNode(nodeId);
    apiKnowledgeNodes.value = apiKnowledgeNodes.value?.filter((node) => node.id !== nodeId) ?? [];
    if (editingKnowledgeNodeId.value === nodeId) resetKnowledgeForm();
    knowledgeMessage.value = { tone: "success", text: "知识点已删除。" };
  } catch (error) {
    knowledgeMessage.value = { tone: "error", text: errorText(error, "知识点删除失败。") };
  } finally {
    knowledgeActionInFlight.value = false;
  }
}

const reviewCards = computed<ReviewCard[]>(() => {
  if (!apiDueReviews.value) {
    return [
      {
        id: "mock-review-1",
        title: "矩阵秩闭卷抽测",
        subject: "数学一",
        meta: "阶段 3 · 预计 20 分钟 · 原型卡片",
        reason: "这次做对后，系统会安排更晚的下一次复习；没做对则会尽快再次出现。",
        status: "待复习",
        tone: "yellow",
        apiBacked: false,
        scheduleId: null,
        scheduleVersion: null,
        resultNote: null,
      },
    ];
  }
  if (apiDueReviews.value.length === 0) {
    return [
      {
        id: "empty-review",
        title: "暂无到期复习",
        subject: "复习",
        meta: "今日没有需要提交的间隔复习结果",
        reason: "继续按今日任务推进；新的掌握证据会重新生成复习计划。",
        status: "空队列",
        tone: "neutral",
        apiBacked: false,
        scheduleId: null,
        scheduleVersion: null,
        resultNote: null,
      },
    ];
  }
  return apiDueReviews.value.map((item) => {
    const submission = reviewSubmissions.value[item.schedule.id];
    const submittedPass = submission?.result.result_type === "pass";
    return {
      id: item.schedule.id,
      title: item.candidate.title || item.knowledge_node_name,
      subject: item.schedule.subject_id ?? item.candidate.subject_id,
      meta: `阶段 ${item.schedule.current_stage} · ${item.candidate.estimated_minutes} 分钟 · 到期 ${formatDate(item.schedule.due_at)}`,
      reason: item.schedule.next_reason,
        status: submission ? (submittedPass ? "这次做对" : "这次没做对") : "待复习",
      tone: submission ? (submittedPass ? "green" : "red") : "yellow",
      apiBacked: true,
      scheduleId: item.schedule.id,
      scheduleVersion: item.schedule.version,
      resultNote: submission
        ? `下次间隔 ${submission.schedule.interval_days} 天 · ${
            submission.created ? "已写入证据" : "幂等返回"
          }`
        : null,
    };
  });
});

function formatBytes(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  return `${(sizeBytes / 1024).toFixed(1)} KB`;
}

function stateLabel(state: ResourcePayload["asset"]["state"]): string {
  const labels: Record<ResourcePayload["asset"]["state"], string> = {
    inbox: "待整理",
    organized: "已整理",
    archived: "已归档",
    deleted: "已删除",
  };
  return labels[state];
}

function toneForAssetState(state: ResourcePayload["asset"]["state"]): Tone {
  if (state === "organized") {
    return "green";
  }
  if (state === "archived") {
    return "blue";
  }
  if (state === "deleted") {
    return "red";
  }
  return "neutral";
}

function scoreNode(node: KnowledgeNodePayload): number {
  return (node.importance ?? 0) + (node.exam_frequency ?? 0);
}

function classForNode(node: KnowledgeNodePayload): KnowledgeChip["className"] {
  if (node.status !== "active") {
    return "danger";
  }
  if (scoreNode(node) >= 170) {
    return "strong";
  }
  if (scoreNode(node) >= 120) {
    return "active";
  }
  return "weak";
}

function isReviewActionRunning(review: ReviewCard, resultType: ReviewResultType): boolean {
  return reviewActionInFlight.value === `${review.scheduleId}:${resultType}`;
}

async function submitReviewResult(
  review: ReviewCard,
  resultType: ReviewResultType,
): Promise<void> {
  if (!review.apiBacked || !review.scheduleId || review.scheduleVersion === null) {
    return;
  }
  const actionKey = `${review.scheduleId}:${resultType}`;
  const client = new ApiClient();
  reviewActionInFlight.value = actionKey;
  reviewActionError.value = null;
  try {
    const response = await client.submitReviewResult(
      review.scheduleId,
      {
        result_type: resultType,
        score: resultType === "pass" ? 90 : 40,
        occurred_at: new Date().toISOString(),
      },
      reviewIdempotencyKey(review, resultType),
    );
    reviewSubmissions.value = {
      ...reviewSubmissions.value,
      [review.scheduleId]: response.data,
    };
    updateReviewSchedule(response.data);
  } catch {
    reviewActionError.value = "复习结果提交失败，请刷新后重试。";
  } finally {
    if (reviewActionInFlight.value === actionKey) {
      reviewActionInFlight.value = null;
    }
  }
}

function updateReviewSchedule(submission: ReviewResultSubmitPayload): void {
  if (!apiDueReviews.value) {
    return;
  }
  apiDueReviews.value = apiDueReviews.value.map((item) =>
    item.schedule.id === submission.schedule.id
      ? {
          ...item,
          schedule: submission.schedule,
        }
      : item,
  );
}

function reviewIdempotencyKey(review: ReviewCard, resultType: ReviewResultType): string {
  return [review.scheduleId, resultType, review.scheduleVersion].join(":");
}

function formatDate(value: string): string {
  return value.slice(0, 10);
}

function wrongbookDueLabel(record: WrongbookRecordPayload): string {
  if (record.current_status === "stable_corrected") {
    return record.resolved_at ? `完成于 ${formatDate(record.resolved_at)}` : "已完成";
  }
  if (record.current_status === "pending_analysis") return "先确认错因";
  if (!record.next_review_at) return "现在可以重做";
  const due = formatDate(record.next_review_at);
  const today = todayString();
  if (due < today) return "已经到期";
  if (due === today) return "今天重做";
  return `${due} 重做`;
}

function isWrongbookDue(record: WrongbookRecordPayload): boolean {
  return !record.next_review_at || formatDate(record.next_review_at) <= todayString();
}

function selectWrongbookFilter(filter: "analysis" | "redo" | "completed"): void {
  wrongbookFilter.value = filter;
  selectedWrongbookId.value = null;
}

function selectWrongbookItem(item: WrongbookDraftHistoryItemPayload): void {
  selectedWrongbookId.value = item.record.id;
  selectWrongbookDraftHistory(item);
}

function startNextWrongbook(): void {
  const next = (wrongbookDraftHistory.value ?? []).find(
    (item) =>
      !["pending_analysis", "stable_corrected"].includes(item.record.current_status) &&
      isWrongbookDue(item.record),
  );
  if (!next) return;
  wrongbookFilter.value = "redo";
  selectWrongbookItem(next);
  requestAnimationFrame(() => document.querySelector(".wrongbook-focus")?.scrollIntoView({ block: "start" }));
}

function nextWrongbookAttemptType(status: WrongbookRecordPayload["current_status"]): WrongbookAttemptType {
  if (status === "pending_variant") return "variant";
  if (status === "pending_interval") return "interval_test";
  return "no_hint_redo";
}

function isWrongbookResultRunning(item: WrongbookDraftHistoryItemPayload, isCorrect: boolean): boolean {
  return wrongbookActionInFlight.value === `${item.record.id}:${isCorrect ? "pass" : "fail"}`;
}

async function submitWrongbookResult(
  item: WrongbookDraftHistoryItemPayload,
  isCorrect: boolean,
): Promise<void> {
  const actionKey = `${item.record.id}:${isCorrect ? "pass" : "fail"}`;
  const client = new ApiClient();
  wrongbookActionInFlight.value = actionKey;
  wrongbookActionError.value = null;
  try {
    const payload = {
      attempt_type: nextWrongbookAttemptType(item.record.current_status),
      is_correct: isCorrect,
      score: isCorrect ? 96 : 40,
      confidence: isCorrect ? 80 : 40,
      attempted_at: new Date().toISOString(),
    };
    const response = await client.submitWrongbookAttempt(
      item.record.id,
      payload,
      [item.record.id, payload.attempt_type, item.record.version, isCorrect ? "pass" : "fail"].join(":"),
    );
    wrongbookSubmissions.value = {
      ...wrongbookSubmissions.value,
      [item.record.id]: response.data,
    };
    wrongbookDraftHistory.value = (wrongbookDraftHistory.value ?? []).map((entry) =>
      entry.record.id === item.record.id
        ? { ...entry, record: response.data.record, verification: response.data.verification }
        : entry,
    );
    selectedWrongbookRecord.value = response.data.record;
    selectedWrongbookVerification.value = response.data.verification;
  } catch {
    wrongbookActionError.value = "错题结果保存失败，请刷新后重试。";
  } finally {
    if (wrongbookActionInFlight.value === actionKey) {
      wrongbookActionInFlight.value = null;
    }
  }
}

async function loadWrongbookDraftHistory(selectRecordId?: string): Promise<void> {
  try {
    const client = new ApiClient();
    const items: WrongbookDraftHistoryItemPayload[] = [];
    let total = 0;
    do {
      const history = await client.wrongbookDraftHistory(100, items.length);
      if (history.data.items.length === 0) break;
      items.push(...history.data.items);
      total = history.data.total;
    } while (items.length < total);
    wrongbookDraftHistory.value = items;
    wrongbookDraftHistoryError.value = null;
    const selected = selectRecordId
      ? items.find((item) => item.record.id === selectRecordId)
      : items.find((item) => item.draft !== null);
    if (selected && (!selectedWrongbookDraft.value || selectRecordId)) {
      selectWrongbookDraftHistory(selected);
    }
  } catch {
    wrongbookDraftHistory.value = null;
    wrongbookDraftHistoryError.value = "错题草稿历史加载失败，请稍后重试。";
  }
}

async function submitWrongbookCapture(): Promise<void> {
  const standardText = wrongbookCaptureForm.value.standard_text.trim();
  if (!standardText) {
    wrongbookCaptureMessage.value = { tone: "error", text: "请先填写题目内容。" };
    return;
  }

  wrongbookCaptureInFlight.value = true;
  wrongbookCaptureMessage.value = null;
  try {
    const response = await new ApiClient().quickCaptureWrongQuestion({
      standard_text: standardText,
      subject_id: wrongbookCaptureForm.value.subject_id.trim() || null,
      source: wrongbookCaptureForm.value.source.trim() || null,
    });
    wrongbookFilter.value = "analysis";
    await loadWrongbookDraftHistory(response.data.record.id);
    wrongbookCaptureForm.value = { standard_text: "", subject_id: "", source: "" };
    showWrongbookCapture.value = false;
    wrongbookCaptureMessage.value = { tone: "success", text: "已记入错题本，接下来分析错因。" };
  } catch {
    wrongbookCaptureMessage.value = { tone: "error", text: "错题保存失败，请稍后重试。" };
  } finally {
    wrongbookCaptureInFlight.value = false;
  }
}

function selectWrongbookDraftHistory(item: WrongbookDraftHistoryItemPayload): void {
  selectedWrongbookId.value = item.record.id;
  selectedWrongbookRecord.value = item.record;
  selectedWrongbookVerification.value = item.verification;
  selectedWrongbookDraft.value = item.draft;
  wrongbookActionError.value = null;
}

async function confirmSelectedWrongbookDraft(): Promise<void> {
  if (!selectedWrongbookDraft.value) {
    return;
  }
  const wrongRecordId = selectedWrongbookDraft.value.wrong_record_id;
  const actionKey = wrongbookDraftActionKey("confirm", wrongRecordId);
  wrongbookActionInFlight.value = actionKey;
  wrongbookActionError.value = null;
  try {
    const confirmed = await new ApiClient().confirmWrongbookDraft(wrongRecordId);
    selectedWrongbookRecord.value = confirmed.data.record;
    selectedWrongbookDraft.value = confirmed.data.draft;
    await loadWrongbookDraftHistory(wrongRecordId);
  } catch {
    wrongbookActionError.value = "错题草稿确认失败，请刷新后重试。";
  } finally {
    if (wrongbookActionInFlight.value === actionKey) {
      wrongbookActionInFlight.value = null;
    }
  }
}

function wrongbookDraftActionKey(kind: "analyze" | "confirm", wrongRecordId: string): string {
  return ["wrongbook-draft", kind, wrongRecordId].join(":");
}

function isWrongbookDraftActionRunning(
  kind: "analyze" | "confirm",
  wrongRecordId: string | null,
): boolean {
  return (
    wrongRecordId !== null &&
    wrongbookActionInFlight.value === wrongbookDraftActionKey(kind, wrongRecordId)
  );
}

function wrongbookStatusLabel(status: WrongbookAttemptSubmitPayload["record"]["current_status"]): string {
  const labels: Record<WrongbookAttemptSubmitPayload["record"]["current_status"], string> = {
    pending_analysis: "先分析错因",
    pending_no_hint_redo: "等待重做",
    pending_variant: "再做一道同类题",
    pending_interval: "稍后再复习",
    stable_corrected: "已稳定掌握",
    regressed: "需要重新复习",
  };
  return labels[status];
}

function wrongbookDraftField(draft: WrongbookDraftPayload, field: string): string {
  const value = draft.structured_json[field];
  return typeof value === "string" && value.trim() ? value : "待确认";
}

function toneForWrongbookStatus(
  status: WrongbookAttemptSubmitPayload["record"]["current_status"],
): Tone {
  if (status === "stable_corrected") {
    return "green";
  }
  if (status === "regressed") {
    return "red";
  }
  if (status === "pending_interval") {
    return "blue";
  }
  return "yellow";
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

onMounted(async () => {
  const client = new ApiClient();
  void loadWrongbookDraftHistory();
  try {
    const [resources, knowledgeNodes, dueReviews] = await Promise.all([
      client.resources(),
      client.knowledgeNodes(),
      client.dueReviews(todayString()),
    ]);
    apiResources.value = resources.data.items;
    apiKnowledgeNodes.value = knowledgeNodes.data.items;
    apiDueReviews.value = dueReviews.data.items;
  } catch {
    apiResources.value = null;
    apiKnowledgeNodes.value = null;
    apiDueReviews.value = null;
  }
});
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-learning"
  >
    <PageHeader
      kicker="学习"
      title="学习中心"
      description="先完成到期复习；错题、资料和 Prompt 按需进入，互不干扰。"
    />

    <nav
      class="learning-section-tabs"
      role="tablist"
      aria-label="学习功能"
    >
      <button
        v-for="section in learningSections"
        :id="`learning-tab-${section.id}`"
        :key="section.id"
        type="button"
        role="tab"
        :aria-selected="activeSection === section.id"
        :aria-controls="`learning-panel-${section.id}`"
        :class="{ selected: activeSection === section.id }"
        @click="selectLearningSection(section.id)"
      >
        <strong>{{ section.label }}</strong>
        <span>{{ section.description }}</span>
      </button>
    </nav>

    <div
      v-show="activeSection === 'prompt'"
      id="learning-panel-prompt"
      role="tabpanel"
      aria-labelledby="learning-tab-prompt"
    >
      <PromptToolbox />
    </div>

    <div
      v-show="activeSection === 'materials'"
      id="learning-panel-materials"
      class="content-grid two-columns"
      role="tabpanel"
      aria-labelledby="learning-tab-materials"
    >
      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              资料队列
            </p>
            <h2>待处理材料</h2>
          </div>
          <StatusTag
            :label="resourceSourceLabel"
            :tone="resourceSourceTone"
          />
        </div>

        <form
          class="learning-manager-form"
          @submit.prevent="uploadLearningResource"
        >
          <label>
            添加资料
            <input
              ref="resourceFileInput"
              type="file"
              accept="image/png,image/jpeg,application/pdf"
              :disabled="resourceActionInFlight"
              @change="selectResourceFile"
            >
          </label>
          <button
            type="submit"
            class="task-action-button"
            :disabled="resourceActionInFlight"
          >
            {{ resourceActionInFlight ? "处理中" : "上传资料" }}
          </button>
        </form>
        <p
          v-if="resourceMessage"
          class="form-message"
          :class="resourceMessage.tone"
          role="status"
        >
          {{ resourceMessage.text }}
        </p>

        <div class="resource-list">
          <article
            v-for="resource in resourceRows"
            :key="resource.title"
            class="resource-row"
          >
            <div>
              <h3>{{ resource.title }}</h3>
              <p>{{ resource.meta }}</p>
            </div>
            <StatusTag
              :label="resource.status"
              :tone="resource.tone"
            />
            <div
              v-if="resource.asset"
              class="resource-actions"
            >
              <button
                type="button"
                class="task-action-button secondary"
                @click="openLearningResource(resource.asset)"
              >
                打开
              </button>
              <button
                type="button"
                class="task-action-button danger"
                :disabled="resourceActionInFlight"
                @click="deleteLearningResource(resource.asset)"
              >
                删除
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              知识图谱
            </p>
            <h2>个人薄弱覆盖层</h2>
          </div>
          <StatusTag
            :label="knowledgeSourceLabel"
            :tone="knowledgeSourceTone"
          />
        </div>

        <form
          class="editor-form knowledge-editor"
          @submit.prevent="saveKnowledgeNode"
        >
          <label>
            名称
            <input
              v-model="knowledgeForm.name"
              required
              maxlength="200"
            >
          </label>
          <label>
            科目
            <input
              v-model="knowledgeForm.subject_id"
              :disabled="Boolean(editingKnowledgeNodeId)"
              required
              maxlength="120"
            >
          </label>
          <label>
            编码
            <input
              v-model="knowledgeForm.code"
              :disabled="Boolean(editingKnowledgeNodeId)"
              required
              maxlength="120"
            >
          </label>
          <label>
            重要度
            <input
              v-model.number="knowledgeForm.importance"
              type="number"
              min="0"
              max="100"
            >
          </label>
          <label>
            考频
            <input
              v-model.number="knowledgeForm.exam_frequency"
              type="number"
              min="0"
              max="100"
            >
          </label>
          <label class="full-width">
            说明
            <textarea
              v-model="knowledgeForm.description"
              rows="2"
            />
          </label>
          <div class="form-actions">
            <button
              type="submit"
              class="task-action-button"
              :disabled="knowledgeActionInFlight"
            >
              {{ editingKnowledgeNodeId ? "保存修改" : "添加知识点" }}
            </button>
            <button
              v-if="editingKnowledgeNodeId"
              type="button"
              class="task-action-button secondary"
              @click="resetKnowledgeForm"
            >
              取消
            </button>
          </div>
        </form>
        <p
          v-if="knowledgeMessage"
          class="form-message"
          :class="knowledgeMessage.tone"
          role="status"
        >
          {{ knowledgeMessage.text }}
        </p>

        <div class="knowledge-map">
          <article
            v-for="node in knowledgeChips"
            :key="node.label"
            class="knowledge-node"
            :class="node.className"
          >
            <strong>{{ node.label }}</strong>
            <div
              v-if="node.id"
              class="knowledge-node-actions"
            >
              <button
                type="button"
                @click="editKnowledgeNode(node.id)"
              >
                编辑
              </button>
              <button
                type="button"
                :disabled="knowledgeActionInFlight"
                @click="deleteKnowledgeNode(node.id)"
              >
                删除
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <section
      v-show="activeSection === 'review'"
      id="learning-panel-review"
      class="panel"
      role="tabpanel"
      aria-labelledby="learning-tab-review"
    >
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            间隔复习
          </p>
          <h2>到期卡片与结果提交</h2>
        </div>
        <StatusTag
          :label="reviewSourceLabel"
          :tone="reviewSourceTone"
        />
      </div>
      <p
        v-if="reviewActionError"
        class="task-action-error"
        role="status"
      >
        {{ reviewActionError }}
      </p>
      <div class="review-list">
        <article
          v-for="review in reviewCards"
          :key="review.id"
          class="review-card"
        >
          <div class="task-card-header">
            <span class="subject-chip">{{ review.subject }}</span>
            <StatusTag
              :label="review.status"
              :tone="review.tone"
            />
          </div>
          <h3>{{ review.title }}</h3>
          <p>{{ review.reason }}</p>
          <dl class="detail-list">
            <div>
              <dt>规则</dt>
              <dd>{{ review.meta }}</dd>
            </div>
            <div v-if="review.resultNote">
              <dt>提交后</dt>
              <dd>{{ review.resultNote }}</dd>
            </div>
          </dl>
          <div
            v-if="review.apiBacked"
            class="task-actions"
            aria-label="复习操作"
          >
            <button
              type="button"
              class="task-action-button"
              :disabled="
                Boolean(review.resultNote) || isReviewActionRunning(review, 'pass')
              "
              @click="submitReviewResult(review, 'pass')"
            >
              这次做对了
            </button>
            <button
              type="button"
              class="task-action-button danger"
              :disabled="
                Boolean(review.resultNote) || isReviewActionRunning(review, 'fail')
              "
              @click="submitReviewResult(review, 'fail')"
            >
              这次没做对
            </button>
          </div>
        </article>
      </div>
    </section>

    <section
      v-show="activeSection === 'wrongbook'"
      id="learning-panel-wrongbook"
      class="panel"
      role="tabpanel"
      aria-labelledby="learning-tab-wrongbook"
    >
      <div class="wrongbook-hero">
        <div>
          <p class="eyebrow">
            今天的错题
          </p>
          <h2 v-if="dueWrongbookCount > 0">
            今天有 {{ dueWrongbookCount }} 道需要重做
          </h2>
          <h2 v-else>
            今天的错题已经完成
          </h2>
          <p>系统会保留每道错题并安排之后重做；连续验证正确后，它会自动退出待办。</p>
        </div>
        <div class="wrongbook-hero-actions">
          <button
            type="button"
            class="secondary-button"
            @click="showWrongbookCapture = !showWrongbookCapture; wrongbookCaptureMessage = null"
          >
            {{ showWrongbookCapture ? "收起" : "记一道错题" }}
          </button>
          <button
            type="button"
            class="primary-action"
            :disabled="dueWrongbookCount === 0"
            @click="startNextWrongbook"
          >
            开始下一题
          </button>
        </div>
      </div>
      <form
        v-if="showWrongbookCapture"
        class="wrongbook-capture-form"
        @submit.prevent="submitWrongbookCapture"
      >
        <div class="wrongbook-capture-heading">
          <div>
            <strong>记一道错题</strong>
            <p>先把题目留下，错因可以稍后分析。</p>
          </div>
          <button
            type="button"
            class="text-button"
            @click="showWrongbookCapture = false; wrongbookCaptureMessage = null"
          >
            取消
          </button>
        </div>
        <label class="field wrongbook-question-field">
          <span>题目内容</span>
          <textarea
            v-model="wrongbookCaptureForm.standard_text"
            rows="4"
            placeholder="粘贴题目，或用一句话记下题目"
            :disabled="wrongbookCaptureInFlight"
          />
        </label>
        <div class="wrongbook-capture-optional">
          <label class="field">
            <span>科目（可选）</span>
            <input
              v-model="wrongbookCaptureForm.subject_id"
              type="text"
              placeholder="例如：数学"
              :disabled="wrongbookCaptureInFlight"
            >
          </label>
          <label class="field">
            <span>来源（可选）</span>
            <input
              v-model="wrongbookCaptureForm.source"
              type="text"
              placeholder="例如：今天的练习册"
              :disabled="wrongbookCaptureInFlight"
            >
          </label>
        </div>
        <button
          type="submit"
          class="primary-action"
          :disabled="wrongbookCaptureInFlight"
        >
          {{ wrongbookCaptureInFlight ? "正在保存…" : "保存到错题本" }}
        </button>
      </form>
      <p
        v-if="wrongbookCaptureMessage"
        :class="wrongbookCaptureMessage.tone === 'error' ? 'task-action-error' : 'task-action-success'"
        role="status"
      >
        {{ wrongbookCaptureMessage.text }}
      </p>
      <p
        v-if="wrongbookActionError"
        class="task-action-error"
        role="status"
      >
        {{ wrongbookActionError }}
      </p>
      <div
        class="wrongbook-tabs"
        role="tablist"
        aria-label="错题状态"
      >
        <button
          type="button"
          :class="{ selected: wrongbookFilter === 'analysis' }"
          @click="selectWrongbookFilter('analysis')"
        >
          待分析 <span>{{ wrongbookCounts.analysis }}</span>
        </button>
        <button
          type="button"
          :class="{ selected: wrongbookFilter === 'redo' }"
          @click="selectWrongbookFilter('redo')"
        >
          待重做 <span>{{ wrongbookCounts.redo }}</span>
        </button>
        <button
          type="button"
          :class="{ selected: wrongbookFilter === 'completed' }"
          @click="selectWrongbookFilter('completed')"
        >
          已完成 <span>{{ wrongbookCounts.completed }}</span>
        </button>
      </div>

      <div class="wrongbook-workspace">
        <div
          class="wrongbook-list"
          aria-label="错题列表"
        >
          <button
            v-for="item in visibleWrongbookItems"
            :key="item.record.id"
            type="button"
            :class="{ selected: selectedWrongbookItem?.record.id === item.record.id }"
            @click="selectWrongbookItem(item)"
          >
            <strong>{{ item.question.standard_text }}</strong>
            <span>{{ item.question.subject_id ?? "未分类" }} · 错误 {{ item.record.error_count }} 次</span>
            <small>{{ wrongbookDueLabel(item.record) }}</small>
          </button>
          <p
            v-if="wrongbookDraftHistory && visibleWrongbookItems.length === 0"
            class="wrongbook-empty"
          >
            {{ wrongbookEmptyLabel }}
          </p>
          <p
            v-else-if="!wrongbookDraftHistory && !wrongbookDraftHistoryError"
            class="wrongbook-empty"
          >
            正在加载错题。
          </p>
        </div>

        <article
          v-if="selectedWrongbookItem"
          class="wrongbook-focus"
        >
          <div class="task-card-header">
            <span>{{ selectedWrongbookItem.question.subject_id ?? "未分类" }}</span>
            <StatusTag
              :label="wrongbookStatusLabel(selectedWrongbookItem.record.current_status)"
              :tone="toneForWrongbookStatus(selectedWrongbookItem.record.current_status)"
            />
          </div>
          <h3>{{ selectedWrongbookItem.question.standard_text }}</h3>
          <p class="wrongbook-source">
            {{ selectedWrongbookItem.question.source ?? "手动记录" }} · 错误 {{ selectedWrongbookItem.record.error_count }} 次
          </p>

          <template v-if="selectedWrongbookItem.record.current_status === 'pending_analysis'">
            <WrongbookCauseEditor
              :key="selectedWrongbookItem.record.id"
              :item="selectedWrongbookItem"
              @saved="loadWrongbookDraftHistory"
              @dirty="wrongbookCausesDirty = $event"
            />
            <div
              v-if="selectedWrongbookItem.draft"
              class="wrongbook-causes"
            >
              <div><span>直接原因</span><strong>{{ wrongbookDraftField(selectedWrongbookItem.draft, 'surface_cause') }}</strong></div>
              <div><span>真正原因</span><strong>{{ wrongbookDraftField(selectedWrongbookItem.draft, 'deep_cause') }}</strong></div>
              <div><span>需要补的基础</span><strong>{{ wrongbookDraftField(selectedWrongbookItem.draft, 'prerequisite_gap') }}</strong></div>
            </div>
            <div class="task-actions">
              <button
                v-if="selectedWrongbookItem.draft?.status === 'draft'"
                type="button"
                class="task-action-button"
                :disabled="wrongbookCausesDirty || isWrongbookDraftActionRunning('confirm', selectedWrongbookItem.record.id)"
                @click="selectWrongbookItem(selectedWrongbookItem); confirmSelectedWrongbookDraft()"
              >
                确认错因并安排重做
              </button>
            </div>
          </template>

          <template v-else-if="selectedWrongbookItem.record.current_status === 'stable_corrected'">
            <div class="wrongbook-complete-message">
              <strong>这道题已经完成</strong>
              <p>它已从待重做中移走，历史记录仍会保留。</p>
            </div>
          </template>

          <template v-else>
            <div class="wrongbook-causes">
              <div><span>错因</span><strong>{{ selectedWrongbookItem.record.deep_cause ?? selectedWrongbookItem.record.surface_cause ?? "待补充" }}</strong></div>
              <div><span>下次重做</span><strong>{{ wrongbookDueLabel(selectedWrongbookItem.record) }}</strong></div>
            </div>
            <p class="wrongbook-instruction">
              {{ isWrongbookDue(selectedWrongbookItem.record) ? "先在纸上独立完成，再记录结果。不要边看答案边做。" : `这道题还没到重做日期，${wrongbookDueLabel(selectedWrongbookItem.record)}。` }}
            </p>
            <p
              v-if="wrongbookSubmissions[selectedWrongbookItem.record.id]"
              class="task-action-success"
              role="status"
            >
              结果已保存，{{ wrongbookDueLabel(selectedWrongbookItem.record) }}。
            </p>
            <div
              v-if="isWrongbookDue(selectedWrongbookItem.record)"
              class="task-actions wrongbook-outcome-actions"
            >
              <button
                type="button"
                class="task-action-button"
                :disabled="isWrongbookResultRunning(selectedWrongbookItem, true)"
                @click="submitWrongbookResult(selectedWrongbookItem, true)"
              >
                这次做对了
              </button>
              <button
                type="button"
                class="task-action-button danger"
                :disabled="isWrongbookResultRunning(selectedWrongbookItem, false)"
                @click="submitWrongbookResult(selectedWrongbookItem, false)"
              >
                仍然做错
              </button>
            </div>
          </template>
        </article>
      </div>
    </section>
  </section>
</template>
