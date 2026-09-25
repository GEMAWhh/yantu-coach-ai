<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { primaryNavItems } from "../app/navigation";
import { isDemoApiEnabled } from "../api/demoClient";

const route = useRoute();

const currentLabel = computed(() => {
  return primaryNavItems.find((item) => item.name === route.name)?.label ?? "今日";
});
const systemLabel = isDemoApiEnabled() ? "本地预览" : "云端个人版";
</script>

<template>
  <div class="app-layout">
    <aside
      class="app-sidebar"
      aria-label="应用侧栏"
    >
      <RouterLink
        class="brand"
        to="/today"
      >
        <span class="brand-mark">研</span>
        <span>
          <strong data-testid="app-title">研途教练</strong>
          <small>本地优先学习闭环</small>
        </span>
      </RouterLink>

      <nav
        class="side-nav"
        aria-label="一级导航"
      >
        <RouterLink
          v-for="item in primaryNavItems"
          :key="item.name"
          class="nav-link"
          :to="item.path"
          data-testid="primary-nav-link"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>
            <strong>{{ item.label }}</strong>
            <small>{{ item.description }}</small>
          </span>
        </RouterLink>
      </nav>

      <section class="sidebar-note">
        <strong>用户确认必需</strong>
        <p>AI 草稿、证据识别和计划调整在确认前不进入正式记录。</p>
      </section>
    </aside>

    <div class="main-panel">
      <header class="topbar">
        <div>
          <span class="topbar-label">当前页面</span>
          <strong>{{ currentLabel }}</strong>
        </div>
        <span class="system-pill">{{ systemLabel }}</span>
      </header>

      <main
        class="page-frame"
        tabindex="-1"
      >
        <RouterView />
      </main>
    </div>

    <nav
      class="bottom-nav"
      aria-label="移动一级导航"
    >
      <RouterLink
        v-for="item in primaryNavItems"
        :key="item.name"
        class="bottom-nav-link"
        :to="item.path"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
