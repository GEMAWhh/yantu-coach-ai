<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";

import { promptDestinations, studyPromptTemplates } from "../features/promptToolbox/templates";
import StatusTag from "./StatusTag.vue";

const STORAGE_KEY = "yantu.studyPromptDraft.v1";

type Feedback = {
  kind: "success" | "error";
  message: string;
};

type StoredDraft = {
  templateId: string;
  subject: string;
  material: string;
  attempt: string;
  focus: string;
  finalPrompt: string;
};

const selectedTemplateId = ref(studyPromptTemplates[0].id);
const form = reactive({
  subject: "",
  material: "",
  attempt: "",
  focus: "",
});
const finalPrompt = ref("");
const feedback = ref<Feedback | null>(null);
const storageWarning = ref<string | null>(null);
let persistencePaused = false;

const selectedTemplate = computed(
  () =>
    studyPromptTemplates.find((template) => template.id === selectedTemplateId.value) ??
    studyPromptTemplates[0],
);

function selectTemplate(templateId: string): void {
  if (selectedTemplateId.value === templateId) return;
  selectedTemplateId.value = templateId;
  finalPrompt.value = "";
  feedback.value = null;
}

function generatePrompt(): void {
  if (!form.material.trim()) {
    feedback.value = { kind: "error", message: "请先填写题目或学习材料。" };
    return;
  }
  const template = selectedTemplate.value;
  const requirements = template.outputRequirements
    .map((requirement, index) => `${index + 1}. ${requirement}`)
    .join("\n");
  finalPrompt.value = [
    `你是一名严谨的考研学习教练。当前任务是：${template.title}。`,
    "",
    `科目或主题：${form.subject.trim() || "未填写"}`,
    "",
    "【题目或学习材料】",
    form.material.trim(),
    "",
    "【我的作答或当前情况】",
    form.attempt.trim() || "未提供，请不要假设我已经掌握任何步骤。",
    "",
    "【希望重点处理】",
    form.focus.trim() || "按任务要求处理，并指出最需要我确认的信息。",
    "",
    "【输出要求】",
    requirements,
    "",
    "【共同约束】",
    "- 看不清、信息不足或存在冲突时，明确指出，不得补造题干、公式、答案或学习事实。",
    "- 区分材料直接支持的事实、你的推断和仍不确定的内容。",
    "- 建议不能直接视为正式学习记录、掌握结论或计划变更。",
    "- 使用清晰的中文分节回答，避免空泛鼓励。",
  ].join("\n");
  feedback.value = { kind: "success", message: "Prompt 已生成，你可以继续修改。" };
}

async function copyPrompt(): Promise<void> {
  if (!finalPrompt.value.trim()) {
    feedback.value = { kind: "error", message: "请先生成或填写最终 Prompt。" };
    return;
  }
  try {
    await navigator.clipboard.writeText(finalPrompt.value);
    feedback.value = { kind: "success", message: "Prompt 已复制到剪贴板。" };
  } catch {
    feedback.value = {
      kind: "error",
      message: "复制失败，请选中最终 Prompt 后手动复制。",
    };
  }
}

function openDestination(label: string, url: string): void {
  const opened = window.open("about:blank", "_blank");
  if (!opened) {
    feedback.value = { kind: "error", message: "浏览器阻止了新窗口，请允许弹窗后重试。" };
    return;
  }
  opened.opener = null;
  opened.location.href = url;
  feedback.value = { kind: "success", message: `${label} 已在新窗口打开，请手动粘贴 Prompt。` };
}

async function clearDraft(): Promise<void> {
  persistencePaused = true;
  selectedTemplateId.value = studyPromptTemplates[0].id;
  form.subject = "";
  form.material = "";
  form.attempt = "";
  form.focus = "";
  finalPrompt.value = "";
  feedback.value = { kind: "success", message: "本地草稿已清空。" };
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    storageWarning.value = "浏览器未允许清理本地草稿。";
  }
  await nextTick();
  persistencePaused = false;
}

function persistDraft(): void {
  if (persistencePaused) return;
  const draft: StoredDraft = {
    templateId: selectedTemplateId.value,
    subject: form.subject,
    material: form.material,
    attempt: form.attempt,
    focus: form.focus,
    finalPrompt: finalPrompt.value,
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    storageWarning.value = null;
  } catch {
    storageWarning.value = "本地草稿保存失败，本页关闭后内容可能丢失。";
  }
}

