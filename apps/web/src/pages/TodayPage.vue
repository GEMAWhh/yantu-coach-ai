<script setup lang="ts">
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore } from "../stores/mockStudy";

const study = useMockStudyStore();
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-today"
  >
    <PageHeader
      kicker="今日"
      title="今日行动"
      description="把周目标压到今天可执行的任务、证据确认和复盘动作；当前页面只使用模拟数据。"
      action-label="开始第一项"
    />

    <div class="metric-grid">
      <MetricCard
        label="今日任务"
        value="4 项"
        detail="预计 125 分钟"
        tone="blue"
      />
      <MetricCard
        label="机动时间"
        value="35 分钟"
        detail="计划不排满全天"
        tone="green"
      />
      <MetricCard
        label="待确认草稿"
        value="2 份"
        detail="确认前不写正式记录"
        tone="yellow"
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
            label="模拟数据"
            tone="cyan"
          />
        </div>

        <div class="task-list">
          <article
            v-for="task in study.todayTasks"
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
