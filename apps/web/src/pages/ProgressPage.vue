<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient, ApiClientError } from "../api/client";
import type {
  AnalyticsErrorsPayload,
  AnalyticsGoalRiskPayload,
  AnalyticsMasteryPayload,
  AnalyticsTimePayload,
  CountBucketPayload,
  TaskPayload,
  WeakNodePayload,
} from "../api/contracts";
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import {
  remediationDraft,
  remediationTaskPayload,
  validateRemediationDraft,
  type RemediationDraft,
} from "../features/progress/remediation";
import { useMockStudyStore, type MasteryItem, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiMastery = ref<AnalyticsMasteryPayload | null>(null);
const apiErrors = ref<AnalyticsErrorsPayload | null>(null);
const apiTime = ref<AnalyticsTimePayload | null>(null);
const apiGoalRisk = ref<AnalyticsGoalRiskPayload | null>(null);
const apiWeakNodes = ref<WeakNodePayload[] | null>(null);
const selectedWeakNode = ref<WeakNodePayload | null>(null);
const remediationForm = ref<RemediationDraft | null>(null);
const remediationSaving = ref(false);
const remediationError = ref<string | null>(null);
const createdRemediationTask = ref<TaskPayload | null>(null);

type MetricItem = {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
};

type RiskItem = {
  title: string;
  body: string;
};

type ProgressMasteryItem = MasteryItem & {
  weakNode: WeakNodePayload | null;
};

const hasAnalytics = computed(
  () =>
    apiMastery.value &&
    apiErrors.value &&
    apiTime.value &&
    apiGoalRisk.value &&
    apiWeakNodes.value,
);
const progressSourceLabel = computed(() => (hasAnalytics.value ? "正式数据" : "原型数据"));
const progressSourceTone = computed<Tone>(() => (hasAnalytics.value ? "green" : "blue"));
const riskSourceLabel = computed(() => (hasAnalytics.value ? "聚合风险" : "需解释"));
const riskSourceTone = computed<Tone>(() => (hasAnalytics.value ? "yellow" : "red"));

const progressMetrics = computed<MetricItem[]>(() => {
  if (!apiMastery.value || !apiErrors.value || !apiTime.value) {
    return [
      {
        label: "稳定掌握",
        value: "18 个",
        detail: "多时间点证据达标",
        tone: "green",
      },
      {
        label: "待巩固",
        value: "7 个",
        detail: "需要变式或间隔复测",
        tone: "yellow",
      },
      {
        label: "需回退",
        value: "3 个",
        detail: "抽测失败或错因重复",
        tone: "red",
      },
    ];
  }
  const stableCount = countStagesAtLeast(apiMastery.value.stage_distribution, 5);
  const regressedCount = countBucket(apiErrors.value.by_status, "regressed");
  return [
    {
      label: "稳定掌握",
      value: `${stableCount} 个`,
      detail: `${apiMastery.value.latest_snapshot_count} 个最新快照`,
      tone: "green",
    },
    {
      label: "待巩固",
      value: `${apiMastery.value.weak_node_count} 个`,
      detail: "存在薄弱节点或阻塞原因",
      tone: "yellow",
    },
    {
      label: "需回退",
      value: `${regressedCount} 个`,
      detail: `错题 ${apiErrors.value.total_wrong_records} 条，实际 ${apiTime.value.actual_minutes} 分钟`,
      tone: regressedCount > 0 ? "red" : "blue",
    },
  ];
});

const masteryRows = computed<ProgressMasteryItem[]>(() => {
  if (!apiWeakNodes.value) {
    return study.mastery.map((item) => ({ ...item, weakNode: null }));
  }
  if (apiWeakNodes.value.length === 0) {
    return [
      {
        node: "当前没有薄弱节点",
        stage: "稳定",
        accuracy: "0 阻塞",
        evidence: "后端薄弱图谱没有返回待处理节点。",
        tone: "green",
        weakNode: null,
      },
    ];
  }
  return apiWeakNodes.value.map((node) => ({
    node: node.label,
    stage: stageLabel(node.latest_stage),
    accuracy:
      node.repeat_error_rate === null ? `${node.evidence_count} 条证据` : `错因率 ${node.repeat_error_rate}%`,
    evidence: evidenceLabel(node),
    tone: toneForStage(node.latest_stage, node.blocking_reasons),
    weakNode: node,
  }));
});

function localDateString(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function openRemediationEditor(node: WeakNodePayload): void {
  selectedWeakNode.value = node;
  remediationForm.value = remediationDraft(node, localDateString());
  remediationError.value = null;
  createdRemediationTask.value = null;
}

function closeRemediationEditor(): void {
  selectedWeakNode.value = null;
  remediationForm.value = null;
  remediationError.value = null;
}

async function createRemediationTask(): Promise<void> {
  if (!selectedWeakNode.value || !remediationForm.value) return;
  const validationError = validateRemediationDraft(remediationForm.value, localDateString());
  if (validationError) {
    remediationError.value = validationError;
    return;
  }
  remediationSaving.value = true;
  remediationError.value = null;
  try {
    const response = await new ApiClient().createTask(
      remediationTaskPayload(selectedWeakNode.value, remediationForm.value),
    );
    createdRemediationTask.value = response.data;
    selectedWeakNode.value = null;
    remediationForm.value = null;
  } catch (error) {
    remediationError.value =
      error instanceof ApiClientError
        ? error.error.message
        : "补救任务创建失败，请保留当前内容并重试。";
  } finally {
    remediationSaving.value = false;
  }
}

const riskItems = computed<RiskItem[]>(() => {
  if (!apiErrors.value || !apiGoalRisk.value || !apiTime.value || !apiMastery.value) {
    return [
      {
        title: "偏差原因",
        body: "841 综合题用时连续超出预估，说明前置概念不稳。",
      },
      {
        title: "建议行动",
        body: "拆小为判据识别、符号检查、例题复述三类任务。",
      },
      {
        title: "回退条件",
        body: "若隔日抽测低于阈值，回退到基础应用并缩短复习间隔。",
      },
    ];
  }
  const timeDelta = apiTime.value.actual_minutes - apiTime.value.estimated_minutes;
  const firstRisk = apiGoalRisk.value.risky_goals[0];
  return [
    {
      title: "偏差原因",
      body:
        timeDelta > 0
          ? `实际用时比预估多 ${timeDelta} 分钟，需检查任务拆分和前置掌握。`
          : "实际用时未超过预估，继续观察掌握证据和错因重复。",
    },
    {
      title: "建议行动",
      body: firstRisk
        ? `优先处理「${firstRisk.title}」，当前进度 ${firstRisk.progress}%，风险 ${firstRisk.risk_status}。`
        : "当前没有高风险目标，优先推进薄弱节点的变式和间隔复测。",
    },
    {
      title: "回退条件",
      body: `${apiMastery.value.weak_node_count} 个薄弱节点，${apiErrors.value.total_wrong_records} 条错题记录；重复错因出现时回退并缩短复习间隔。`,
    },
  ];
});

function countBucket(buckets: CountBucketPayload[], key: string): number {
  return buckets.find((bucket) => bucket.key === key)?.count ?? 0;
}

function countStagesAtLeast(buckets: CountBucketPayload[], minStage: number): number {
  return buckets.reduce((total, bucket) => {
    const stage = Number(bucket.key);
    return Number.isFinite(stage) && stage >= minStage ? total + bucket.count : total;
  }, 0);
}

function stageLabel(stage: number): string {
  const labels: Record<number, string> = {
    0: "未接触",
    1: "已接触",
    2: "基础理解",
    3: "基础应用",
    4: "待变式验证",
    5: "稳定掌握",
  };
  return labels[stage] ?? `阶段 ${stage}`;
}

function toneForStage(stage: number, blockingReasons: string[]): Tone {
  if (blockingReasons.length > 0 && stage <= 2) {
    return "red";
  }
  if (blockingReasons.length > 0 || stage <= 3) {
    return "yellow";
  }
  if (stage >= 5) {
    return "green";
  }
  return "blue";
}

function evidenceLabel(node: WeakNodePayload): string {
  const blockers =
    node.blocking_reasons.length > 0 ? node.blocking_reasons.join(" / ") : "等待更多证据";
  return `${node.evidence_count} 条证据 · ${blockers}`;
}

onMounted(async () => {
  const client = new ApiClient();
  try {
    const [mastery, errors, time, goalRisk, weakGraph] = await Promise.all([
      client.analyticsMastery(),
      client.analyticsErrors(),
      client.analyticsTime(),
      client.analyticsGoalRisk(),
      client.weakGraph(),
    ]);
    apiMastery.value = mastery.data;
    apiErrors.value = errors.data;
    apiTime.value = time.data;
    apiGoalRisk.value = goalRisk.data;
    apiWeakNodes.value = weakGraph.data.items;
  } catch {
    apiMastery.value = null;
    apiErrors.value = null;
    apiTime.value = null;
    apiGoalRisk.value = null;
    apiWeakNodes.value = null;
  }
});
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-progress"
  >
    <PageHeader
      kicker="进度"
      title="掌握与风险"
      description="按证据展示掌握阶段、正确率、错因和计划偏差，避免把任务完成等同于掌握。"
    />

    <div class="metric-grid">
      <MetricCard
        v-for="metric in progressMetrics"
        :key="metric.label"
        :label="metric.label"
        :value="metric.value"
        :detail="metric.detail"
        :tone="metric.tone"
      />
    </div>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            掌握判定
          </p>
          <h2>知识点状态</h2>
        </div>
        <StatusTag
          :label="progressSourceLabel"
          :tone="progressSourceTone"
        />
      </div>

      <div
        v-if="createdRemediationTask"
        class="form-message success remediation-success"
        role="status"
      >
        <span>
          已创建「{{ createdRemediationTask.title }}」，计划日期
          {{ createdRemediationTask.planned_date }}。
        </span>
        <div class="form-actions">
          <RouterLink
            class="task-action-button secondary"
            to="/planning"
          >
            查看规划
          </RouterLink>
          <RouterLink
            class="task-action-button secondary"
            to="/today"
          >
            查看今日
          </RouterLink>
        </div>
      </div>

      <form
        v-if="selectedWeakNode && remediationForm"
        class="editor-form inline-task-editor remediation-editor"
        @submit.prevent="createRemediationTask"
      >
        <div class="full-width remediation-context">
          <strong>{{ selectedWeakNode.label }}</strong>
          <span>
            {{ stageLabel(selectedWeakNode.latest_stage) }} ·
            {{ selectedWeakNode.evidence_count }} 条证据 ·
            {{ selectedWeakNode.blocking_reasons.join(" / ") || "等待更多证据" }}
          </span>
        </div>
        <label>
          <span>任务名称</span>
          <input
            v-model="remediationForm.title"
            maxlength="240"
            required
          >
        </label>
        <label>
          <span>计划日期</span>
          <input
            v-model="remediationForm.plannedDate"
            type="date"
            :min="localDateString()"
            required
          >
        </label>
        <label>
          <span>预计分钟</span>
          <input
            v-model.number="remediationForm.estimatedMinutes"
            type="number"
            min="5"
            max="240"
            required
          >
        </label>
        <label>
          <span>优先级</span>
          <select v-model="remediationForm.priority">
            <option value="normal">普通</option>
            <option value="high">高</option>
            <option value="must">必须</option>
          </select>
        </label>
        <label class="full-width">
          <span>补救原因</span>
          <textarea
            v-model="remediationForm.reason"
            rows="3"
            required
          />
        </label>
        <label class="full-width">
          <span>完成标准</span>
          <textarea
            v-model="remediationForm.completionStandard"
            rows="3"
            required
          />
        </label>
        <p
          v-if="remediationError"
          class="form-message error full-width"
          role="alert"
        >
          {{ remediationError }}
        </p>
        <div class="form-actions">
          <button
            type="submit"
            class="task-action-button"
            :disabled="remediationSaving"
          >
            {{ remediationSaving ? "创建中" : "确认创建任务" }}
          </button>
          <button
            type="button"
            class="task-action-button secondary"
            :disabled="remediationSaving"
            @click="closeRemediationEditor"
          >
            取消
          </button>
        </div>
      </form>

      <div class="mastery-list">
        <article
          v-for="item in masteryRows"
          :key="item.node"
          class="mastery-row"
        >
          <div>
            <h3>{{ item.node }}</h3>
            <p>{{ item.evidence }}</p>
          </div>
          <div class="mastery-meta">
            <StatusTag
              :label="item.stage"
              :tone="item.tone"
            />
            <strong>{{ item.accuracy }}</strong>
            <button
              v-if="item.weakNode"
              type="button"
              class="task-action-button"
              @click="openRemediationEditor(item.weakNode)"
            >
              创建补救任务
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            周风险
          </p>
          <h2>原因与行动</h2>
        </div>
        <StatusTag
          :label="riskSourceLabel"
          :tone="riskSourceTone"
        />
      </div>
      <div class="risk-grid">
        <article
          v-for="item in riskItems"
          :key="item.title"
          class="risk-item"
        >
          <strong>{{ item.title }}</strong>
          <p>{{ item.body }}</p>
        </article>
      </div>
    </section>
  </section>
</template>
