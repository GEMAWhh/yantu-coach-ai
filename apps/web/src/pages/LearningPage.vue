<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type {
  DueReviewPayload,
  KnowledgeNodePayload,
  ResourcePayload,
  ReviewResultSubmitPayload,
  ReviewResultType,
  WrongbookAttemptSubmitPayload,
  WrongbookCandidatePayload,
} from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
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

type KnowledgeChip = {
  label: string;
  className: "strong" | "active" | "weak" | "danger";
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
const reviewSourceLabel = computed(() => (apiDueReviews.value ? "正式复习" : "原型复习"));
const reviewSourceTone = computed<Tone>(() => (apiDueReviews.value ? "green" : "yellow"));

const resourceRows = computed<LearningResource[]>(() => {
  if (!apiResources.value) {
    return study.resources;
  }
  if (apiResources.value.length === 0) {
    return [
      {
        title: "当前没有待处理材料",
        meta: "后端资源队列为空，可先上传讲义、题目截图或解析文件。",
        status: "空队列",
        tone: "neutral",
      },
    ];
  }
  return apiResources.value.map((resource) => ({
    title: resource.asset.original_name,
    meta: `${resource.asset.mime_type} · ${formatBytes(resource.asset.size_bytes)} · 引用 ${resource.asset.reference_count}`,
    status: stateLabel(resource.asset.state),
    tone: toneForAssetState(resource.asset.state),
  }));
});

const knowledgeChips = computed<KnowledgeChip[]>(() => {
  if (!apiKnowledgeNodes.value) {
    return [
      { label: "稳定掌握", className: "strong" },
      { label: "基础应用", className: "active" },
      { label: "待巩固", className: "weak" },
      { label: "薄弱/衰退", className: "danger" },
    ];
  }
  if (apiKnowledgeNodes.value.length === 0) {
    return [{ label: "暂无知识点", className: "weak" }];
  }
  return [...apiKnowledgeNodes.value]
    .sort((left, right) => scoreNode(right) - scoreNode(left))
    .slice(0, 6)
    .map((node) => ({
      label: node.name,
      className: classForNode(node),
    }));
});

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
      description="集中展示资料、题库、错题、复习卡片和知识图谱入口，保留原型交互语义。"
      action-label="查看下一知识点"
    />

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

        <div class="knowledge-map">
          <button
            v-for="node in knowledgeChips"
            :key="node.label"
            type="button"
            class="knowledge-node"
            :class="node.className"
          >
            {{ node.label }}
          </button>
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
