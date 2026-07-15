<script setup lang="ts">
import { ref } from "vue";

import { isPersonalAuthRequired } from "./api/auth";
import PersonalAccessGate from "./components/PersonalAccessGate.vue";
import AppLayout from "./layouts/AppLayout.vue";

const isUnlocked = ref(!isPersonalAuthRequired());
</script>

<template>
  <AppLayout v-if="isUnlocked" />
  <PersonalAccessGate
    v-else
    @unlocked="isUnlocked = true"
  />
</template>
