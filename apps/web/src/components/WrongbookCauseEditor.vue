<script setup lang="ts">
import { ref, watch } from "vue";
import { ApiClient } from "../api/client";
import type { WrongbookDraftHistoryItemPayload } from "../api/contracts";

const props = defineProps<{ item: WrongbookDraftHistoryItemPayload }>();
const emit = defineEmits<{ saved: [recordId: string]; dirty: [value: boolean] }>();
const form = ref({ surface_cause: "", deep_cause: "", prerequisite_gap: "" });
const saving = ref(false);
const message = ref("");
const failed = ref(false);

watch(() => [props.item.record.id, props.item.draft?.id], () => {
  const draft = props.item.draft?.structured_json;
  for (const field of Object.keys(form.value) as Array<keyof typeof form.value>) {
    const value = draft?.[field] ?? props.item.record[field];
    form.value[field] = typeof value === "string" ? value : "";
  }
  message.value = "";
  emit("dirty", false);
}, { immediate: true });

async function save(): Promise<void> {
  if (saving.value) return;
  const values = Object.fromEntries(Object.entries(form.value).map(([key, value]) => [key, value.trim()]));
  if (Object.values(values).some((value) => !value)) {
    failed.value = true;
    message.value = "请填写三项错因；没有需要补的基础可以填“暂无”。";
    return;
  }
  saving.value = true;
  emit("dirty", true);
  message.value = "";
  try {
    const response = await new ApiClient().saveManualWrongbookDraft(props.item.record.id, {
      ...values,
      remediation_plan: props.item.draft?.structured_json.remediation_plan ?? [],
      uncertain_fields: props.item.draft?.structured_json.uncertain_fields ?? [],
    });
    if (response.data.draft.status !== "draft") throw new Error("Invalid draft");
    emit("saved", props.item.record.id);
    failed.value = false;
    message.value = "错因已保存为草稿，请确认后安排重做。";
  } catch {
    failed.value = true;
    message.value = "错因保存失败，输入已保留，请重试。";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <form
    class="wrongbook-capture-form"
    @submit.prevent="save"
    @input="emit('dirty', true)"
  >
    <strong>填写或修改错因</strong>
    <label class="field">
      <span>哪里做错了</span>
      <textarea
        v-model="form.surface_cause"
        rows="2"
        :disabled="saving"
        placeholder="例如：漏掉了参数小于零的情况"
      />
    </label>
    <label class="field">
      <span>为什么会做错</span>
      <textarea
        v-model="form.deep_cause"
        rows="2"
        :disabled="saving"
        placeholder="例如：没有先分类讨论，就直接套公式"
      />
    </label>
    <label class="field">
      <span>需要补什么基础</span>
      <textarea
        v-model="form.prerequisite_gap"
        rows="2"
        :disabled="saving"
        placeholder="没有缺口可以填：暂无"
      />
    </label>
    <p
      v-if="message"
      role="status"
      :class="failed ? 'task-action-error' : 'task-action-success'"
    >
      {{ message }}
    </p>
    <button
      class="primary-action"
      type="submit"
      :disabled="saving"
    >
      {{ saving ? "正在保存…" : "保存错因草稿" }}
    </button>
  </form>
</template>
