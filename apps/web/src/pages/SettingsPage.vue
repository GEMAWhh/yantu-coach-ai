<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClient } from "../api/client";
import type { SettingsProfilePayload, SettingsRulePayload } from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore, type RuleItem, type Tone } from "../stores/mockStudy";

const study = useMockStudyStore();
const apiProfile = ref<SettingsProfilePayload | null>(null);
const apiRules = ref<SettingsRulePayload[] | null>(null);
const settingsSourceLabel = computed(() => (apiProfile.value ? "正式数据" : "原型数据"));
const settingsSourceTone = computed<Tone>(() => (apiProfile.value ? "green" : "yellow"));
const ruleSourceLabel = computed(() => (apiRules.value ? "正式规则" : "展示态"));
const ruleSourceTone = computed<Tone>(() => (apiRules.value ? "green" : "cyan"));

const profileRows = computed(() => [
  {
    label: "目标院校",
    value: apiProfile.value?.target_school ?? "大连理工大学",
  },
  {
    label: "方向",
    value: apiProfile.value?.target_major ?? "控制科学与工程学硕",
  },
  {
    label: "阶段",
    value: apiProfile.value?.current_phase ?? "需要用户确认",
  },
  {
    label: "考试日期",
    value: apiProfile.value?.exam_date ?? "未设置",
  },
  {
    label: "教练风格",
    value: apiProfile.value?.coach_style ?? "balanced",
  },
]);

const governanceRules = computed<RuleItem[]>(() => {
  if (!apiRules.value) {
    return study.governanceRules;
  }
  return apiRules.value.map((rule) => ({
    title: rule.key,
    description: `${rule.path} · ${rule.sha256.slice(0, 12)}`,
    status: rule.version ?? "unversioned",
    tone: "green",
  }));
});

onMounted(async () => {
  const client = new ApiClient();
  try {
    const [profileResponse, rulesResponse] = await Promise.all([
      client.settingsProfile(),
      client.settingsRules(),
    ]);
    apiProfile.value = profileResponse.data;
    apiRules.value = rulesResponse.data.items;
  } catch {
    apiProfile.value = null;
    apiRules.value = null;
  }
});
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-settings"
  >
    <PageHeader
      kicker="设置"
      title="规则与数据安全"
      description="集中管理考试信息、学习画像、AI 草稿边界、备份恢复和本地数据规则。"
      action-label="检查规则版本"
    />

    <div class="content-grid two-columns">
      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              考试目标
            </p>
            <h2>当前画像</h2>
          </div>
          <StatusTag
            :label="settingsSourceLabel"
            :tone="settingsSourceTone"
          />
        </div>
        <dl class="settings-list">
          <div
            v-for="row in profileRows"
            :key="row.label"
          >
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              数据安全
            </p>
            <h2>本地优先</h2>
          </div>
          <StatusTag
            label="默认 127.0.0.1"
            tone="green"
          />
        </div>
        <div class="backup-card">
          <strong>备份与恢复</strong>
          <p>正式数据迁移前必须创建并校验备份；恢复前会自动生成 pre-restore 备份。</p>
        </div>
        <div class="backup-card">
          <strong>密钥边界</strong>
          <p>前端不保存 API Key，构建产物和测试快照不得包含完整密钥。</p>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            治理规则
          </p>
          <h2>不可破坏的业务边界</h2>
        </div>
        <StatusTag
          :label="ruleSourceLabel"
          :tone="ruleSourceTone"
        />
      </div>
      <div class="rule-grid">
        <article
          v-for="rule in governanceRules"
          :key="rule.title"
          class="rule-card"
        >
          <StatusTag
            :label="rule.status"
            :tone="rule.tone"
          />
          <h3>{{ rule.title }}</h3>
          <p>{{ rule.description }}</p>
        </article>
      </div>
    </section>
  </section>
</template>
