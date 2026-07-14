<script setup lang="ts">
defineProps<{
  kicker: string;
  title: string;
  description: string;
  actionLabel: string;
}>();
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
      class="primary-action"
      type="button"
    >
      {{ actionLabel }}
    </button>
  </header>
</template>