function restoreDraft(): void {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const draft = JSON.parse(raw) as Partial<StoredDraft>;
    if (
      typeof draft.templateId === "string" &&
      studyPromptTemplates.some((template) => template.id === draft.templateId)
    ) {
      selectedTemplateId.value = draft.templateId;
    }
    form.subject = stringValue(draft.subject);
    form.material = stringValue(draft.material);
    form.attempt = stringValue(draft.attempt);
    form.focus = stringValue(draft.focus);
    finalPrompt.value = stringValue(draft.finalPrompt);
  } catch {
    storageWarning.value = "本地草稿无法读取，可清空后重新填写。";
  }
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

watch(
  () => ({
    templateId: selectedTemplateId.value,
    subject: form.subject,
    material: form.material,
    attempt: form.attempt,
    focus: form.focus,
    finalPrompt: finalPrompt.value,
  }),
  persistDraft,
  { deep: true },
);

onMounted(restoreDraft);
</script>

<template>
  <section
    class="panel prompt-toolbox"
    aria-labelledby="prompt-toolbox-title"
  >
    <div class="section-heading">
      <div>
        <p class="eyebrow">
          Prompt 工具箱
        </p>
        <h2 id="prompt-toolbox-title">
          选择任务，再去常用模型中对话
        </h2>
      </div>
      <StatusTag
        label="仅本地草稿"
        tone="cyan"
      />
    </div>

    <p class="prompt-toolbox-intro">
      系统只生成并复制 Prompt，不会调用模型或自动发送内容；模型回答也不会自动写入正式记录。
    </p>

    <div
      class="prompt-template-tabs"
      role="tablist"
      aria-label="学习 Prompt 类型"
    >
      <button
        v-for="template in studyPromptTemplates"
        :key="template.id"
        type="button"
        role="tab"
        :aria-selected="selectedTemplateId === template.id"
        :class="{ selected: selectedTemplateId === template.id }"
        @click="selectTemplate(template.id)"
      >
        <strong>{{ template.title }}</strong>
        <span>{{ template.summary }}</span>
      </button>
    </div>

    <form
      class="prompt-builder"
      @submit.prevent="generatePrompt"
    >
      <div class="prompt-fields">
        <label>
          <span>科目或主题</span>
          <input
            v-model="form.subject"
            maxlength="120"
            placeholder="例如：数学一 · 导数应用"
          >
        </label>
        <label>
          <span>希望重点处理</span>
          <input
            v-model="form.focus"
            maxlength="500"
            :placeholder="selectedTemplate.focusHint"
          >
        </label>
        <label class="full-width">
          <span>题目或学习材料</span>
          <textarea
            v-model="form.material"
            rows="7"
            required
            :placeholder="selectedTemplate.materialHint"
          />
        </label>
        <label class="full-width">
          <span>我的作答或当前情况</span>
          <textarea
            v-model="form.attempt"
            rows="5"
            :placeholder="selectedTemplate.attemptHint"
          />
        </label>
      </div>

      <div class="prompt-form-actions">
        <button
          class="task-action-button"
          type="submit"
        >
          生成 Prompt
        </button>
        <button
          class="task-action-button secondary"
          type="button"
          @click="clearDraft"
        >
          清空草稿
        </button>
      </div>
    </form>

    <div class="prompt-output">
      <label for="final-study-prompt">最终 Prompt（可继续修改）</label>
      <textarea
        id="final-study-prompt"
        v-model="finalPrompt"
        rows="18"
        placeholder="填写材料并点击“生成 Prompt”后，这里会出现可编辑的完整内容。"
      />
      <div class="prompt-form-actions">
        <button
          class="task-action-button"
          type="button"
          @click="copyPrompt"
        >
          复制 Prompt
        </button>
      </div>
    </div>

    <p
      v-if="feedback"
      class="form-message"
      :class="feedback.kind"
      :role="feedback.kind === 'error' ? 'alert' : 'status'"
    >
      {{ feedback.message }}
    </p>
    <p
      v-if="storageWarning"
      class="form-message error"
      role="alert"
    >
      {{ storageWarning }}
    </p>

    <div class="prompt-destinations">
      <div>
        <strong>打开外部 Chat</strong>
        <p>新窗口只打开网站，不会携带或发送上面的 Prompt。</p>
      </div>
      <div class="prompt-destination-actions">
        <button
          v-for="destination in promptDestinations"
          :key="destination.id"
          class="task-action-button secondary"
          type="button"
          @click="openDestination(destination.label, destination.url)"
        >
          {{ destination.label }}
        </button>
      </div>
    </div>
  </section>
</template>
