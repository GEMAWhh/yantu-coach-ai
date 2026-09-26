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
  WrongbookCandidatePayload,
  WrongbookDraftHistoryItemPayload,
  WrongbookDraftPayload,
  WrongbookRecordPayload,
  WrongbookVerificationPayload,
} from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import PromptToolbox from "../components/PromptToolbox.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type LearningResource, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiResources = ref<ResourcePayload[] | null>(null);
const apiKnowledgeNodes = ref<KnowledgeNodePayload[] | null>(null);
const apiWrongbookCandidates = ref<WrongbookCandidatePayload[] | null>(null);
const apiDueReviews = ref<DueReviewPayload[] | null>(null);
const reviewActionInFlight = ref<string | null>(null);
const reviewActionError = ref<string | null>(null);
const reviewSubmissions = ref<Record<string, ReviewResultSubmitPayload>>({});
const wrongbookActionInFlight = ref<string | null>(null);
const wrongbookActionError = ref<string | null>(null);
const wrongbookSubmissions = ref<Record<string, WrongbookAttemptSubmitPayload>>({});
const wrongbookDraftHistory = ref<WrongbookDraftHistoryItemPayload[] | null>(null);
const wrongbookDraftHistoryError = ref<string | null>(null);
const selectedWrongbookRecord = ref<WrongbookRecordPayload | null>(null);
const selectedWrongbookVerification = ref<WrongbookVerificationPayload | null>(null);
const selectedWrongbookDraft = ref<WrongbookDraftPayload | null>(null);
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

type KnowledgeChip = {
  id: string | null;
  label: string;
  className: "strong" | "active" | "weak" | "danger";
};

type ResourceRow = LearningResource & {
  asset: ResourcePayload["asset"] | null;
};

type LoopCard = {
  title: string;
  body: string;
};

