<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type { GoalTreePayload } from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type PlanLevel, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiPlanLevels = ref<PlanLevel[] | null>(null);
const planSourceLabel = computed(() => (apiPlanLevels.value ? "正式数据" : "可追溯"));
const planSourceTone = computed<Tone>(() => (apiPlanLevels.value ? "green" : "green"));
const planLevels = computed(() => apiPlanLevels.value ?? study.planLevels);

function toneForGoal(goal: GoalTreePayload): Tone {
  if (goal.status === "completed") {
    return "green";
  }
  if (goal.risk_status === "slow" || goal.risk_status === "delayed") {
    return "yellow";
  }
  if (goal.risk_status === "blocked" || goal.status === "delayed") {
    return "red";
  }
  return "blue";
}

function flattenGoals(goals: GoalTreePayload[]): GoalTreePayload[] {
  return goals.flatMap((goal) => [goal, ...flattenGoals(goal.children)]);
}

function mapGoal(goal: GoalTreePayload): PlanLevel {
  return {
    level: goal.level,
    title: goal.title,
    status: goal.status,
    detail: `${goal.progress}% · ${goal.actual_minutes}/${goal.estimated_minutes} min`,
    tone: toneForGoal(goal),
  };
}

onMounted(async () => {
  try {
    const response = await new ApiClient().goalsTree();
    apiPlanLevels.value = flattenGoals(response.data.items).map(mapGoal);
  } catch {
    apiPlanLevels.value = null;
  }
});
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-planning"
  >
    <PageHeader
      kicker="规划"
      title="五层规划"
      description="从学期目标到每日任务逐级解释来源、风险和机动时间，当前只保留原型级模拟展示。"
      action-label="调整本周计划"
    />

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            目标拆解
          </p>
          <h2>学期 → 季度 → 月 → 周 → 日</h2>
        </div>
        <StatusTag
          :label="planSourceLabel"
          :tone="planSourceTone"
        />
      </div>

      <ol class="timeline">
        <li
          v-for="level in planLevels"
          :key="level.level"
          class="timeline-item"
        >
          <span class="timeline-level">{{ level.level }}</span>
          <div>
            <div class="timeline-title">
              <h3>{{ level.title }}</h3>
              <StatusTag
                :label="level.status"
                :tone="level.tone"
              />
            </div>
            <p>{{ level.detail }}</p>
          </div>
        </li>
      </ol>
    </section>

    <div class="content-grid three-columns">
      <article class="panel compact-panel">
        <StatusTag
          label="计划安全"
          tone="green"
        />
        <h2>保留机动时间</h2>
        <p>日计划不排满全部可用时间，默认保留 20% 左右用于波动、复盘和补救。</p>
      </article>
      <article class="panel compact-panel">
        <StatusTag
          label="单科约束"
          tone="blue"
        />
        <h2>只学某科时不插队</h2>
        <p>选择“只学数学一”时，页面不展示 841 任务作为今日候选。</p>
      </article>
      <article class="panel compact-panel">
        <StatusTag
          label="前置不足"
          tone="red"
        />
        <h2>阻止或降级</h2>
        <p>前置知识不足时，不强行进入综合题，先回到必要基础训练。</p>
      </article>
    </div>
  </section>
</template>
