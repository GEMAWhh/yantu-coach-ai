<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type {
  AnalyticsErrorsPayload,
  AnalyticsGoalRiskPayload,
  AnalyticsMasteryPayload,
  AnalyticsTimePayload,
  CountBucketPayload,
  WeakNodePayload,
} from "../api/contracts";
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type MasteryItem, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiMastery = ref<AnalyticsMasteryPayload | null>(null);
const apiErrors = ref<AnalyticsErrorsPayload | null>(null);
const apiTime = ref<AnalyticsTimePayload | null>(null);
const apiGoalRisk = ref<AnalyticsGoalRiskPayload | null>(null);
const apiWeakNodes = ref<WeakNodePayload[] | null>(null);

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

const masteryRows = computed<MasteryItem[]>(() => {
  if (!apiWeakNodes.value) {
    return study.mastery;
  }
  if (apiWeakNodes.value.length === 0) {
    return [
      {
        node: "当前没有薄弱节点",
        stage: "稳定",
        accuracy: "0 阻塞",
        evidence: "后端薄弱图谱没有返回待处理节点。",
        tone: "green",
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
  }));
});

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
