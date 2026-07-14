<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type { TaskPayload, TodayPayload } from "../api/contracts";
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type TodayTask, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiToday = ref<TodayPayload | null>(null);
const taskSourceLabel = computed(() => (apiToday.value ? "正式数据" : "模拟数据"));
const taskSourceTone = computed<Tone>(() => (apiToday.value ? "green" : "cyan"));
const todayTasks = computed(() => apiToday.value?.tasks.map(mapTask) ?? study.todayTasks);
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
    value: "2 份",
    detail: "确认前不写正式记录",
    tone: "yellow" as Tone,
  },
]);

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

function mapTask(task: TaskPayload): TodayTask {
  return {
    id: task.id,
    subject: task.subject_id ?? task.task_type,
    title: task.title,
    source: `${task.source_type}${task.source_id ? ` / ${task.source_id}` : ""}`,
    reason: task.reason ?? task.completion_standard ?? "待补充执行理由",
    estimateMinutes: task.estimated_minutes,
    status: task.status,
    tone: toneForStatus(task.status),
  };
}

onMounted(async () => {
  try {
    const today = new Date().toISOString().slice(0, 10);
    const response = await new ApiClient().today(today);
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
          </article>
        </div>
      </section>

      <aside class="panel stacked-panel">
        <section class="notice-card ai-draft">
          <StatusTag
            label="AI 草稿 · 待确认"
            tone="yellow"
          />
          <h2>昨日复盘草稿</h2>
          <p>
            已识别 2 个高频错因：条件遗漏、符号方向误判。用户确认前，不更新掌握判定和后续计划。
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
