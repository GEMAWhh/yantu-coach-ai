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
    data-testid="page-progress"
  >
    <PageHeader
      kicker="进度"
      title="掌握与风险"
      description="按证据展示掌握阶段、正确率、错因和计划偏差，避免把任务完成等同于掌握。"
      action-label="查看风险来源"
    />

    <div class="metric-grid">
      <MetricCard
        label="稳定掌握"
        value="18 个"
        detail="多时间点证据达标"
        tone="green"
      />
      <MetricCard
        label="待巩固"
        value="7 个"
        detail="需要变式或间隔复测"
        tone="yellow"
      />
      <MetricCard
        label="需回退"
        value="3 个"
        detail="抽测失败或错因重复"
        tone="red"
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
          label="不由勾选决定"
          tone="blue"
        />
      </div>

      <div class="mastery-list">
        <article
          v-for="item in study.mastery"
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
          label="需解释"
          tone="red"
        />
      </div>
      <div class="risk-grid">
        <article class="risk-item">
          <strong>偏差原因</strong>
          <p>841 综合题用时连续超出预估，说明前置概念不稳。</p>
        </article>
        <article class="risk-item">
          <strong>建议行动</strong>
          <p>拆小为判据识别、符号检查、例题复述三类任务。</p>
        </article>
        <article class="risk-item">
          <strong>回退条件</strong>
          <p>若隔日抽测低于阈值，回退到基础应用并缩短复习间隔。</p>
        </article>
      </div>
    </section>
  </section>
</template>
