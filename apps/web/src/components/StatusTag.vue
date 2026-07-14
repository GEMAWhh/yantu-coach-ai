<script setup lang="ts">
import type { Tone } from "../stores/mockStudy";

withDefaults(defineProps<{
  label: string;
  tone?: Tone;
}>(), {
  tone: "neutral",
});
</script>

<template>
  <span
    class="status-tag"
    :class="`tone-${tone}`"
  >
    {{ label }}
  </span>
</template>