type WrongbookCard = LoopCard & {
  id: string;
  status: string;
  tone: Tone;
  apiBacked: boolean;
  sourceId: string | null;
  taskType: string | null;
  resultNote: string | null;
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
const wrongbookSourceLabel = computed(() =>
  apiWrongbookCandidates.value ? "规划候选" : "证据驱动",
);
const wrongbookSourceTone = computed<Tone>(() =>
  apiWrongbookCandidates.value ? "green" : "blue",
);
const wrongbookDraftSourceTone = computed<Tone>(() =>
  wrongbookDraftHistory.value ? "green" : "yellow",
);
const pendingWrongbookDraftCount = computed(() =>
  wrongbookDraftHistory.value
    ? wrongbookDraftHistory.value.filter((item) => item.draft?.status === "draft").length
    : selectedWrongbookDraft.value?.status === "draft"
      ? 1
      : 0,
);
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
        reason: "多时间点复习通过后才延长间隔；失败会触发回退和短间隔复测。",
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
      status: submission ? (submittedPass ? "已通过" : "已失败") : "待复习",
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

const wrongbookCards = computed<WrongbookCard[]>(() => {
  if (!apiWrongbookCandidates.value) {
    return [
      {
        id: "mock-wrongbook-1",
        title: "1. 分类上传",
        body: "题干、作答、答案、解析、错因、重做和变式附件分别保存。",
        status: "原型",
        tone: "blue",
        apiBacked: false,
        sourceId: null,
        taskType: null,
        resultNote: null,
      },
      {
        id: "mock-wrongbook-2",
        title: "2. 用户确认",
        body: "OCR 或 AI 结构化结果必须由用户确认后才进入正式记录。",
        status: "原型",
        tone: "yellow",
        apiBacked: false,
        sourceId: null,
        taskType: null,
        resultNote: null,
      },
      {
        id: "mock-wrongbook-3",
        title: "3. 隔日重做",
        body: "原题即时正确最多推进到待变式验证，不直接标记解决。",
        status: "原型",
        tone: "yellow",
        apiBacked: false,
        sourceId: null,
        taskType: null,
        resultNote: null,
      },
      {
        id: "mock-wrongbook-4",
        title: "4. 稳定修正",
        body: "无提示重做、变式和间隔复测均通过后，才可稳定修正。",
        status: "原型",
        tone: "green",
        apiBacked: false,
        sourceId: null,
        taskType: null,
        resultNote: null,
      },
    ];
  }
  if (apiWrongbookCandidates.value.length === 0) {
    return [
      {
        id: "empty-wrongbook",
        title: "暂无错题候选",
        body: "当前没有进入今日计划的错题候选，继续按资源和知识图谱推进。",
        status: "空队列",
        tone: "neutral",
        apiBacked: false,
        sourceId: null,
        taskType: null,
        resultNote: null,
      },
    ];
  }
  return apiWrongbookCandidates.value.slice(0, 4).map((candidate, index) => {
    const submission = candidate.source_id
      ? wrongbookSubmissions.value[candidate.source_id]
      : null;
    return {
      id: candidate.id,
      title: `${index + 1}. ${candidate.title}`,
      body: `${candidate.subject_id} · ${candidate.estimated_minutes} 分钟 · 弱项 ${candidate.weakness} · 重复错因 ${candidate.repeat_error}`,
      status: submission ? wrongbookStatusLabel(submission.record.current_status) : "待验证",
      tone: submission ? toneForWrongbookStatus(submission.record.current_status) : "yellow",
      apiBacked: true,
      sourceId: candidate.source_id,
      taskType: candidate.task_type,
      resultNote: submission
        ? `${attemptTypeLabel(submission.attempt.attempt_type)} · ${
            submission.attempt.is_correct ? "正确" : "错误"
          } · ${submission.created ? "已记录" : "幂等返回"}`
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

function isWrongbookActionRunning(
  card: WrongbookCard,
  resultKind: "variant" | "interval",
  isCorrect: boolean,
): boolean {
  return wrongbookActionInFlight.value === wrongbookActionKey(card, resultKind, isCorrect);
}

async function submitWrongbookResult(
  card: WrongbookCard,
  resultKind: "variant" | "interval",
  isCorrect: boolean,
): Promise<void> {
  if (!card.apiBacked || !card.sourceId) {
    return;
  }
  const actionKey = wrongbookActionKey(card, resultKind, isCorrect);
  const client = new ApiClient();
  wrongbookActionInFlight.value = actionKey;
  wrongbookActionError.value = null;
  try {
    const payload = {
      is_correct: isCorrect,
      score: isCorrect ? 96 : 40,
      confidence: isCorrect ? 80 : 40,
      attempted_at: new Date().toISOString(),
    };
    const response =
      resultKind === "variant"
        ? await client.submitWrongbookVariantResult(
            card.sourceId,
            payload,
            wrongbookIdempotencyKey(card, resultKind, isCorrect),
          )
        : await client.submitWrongbookIntervalResult(
            card.sourceId,
            payload,
            wrongbookIdempotencyKey(card, resultKind, isCorrect),
          );
    wrongbookSubmissions.value = {
      ...wrongbookSubmissions.value,
      [card.sourceId]: response.data,
    };
  } catch {
    wrongbookActionError.value = "错题验证结果提交失败，请刷新后重试。";
  } finally {
    if (wrongbookActionInFlight.value === actionKey) {
      wrongbookActionInFlight.value = null;
    }
  }
}

async function loadWrongbookDraftHistory(selectRecordId?: string): Promise<void> {
  try {
    const history = await new ApiClient().wrongbookDraftHistory(10);
    wrongbookDraftHistory.value = history.data.items;
    wrongbookDraftHistoryError.value = null;
    const selected = selectRecordId
      ? history.data.items.find((item) => item.record.id === selectRecordId)
      : history.data.items.find((item) => item.draft !== null);
    if (selected && (!selectedWrongbookDraft.value || selectRecordId)) {
      selectWrongbookDraftHistory(selected);
    }
  } catch {
    wrongbookDraftHistory.value = null;
    wrongbookDraftHistoryError.value = "错题草稿历史加载失败，请稍后重试。";
  }
}

function selectWrongbookDraftHistory(item: WrongbookDraftHistoryItemPayload): void {
  selectedWrongbookRecord.value = item.record;
  selectedWrongbookVerification.value = item.verification;
  selectedWrongbookDraft.value = item.draft;
  wrongbookActionError.value = null;
}

async function analyzeWrongbookDraft(card: WrongbookCard): Promise<void> {
  if (!card.apiBacked || !card.sourceId) {
    return;
  }
  const actionKey = wrongbookDraftActionKey("analyze", card.sourceId);
  wrongbookActionInFlight.value = actionKey;
  wrongbookActionError.value = null;
  try {
    const analyzed = await new ApiClient().analyzeWrongbookRecord(card.sourceId, {
      provider_mode: "valid",
    });
    selectedWrongbookDraft.value = analyzed.data.draft;
    await loadWrongbookDraftHistory(analyzed.data.draft.wrong_record_id);
  } catch {
    wrongbookActionError.value = "错题草稿生成失败，请刷新后重试。";
  } finally {
    if (wrongbookActionInFlight.value === actionKey) {
      wrongbookActionInFlight.value = null;
    }
  }
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

function wrongbookActionKey(
  card: WrongbookCard,
  resultKind: "variant" | "interval",
  isCorrect: boolean,
): string {
  return [card.sourceId, resultKind, isCorrect ? "pass" : "fail"].join(":");
}

function wrongbookIdempotencyKey(
  card: WrongbookCard,
  resultKind: "variant" | "interval",
  isCorrect: boolean,
): string {
  return [card.sourceId, resultKind, isCorrect ? "pass" : "fail", card.taskType ?? "candidate"].join(
    ":",
  );
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
    pending_analysis: "待分析",
    pending_no_hint_redo: "待无提示重做",
    pending_variant: "待变式",
    pending_interval: "待间隔复测",
    stable_corrected: "稳定修正",
    regressed: "已回退",
  };
  return labels[status];
}

function wrongbookDraftStatusLabel(draft: WrongbookDraftPayload | null): string {
  if (!draft) {
    return "未分析";
  }
  const labels: Record<WrongbookDraftPayload["status"], string> = {
    draft: "待确认",
    needs_correction: "需修正",
    confirmed: "已确认",
  };
  return labels[draft.status];
}

function wrongbookDraftTone(draft: WrongbookDraftPayload | null): Tone {
  if (!draft) {
    return "neutral";
  }
  if (draft.status === "confirmed") {
    return "green";
  }
  if (draft.status === "needs_correction") {
    return "yellow";
  }
  return "blue";
}

function wrongbookDraftTitle(draft: WrongbookDraftPayload | null): string {
  if (!draft) {
    return "暂无可处理错题草稿";
  }
  if (draft.status === "confirmed") {
    return "错题草稿已确认";
  }
  if (draft.status === "needs_correction") {
    return "错题草稿需修正";
  }
  return "待确认错题草稿";
}

function wrongbookDraftSummary(draft: WrongbookDraftPayload): string {
  if (draft.validation_errors.length > 0) {
    return `草稿存在 ${draft.validation_errors.length} 个结构问题，需要人工修正后才能确认。`;
  }
  const remediationPlan = draft.structured_json.remediation_plan;
  const actionCount = Array.isArray(remediationPlan) ? remediationPlan.length : 0;
  return `草稿已生成错因诊断和 ${actionCount} 条补救动作；确认前不写入正式错题记录。`;
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

function attemptTypeLabel(type: WrongbookAttemptSubmitPayload["attempt"]["attempt_type"]): string {
  const labels: Record<WrongbookAttemptSubmitPayload["attempt"]["attempt_type"], string> = {
    original_redo: "原题重做",
    no_hint_redo: "无提示重做",
    variant: "变式",
    interval_test: "间隔复测",
    transfer_test: "迁移测试",
  };
  return labels[type];
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

onMounted(async () => {
  const client = new ApiClient();
  void loadWrongbookDraftHistory();
  try {
    const [resources, knowledgeNodes, wrongbookCandidates, dueReviews] = await Promise.all([
      client.resources(),
      client.knowledgeNodes(),
      client.wrongbookPlanningCandidates(),
      client.dueReviews(todayString()),
    ]);
    apiResources.value = resources.data.items;
    apiKnowledgeNodes.value = knowledgeNodes.data.items;
    apiWrongbookCandidates.value = wrongbookCandidates.data.items;
    apiDueReviews.value = dueReviews.data.items;
  } catch {
    apiResources.value = null;
    apiKnowledgeNodes.value = null;
    apiWrongbookCandidates.value = null;
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
      title="资料与知识单元"
      description="使用固定学习 Prompt 辅助对话，并管理资料、错题、复习卡片和知识图谱。"
    />

    <PromptToolbox />

    <div class="content-grid two-columns">
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

    <section class="panel">
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
              通过
            </button>
            <button
              type="button"
              class="task-action-button danger"
              :disabled="
                Boolean(review.resultNote) || isReviewActionRunning(review, 'fail')
              "
              @click="submitReviewResult(review, 'fail')"
            >
              失败
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            错题闭环
          </p>
          <h2>确认、重做、变式、间隔复测</h2>
        </div>
        <StatusTag
          :label="wrongbookSourceLabel"
          :tone="wrongbookSourceTone"
        />
      </div>
      <p
        v-if="wrongbookActionError"
        class="task-action-error"
        role="status"
      >
        {{ wrongbookActionError }}
      </p>
      <div class="draft-workspace">
        <article class="draft-panel">
          <div class="task-card-header">
            <strong>{{ wrongbookDraftTitle(selectedWrongbookDraft) }}</strong>
            <StatusTag
              :label="wrongbookDraftStatusLabel(selectedWrongbookDraft)"
              :tone="wrongbookDraftTone(selectedWrongbookDraft)"
            />
          </div>
          <template v-if="selectedWrongbookDraft">
            <p>{{ wrongbookDraftSummary(selectedWrongbookDraft) }}</p>
            <dl class="detail-list">
              <div>
                <dt>表层错因</dt>
                <dd>{{ wrongbookDraftField(selectedWrongbookDraft, "surface_cause") }}</dd>
              </div>
              <div>
                <dt>深层错因</dt>
                <dd>{{ wrongbookDraftField(selectedWrongbookDraft, "deep_cause") }}</dd>
              </div>
              <div>
                <dt>前置缺口</dt>
                <dd>{{ wrongbookDraftField(selectedWrongbookDraft, "prerequisite_gap") }}</dd>
              </div>
              <div v-if="selectedWrongbookRecord">
                <dt>正式记录</dt>
                <dd>
                  {{ wrongbookStatusLabel(selectedWrongbookRecord.current_status) }} · 错误
                  {{ selectedWrongbookRecord.error_count }} 次
                </dd>
              </div>
              <div v-if="selectedWrongbookVerification">
                <dt>验证状态</dt>
                <dd>
                  变式 {{ selectedWrongbookVerification.variant_passed ? "已过" : "未过" }} ·
                  间隔 {{ selectedWrongbookVerification.interval_test_passed ? "已过" : "未过" }}
                </dd>
              </div>
            </dl>
            <div class="task-actions">
              <button
                type="button"
                class="task-action-button"
                :disabled="
                  selectedWrongbookDraft.status !== 'draft' ||
                    isWrongbookDraftActionRunning('confirm', selectedWrongbookDraft.wrong_record_id)
                "
                @click="confirmSelectedWrongbookDraft"
              >
                确认草稿
              </button>
            </div>
          </template>
          <p v-else>
            暂无可处理错题草稿。
          </p>
        </article>

        <article class="draft-panel">
          <div class="task-card-header">
            <strong>错题草稿历史</strong>
            <StatusTag
              :label="`${pendingWrongbookDraftCount} 份待确认`"
              :tone="wrongbookDraftSourceTone"
            />
          </div>
          <p
            v-if="wrongbookDraftHistoryError"
            class="task-action-error"
            role="status"
          >
            {{ wrongbookDraftHistoryError }}
          </p>
          <div
            v-if="wrongbookDraftHistory && wrongbookDraftHistory.length > 0"
            class="draft-history-list"
          >
            <button
              v-for="item in wrongbookDraftHistory"
              :key="item.record.id"
              type="button"
              class="draft-history-item"
              @click="selectWrongbookDraftHistory(item)"
            >
              <span>
                <strong>{{ formatDate(item.record.updated_at) }}</strong>
                <small>
                  {{ item.record.knowledge_node_id ?? "未关联知识点" }} ·
                  {{ wrongbookStatusLabel(item.record.current_status) }}
                </small>
              </span>
              <StatusTag
                :label="wrongbookDraftStatusLabel(item.draft)"
                :tone="wrongbookDraftTone(item.draft)"
              />
            </button>
          </div>
          <p v-else-if="wrongbookDraftHistory && wrongbookDraftHistory.length === 0">
            暂无错题草稿历史。
          </p>
          <p v-else-if="!wrongbookDraftHistoryError">
            正在加载错题草稿历史。
          </p>
        </article>
      </div>

      <div class="step-grid">
        <article
          v-for="card in wrongbookCards"
          :key="card.id"
        >
          <div class="task-card-header">
            <strong>{{ card.title }}</strong>
            <StatusTag
              :label="card.status"
              :tone="card.tone"
            />
          </div>
          <p>{{ card.body }}</p>
          <p v-if="card.resultNote">
            {{ card.resultNote }}
          </p>
          <div
            v-if="card.apiBacked"
            class="task-actions"
            aria-label="错题验证操作"
          >
            <button
              type="button"
              class="task-action-button secondary"
              :disabled="isWrongbookDraftActionRunning('analyze', card.sourceId)"
              @click="analyzeWrongbookDraft(card)"
            >
              生成草稿
            </button>
            <button
              type="button"
              class="task-action-button"
              :disabled="
                Boolean(card.resultNote) || isWrongbookActionRunning(card, 'variant', true)
              "
              @click="submitWrongbookResult(card, 'variant', true)"
            >
              变式通过
            </button>
            <button
              type="button"
              class="task-action-button danger"
              :disabled="
                Boolean(card.resultNote) || isWrongbookActionRunning(card, 'variant', false)
              "
              @click="submitWrongbookResult(card, 'variant', false)"
            >
              变式失败
            </button>
            <button
              type="button"
              class="task-action-button secondary"
              :disabled="
                Boolean(card.resultNote) || isWrongbookActionRunning(card, 'interval', true)
              "
              @click="submitWrongbookResult(card, 'interval', true)"
            >
              间隔通过
            </button>
            <button
              type="button"
              class="task-action-button danger"
              :disabled="
                Boolean(card.resultNote) || isWrongbookActionRunning(card, 'interval', false)
              "
              @click="submitWrongbookResult(card, 'interval', false)"
            >
              间隔失败
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>
