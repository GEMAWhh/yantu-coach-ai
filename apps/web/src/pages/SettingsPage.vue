<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiClient } from "../api/client";
import type { SettingsProfilePayload, SettingsRulePayload } from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import type { RuleItem, Tone } from "../stores/mockStudy";

const apiProfile = ref<SettingsProfilePayload | null>(null);
const apiRules = ref<SettingsRulePayload[]>([]);
const editing = ref(false);
const saving = ref(false);
const pageError = ref<string | null>(null);
const savedMessage = ref<string | null>(null);
const form = reactive({
  name: "",
  targetSchool: "",
  targetMajor: "",
  examDate: "",
  currentPhase: "",
  coachStyle: "balanced",
  timezone: "Asia/Shanghai",
});

const settingsSourceLabel = computed(() => (apiProfile.value ? "已保存" : "无法读取"));
const settingsSourceTone = computed<Tone>(() => (apiProfile.value ? "green" : "red"));
const profileRows = computed(() => [
  { label: "称呼", value: apiProfile.value?.name ?? "未设置" },
  { label: "目标院校", value: apiProfile.value?.target_school || "未设置" },
  { label: "方向", value: apiProfile.value?.target_major || "未设置" },
  { label: "阶段", value: apiProfile.value?.current_phase || "未设置" },
  { label: "考试日期", value: apiProfile.value?.exam_date || "未设置" },
  { label: "教练风格", value: coachStyleLabel(apiProfile.value?.coach_style) },
  { label: "时区", value: apiProfile.value?.timezone || "未设置" },
]);
const governanceRules = computed<RuleItem[]>(() =>
  apiRules.value.map((rule) => ({
    title: rule.key,
    description: `${rule.path} · ${rule.sha256.slice(0, 12)}`,
    status: rule.version ?? "unversioned",
    tone: "green",
  })),
);

function beginEdit(): void {
  form.name = apiProfile.value?.name ?? "";
  form.targetSchool = apiProfile.value?.target_school ?? "";
  form.targetMajor = apiProfile.value?.target_major ?? "";
  form.examDate = apiProfile.value?.exam_date ?? "";
  form.currentPhase = apiProfile.value?.current_phase ?? "";
  form.coachStyle = apiProfile.value?.coach_style ?? "balanced";
  form.timezone = apiProfile.value?.timezone ?? "Asia/Shanghai";
  editing.value = true;
  pageError.value = null;
  savedMessage.value = null;
}

function cancelEdit(): void {
  editing.value = false;
  pageError.value = null;
}

async function saveProfile(): Promise<void> {
  if (!form.name.trim()) {
    pageError.value = "请填写称呼。";
    return;
  }
  saving.value = true;
  pageError.value = null;
  try {
    const response = await new ApiClient().updateSettingsProfile({
      name: form.name.trim(),
      target_school: form.targetSchool.trim() || null,
      target_major: form.targetMajor.trim() || null,
      exam_date: form.examDate || null,
      current_phase: form.currentPhase.trim() || null,
      coach_style: form.coachStyle,
      timezone: form.timezone,
    });
    apiProfile.value = response.data;
    editing.value = false;
    savedMessage.value = "学习画像已保存。";
  } catch {
    pageError.value = "保存失败，请检查网络后重试。";
  } finally {
    saving.value = false;
  }
}

function coachStyleLabel(value?: string): string {
  return ({ balanced: "均衡", strict: "严格", supportive: "鼓励" } as Record<string, string>)[
    value ?? ""
  ] ?? value ?? "未设置";
}

onMounted(async () => {
  const client = new ApiClient();
  const [profileResult, rulesResult] = await Promise.allSettled([
    client.settingsProfile(),
    client.settingsRules(),
  ]);
  if (profileResult.status === "fulfilled") {
    apiProfile.value = profileResult.value.data;
  }
  if (rulesResult.status === "fulfilled") {
    apiRules.value = rulesResult.value.data.items;
  }
  if (profileResult.status === "rejected") {
    pageError.value = "学习画像读取失败；仍可填写并保存新设置。";
  } else if (rulesResult.status === "rejected") {
    pageError.value = "治理规则暂时无法读取，学习画像仍可正常编辑。";
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
      title="学习画像与规则"
      description="维护考试目标和辅导偏好；保存后刷新页面仍会保留。"
      :action-label="!editing ? '编辑学习画像' : undefined"
      @action="beginEdit"
    />

    <p
      v-if="pageError"
      class="form-message error"
      role="alert"
    >
      {{ pageError }}
    </p>
    <p
      v-if="savedMessage"
      class="form-message success"
      role="status"
    >
      {{ savedMessage }}
    </p>

    <div class="content-grid two-columns">
      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              考试目标
            </p><h2>当前画像</h2>
          </div>
          <StatusTag
            :label="settingsSourceLabel"
            :tone="settingsSourceTone"
          />
        </div>

        <form
          v-if="editing"
          class="editor-form"
          @submit.prevent="saveProfile"
        >
          <label><span>称呼</span><input
            v-model="form.name"
            maxlength="120"
            required
          ></label>
          <label><span>目标院校</span><input
            v-model="form.targetSchool"
            maxlength="160"
          ></label>
          <label><span>专业方向</span><input
            v-model="form.targetMajor"
            maxlength="160"
          ></label>
          <label><span>考试日期</span><input
            v-model="form.examDate"
            type="date"
          ></label>
          <label><span>当前阶段</span><input
            v-model="form.currentPhase"
            maxlength="80"
            placeholder="例如：强化阶段"
          ></label>
          <label>
            <span>教练风格</span>
            <select v-model="form.coachStyle">
              <option value="balanced">均衡</option>
              <option value="strict">严格</option>
              <option value="supportive">鼓励</option>
            </select>
          </label>
          <label><span>时区</span><input
            v-model="form.timezone"
            maxlength="80"
            required
            placeholder="例如 Asia/Shanghai"
          ></label>
          <div class="form-actions">
            <button
              class="task-action-button"
              type="submit"
              :disabled="saving"
            >
              {{ saving ? "保存中" : "保存" }}
            </button>
            <button
              class="task-action-button secondary"
              type="button"
              :disabled="saving"
              @click="cancelEdit"
            >
              取消
            </button>
          </div>
        </form>

        <dl
          v-else
          class="settings-list"
        >
          <div
            v-for="row in profileRows"
            :key="row.label"
          >
            <dt>{{ row.label }}</dt><dd>{{ row.value }}</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              数据安全
            </p><h2>云端个人数据</h2>
          </div>
        </div>
        <div class="backup-card">
          <strong>备份与恢复</strong><p>正式数据迁移前必须创建并校验备份；恢复前生成 pre-restore 备份。</p>
        </div>
        <div class="backup-card">
          <strong>密钥边界</strong><p>浏览器不长期保存访问密钥，模型服务密钥只保存在后端环境变量中。</p>
        </div>
      </section>
    </div>

    <section
      v-if="governanceRules.length"
      class="panel"
    >
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            治理规则
          </p><h2>不可破坏的业务边界</h2>
        </div>
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
