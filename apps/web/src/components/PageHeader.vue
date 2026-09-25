<script setup lang="ts">
defineProps<{
  kicker: string;
  title: string;
  description: string;
  actionLabel?: string;
}>();

defineEmits<{ action: [] }>();
</script>

<template>
  <header class="page-header">
    <div>
      <p class="eyebrow">
        {{ kicker }}
      </p>
      <h1 data-testid="page-title">
        {{ title }}
      </h1>
      <p class="page-summary">
        {{ description }}
      </p>
    </div>
    <button
      v-if="actionLabel"
      class="primary-action"
      type="button"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </button>
  </header>
</template>
