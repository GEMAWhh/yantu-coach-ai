<script setup lang="ts">
import type { Tone } from "../stores/mockStudy";

withDefaults(defineProps<{
  label: string;
  value: string;
  detail: string;
  tone?: Tone;
}>(), {
  tone: "neutral",
});
</script>

<template>
  <article
    class="metric-card"
    :class="`tone-${tone}`"
  >
    <p class="metric-label">
      {{ label }}
    </p>
    <strong>{{ value }}</strong>
    <span>{{ detail }}</span>
  </article>
</template>
