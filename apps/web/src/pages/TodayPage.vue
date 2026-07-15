<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type {
  EvidenceDraftPayload,
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
const evidenceActionInFlight = ref<"create" | "confirm" | "reject" | null>(null);
const evidenceActionError = ref<string | null>(null);
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
    value: evidenceDraft.value?.status === "draft" ? "1 份" : "0 份",
    detail: evidenceRecord.value
      ? `证据记录 ${evidenceRecordStatusLabel(evidenceRecord.value.status)}`
      : "确认前不写正式记录",
    tone: "yellow" as Tone,
  },
]);
const evidenceSourceLabel = computed(() => (evidenceRecord.value ? "正式草稿" : "原型草稿"));
const evidenceSourceTone = computed<Tone>(() => (evidenceRecord.value ? "green" : "yellow"));
const evidenceCardTitle = computed(() =>
  evidenceDraft.value ? evidenceDraftTitle(evidenceDraft.value) : "昨日复盘草稿",
);
const evidenceCardBody = computed(() => {
  if (!evidenceDraft.value) {
    return "已识别 2 个高频错因：条件遗漏、符号方向误判。用户确认前，不更新掌握判定和后续计划。";
  }
  return evidenceDraftSummary(evidenceDraft.value);
});

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

async function createEvidenceDraft(): Promise<void> {
  const client = new ApiClient();
  evidenceActionInFlight.value = "create";
  evidenceActionError.value = null;
  try {
    const upload = await client.uploadEvidence({
      study_date: todayString(),
      subject_id: "math",
      files: [
        {
          original_name: "daily-evidence.png",
          mime_type: "image/png",
          content_base64: "iVBORw0KGgpldmlkZW5jZS1kZW1vLXBuZw==",
        },
      ],
    });
    const analyzed = await client.analyzeEvidence(upload.data.record.id, {
      provider_mode: "valid",
    });
    evidenceRecord.value = upload.data.record;
    evidenceDraft.value = analyzed.data.draft;
  } catch {
    evidenceActionError.value = "证据草稿生成失败，请刷新后重试。";
  } finally {
    if (evidenceActionInFlight.value === "create") {
      evidenceActionInFlight.value = null;
    }
  }
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

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

onMounted(async () => {
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
          <div class="task-actions">
            <button
              type="button"
              class="task-action-button"
              :disabled="Boolean(evidenceDraft) || evidenceActionInFlight === 'create'"
              @click="createEvidenceDraft"
            >
              生成草稿
            </button>
            <button
              type="button"
              class="task-action-button"
              :disabled="!canConfirmEvidence() || evidenceActionInFlight === 'confirm'"
              @click="confirmEvidenceDraft"
            >
              确认
            </button>
            <button
              type="button"
              class="task-action-button danger"
              :disabled="!canRejectEvidence() || evidenceActionInFlight === 'reject'"
              @click="rejectEvidenceDraft"
            >
              驳回
            </button>
          </div>
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
