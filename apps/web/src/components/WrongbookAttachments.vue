<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { ApiClient } from "../api/client";
import type { AssetPayload, WrongbookAttachmentList, WrongbookAttachmentRole } from "../api/contracts";

const props = defineProps<{ recordId: string }>();
const client = new ApiClient();
const items = ref<WrongbookAttachmentList["items"]>([]);
const role = ref<WrongbookAttachmentRole>("statement");
const file = ref<File | null>(null);
const pending = ref<AssetPayload | null>(null);
const busy = ref(false);
const loaded = ref(false);
const message = ref("");
const preview = ref("");
const previewType = ref("");
const labels: Record<string, string> = { statement: "题目", figure: "题目配图", my_answer: "我的作答", marking: "批改", standard_answer: "答案", original_solution: "答案解析", supplement: "补充" };
function closePreview(): void {
  if (preview.value) URL.revokeObjectURL(preview.value);
  preview.value = "";
}
onBeforeUnmount(closePreview);
async function load(): Promise<void> {
  try { items.value = (await client.wrongbookAttachments(props.recordId)).data.items; loaded.value = true; }
  catch { loaded.value = false; message.value = "附件列表加载失败，请重试。"; }
}
watch(() => props.recordId, () => {
  items.value = []; loaded.value = false; file.value = null; pending.value = null; message.value = ""; closePreview();
  void load();
}, { immediate: true });
function choose(event: Event): void {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null;
  pending.value = null;
  message.value = "";
}
async function upload(): Promise<void> {
  if (!file.value || busy.value || !loaded.value) return;
  const selected = file.value;
  if (!["image/png", "image/jpeg", "application/pdf"].includes(selected.type)) {
    message.value = "请选择 PNG、JPEG 图片或 PDF 文件。"; return;
  }
  busy.value = true;
  try {
    if (!pending.value) {
      const content = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
        reader.onerror = () => reject(new Error("read failed"));
        reader.readAsDataURL(selected);
      });
      pending.value = (await client.uploadAsset({ original_name: selected.name, mime_type: selected.type as AssetPayload["mime_type"], content_base64: content, state: "inbox" })).data;
    }
    const order = Math.max(-1, ...items.value.filter((item) => item.link.asset_role === role.value).map((item) => item.link.page_order)) + 1;
    await client.linkWrongbookAttachment(props.recordId, { asset_id: pending.value.id, asset_role: role.value, page_order: order });
    pending.value = null; file.value = null;
    message.value = "附件已保存。";
    await load();
  } catch { message.value = "附件保存失败，文件已保留，请重试。"; }
  finally { busy.value = false; }
}
async function open(asset: AssetPayload): Promise<void> {
  closePreview();
  try {
    const result = (await client.evidenceAssetContent(asset.id)).data;
    const bytes = Uint8Array.from(atob(result.content_base64), (char) => char.charCodeAt(0));
    preview.value = URL.createObjectURL(new Blob([bytes], { type: asset.mime_type }));
    previewType.value = asset.mime_type;
  } catch { message.value = "附件打开失败，请重试。"; }
}
</script>

<template>
  <section class="attachments">
    <h4>题目原件与作答</h4>
    <form @submit.prevent="upload">
      <label class="field"><span>附件类型</span><select
        v-model="role"
        :disabled="busy"
      ><option value="statement">题目</option><option value="my_answer">我的作答</option><option value="original_solution">答案解析</option></select></label>
      <label class="field"><span>选择图片或 PDF</span><input
        type="file"
        accept="image/png,image/jpeg,application/pdf"
        :disabled="busy"
        @change="choose"
      ></label>
      <label class="field"><span>拍照</span><input
        type="file"
        accept="image/png,image/jpeg"
        capture="environment"
        :disabled="busy"
        @change="choose"
      ></label>
      <button
        type="submit"
        :disabled="!file || busy || !loaded"
      >
        {{ busy ? '正在保存…' : '保存附件' }}
      </button>
    </form>
    <p
      v-if="message"
      role="status"
    >
      {{ message }}
    </p>
    <button
      v-if="!loaded"
      type="button"
      @click="load"
    >
      重新加载附件
    </button>
    <ul>
      <li
        v-for="item in items"
        :key="item.link.id"
      >
        <span>{{ labels[item.link.asset_role] }} · {{ item.asset.original_name }}</span><button
          type="button"
          @click="open(item.asset)"
        >
          查看
        </button>
      </li>
    </ul>
    <template v-if="preview">
      <img
        v-if="previewType !== 'application/pdf'"
        :src="preview"
        alt="错题附件预览"
      >
      <a
        v-else
        :href="preview"
        target="_blank"
        rel="noopener"
      >打开 PDF</a>
      <button
        type="button"
        @click="closePreview"
      >
        收起原件
      </button>
    </template>
  </section>
</template>

<style scoped>
.attachments { border-top: 1px solid #dbe3ef; padding: 16px 0; }
form { display: grid; gap: 12px; }
input, select { max-width: 100%; min-width: 0; }
select { width: 100%; padding: 10px; border: 1px solid #ccd9ec; border-radius: 6px; background: white; font: inherit; }
input[type="file"] { width: 100%; font: inherit; font-size: 14px; }
button { padding: 9px 14px; border: 1px solid #ccd9ec; border-radius: 6px; background: #fff; color: #193454; font: inherit; cursor: pointer; }
button[type="submit"] { background: #2d6bec; color: white; border-color: #2d6bec; }
button:disabled { opacity: .5; cursor: default; }
ul { list-style: none; padding: 0; }
li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 0; }
li span { overflow-wrap: anywhere; min-width: 0; }
li button { flex-shrink: 0; }
img { display: block; max-width: 100%; max-height: 600px; object-fit: contain; margin: 12px 0; }
</style>
