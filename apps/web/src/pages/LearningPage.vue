<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type {
  KnowledgeNodePayload,
  ResourcePayload,
  WrongbookCandidatePayload,
} from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type LearningResource, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiResources = ref<ResourcePayload[] | null>(null);
const apiKnowledgeNodes = ref<KnowledgeNodePayload[] | null>(null);
const apiWrongbookCandidates = ref<WrongbookCandidatePayload[] | null>(null);

type KnowledgeChip = {
  label: string;
  className: "strong" | "active" | "weak" | "danger";
};

type LoopCard = {
  title: string;
  body: string;
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

const wrongbookCards = computed<LoopCard[]>(() => {
  if (!apiWrongbookCandidates.value) {
    return [
      {
        title: "1. 分类上传",
        body: "题干、作答、答案、解析、错因、重做和变式附件分别保存。",
      },
      {
        title: "2. 用户确认",
        body: "OCR 或 AI 结构化结果必须由用户确认后才进入正式记录。",
      },
      {
        title: "3. 隔日重做",
        body: "原题即时正确最多推进到待变式验证，不直接标记解决。",
      },
      {
        title: "4. 稳定修正",
        body: "无提示重做、变式和间隔复测均通过后，才可稳定修正。",
      },
    ];
  }
  if (apiWrongbookCandidates.value.length === 0) {
    return [
      {
        title: "暂无错题候选",
        body: "当前没有进入今日计划的错题候选，继续按资源和知识图谱推进。",
      },
    ];
  }
  return apiWrongbookCandidates.value.slice(0, 4).map((candidate, index) => ({
    title: `${index + 1}. ${candidate.title}`,
    body: `${candidate.subject_id} · ${candidate.estimated_minutes} 分钟 · 弱项 ${candidate.weakness} · 重复错因 ${candidate.repeat_error}`,
  }));
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

onMounted(async () => {
  const client = new ApiClient();
  try {
    const [resources, knowledgeNodes, wrongbookCandidates] = await Promise.all([
      client.resources(),
      client.knowledgeNodes(),
      client.wrongbookPlanningCandidates(),
    ]);
    apiResources.value = resources.data.items;
    apiKnowledgeNodes.value = knowledgeNodes.data.items;
    apiWrongbookCandidates.value = wrongbookCandidates.data.items;
  } catch {
    apiResources.value = null;
    apiKnowledgeNodes.value = null;
    apiWrongbookCandidates.value = null;
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
            错题闭环
          </p>
          <h2>确认、重做、变式、间隔复测</h2>
        </div>
        <StatusTag
          :label="wrongbookSourceLabel"
          :tone="wrongbookSourceTone"
        />
      </div>
      <div class="step-grid">
        <article
          v-for="card in wrongbookCards"
          :key="card.title"
        >
          <strong>{{ card.title }}</strong>
          <p>{{ card.body }}</p>
        </article>
      </div>
    </section>
  </section>
</template>
