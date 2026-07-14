<script setup lang="ts">
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore } from "../stores/mockStudy";

const study = useMockStudyStore();
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
            label="本地优先"
            tone="cyan"
          />
        </div>

        <div class="resource-list">
          <article
            v-for="resource in study.resources"
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
            label="模拟"
            tone="yellow"
          />
        </div>

        <div class="knowledge-map">
          <button
            type="button"
            class="knowledge-node strong"
          >
            稳定掌握
          </button>
          <button
            type="button"
            class="knowledge-node active"
          >
            基础应用
          </button>
          <button
            type="button"
            class="knowledge-node weak"
          >
            待巩固
          </button>
          <button
            type="button"
            class="knowledge-node danger"
          >
            薄弱/衰退
          </button>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            错题闭环
          </p>
          <h2>确认、重做、变式、间隔复测</h2>
        </div>
        <StatusTag
          label="证据驱动"
          tone="blue"
        />
      </div>
      <div class="step-grid">
        <article>
          <strong>1. 分类上传</strong>
          <p>题干、作答、答案、解析、错因、重做和变式附件分别保存。</p>
        </article>
        <article>
          <strong>2. 用户确认</strong>
          <p>OCR 或 AI 结构化结果必须由用户确认后才进入正式记录。</p>
        </article>
        <article>
          <strong>3. 隔日重做</strong>
          <p>原题即时正确最多推进到待变式验证，不直接标记解决。</p>
        </article>
        <article>
          <strong>4. 稳定修正</strong>
          <p>无提示重做、变式和间隔复测均通过后，才可稳定修正。</p>
        </article>
      </div>
    </section>
  </section>
</template>
