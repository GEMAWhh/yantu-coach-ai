<script setup lang="ts">
type NavEntry = {
  label: string;
  description: string;
};

const navEntries: NavEntry[] = [
  { label: "今日", description: "计划、执行记录、学习证据" },
  { label: "规划", description: "学期、季度、月、周、日目标" },
  { label: "学习", description: "资料、题库、错题、复习卡片" },
  { label: "进度", description: "偏差、掌握阶段、正确率、风险" },
  { label: "设置", description: "考试信息、规则、AI 配置、数据管理" },
];
</script>

<template>
  <main class="app-shell">
    <section class="workspace">
      <header class="workspace-header">
        <p class="eyebrow">
          本地优先学习闭环
        </p>
        <h1 data-testid="app-title">
          研途教练
        </h1>
        <p class="summary">
          当前骨架只验证工程启动、入口结构和质量门禁；学习业务将在后续 Issue 中实现。
        </p>
      </header>

      <nav
        class="primary-nav"
        aria-label="一级导航"
      >
        <button
          v-for="entry in navEntries"
          :key="entry.label"
          class="nav-entry"
          type="button"
          data-testid="nav-entry"
        >
          <span class="nav-label">{{ entry.label }}</span>
          <span class="nav-description">{{ entry.description }}</span>
        </button>
      </nav>
    </section>
  </main>
</template>
