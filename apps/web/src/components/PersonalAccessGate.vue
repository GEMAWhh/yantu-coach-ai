<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiClient, ApiClientError } from "../api/client";
import {
  clearPersonalAccessKey,
  getPersonalAccessKey,
  setPersonalAccessKey,
} from "../api/auth";

const emit = defineEmits<{
  unlocked: [];
}>();

const accessKey = ref("");
const errorMessage = ref("");
const isChecking = ref(false);

async function verify(key: string): Promise<void> {
  isChecking.value = true;
  errorMessage.value = "";
  setPersonalAccessKey(key);
  try {
    await new ApiClient().authStatus();
    emit("unlocked");
  } catch (error) {
    clearPersonalAccessKey();
    errorMessage.value =
      error instanceof ApiClientError && error.status === 401
        ? "访问密钥不正确，请重新输入。"
        : "暂时无法连接云端服务，请稍后重试。";
  } finally {
    isChecking.value = false;
  }
}

async function submit(): Promise<void> {
  const key = accessKey.value.trim();
  if (key.length < 32) {
    errorMessage.value = "访问密钥至少需要 32 个字符。";
    return;
  }
  await verify(key);
}

onMounted(async () => {
  const storedKey = getPersonalAccessKey();
  if (storedKey) {
    await verify(storedKey);
  }
});
</script>

<template>
  <main class="access-gate">
    <section
      class="access-card"
      aria-labelledby="access-title"
    >
      <div
        class="access-brand"
        aria-hidden="true"
      >
        研
      </div>
      <p class="eyebrow">
        云端个人版
      </p>
      <h1 id="access-title">
        进入研途教练
      </h1>
      <p class="access-description">
        输入你的个人访问密钥。密钥只保存在当前浏览器会话中。
      </p>

      <form
        class="access-form"
        novalidate
        @submit.prevent="submit"
      >
        <label for="personal-access-key">个人访问密钥</label>
        <input
          id="personal-access-key"
          v-model="accessKey"
          type="password"
          autocomplete="current-password"
          minlength="32"
          :disabled="isChecking"
          placeholder="请输入至少 32 个字符"
        >
        <p
          v-if="errorMessage"
          class="access-error"
          role="alert"
        >
          {{ errorMessage }}
        </p>
        <button
          class="primary-button access-submit"
          type="submit"
          :disabled="isChecking"
        >
          {{ isChecking ? "正在验证…" : "安全进入" }}
        </button>
      </form>
    </section>
  </main>
</template>
