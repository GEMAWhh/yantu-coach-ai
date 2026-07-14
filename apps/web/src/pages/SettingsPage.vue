<script setup lang="ts">
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { useMockStudyStore } from "../stores/mockStudy";

const study = useMockStudyStore();
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-settings"
  >
    <PageHeader
      kicker="设置"
      title="规则与数据安全"
      description="集中管理考试信息、学习画像、AI 草稿边界、备份恢复和本地数据规则。"
      action-label="检查规则版本"
    />

    <div class="content-grid two-columns">
      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              考试目标
            </p>
            <h2>当前画像</h2>
          </div>
          <StatusTag
            label="需用户确认"
            tone="yellow"
          />
        </div>
        <dl class="settings-list">
          <div>
            <dt>目标院校</dt>
            <dd>大连理工大学</dd>
          </div>
          <div>
            <dt>方向</dt>
            <dd>控制科学与工程学硕</dd>
          </div>
          <div>
            <dt>科目</dt>
            <dd>数学一、专业课 841</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              数据安全
            </p>
            <h2>本地优先</h2>
          </div>
          <StatusTag
            label="默认 127.0.0.1"
            tone="green"
          />
        </div>
        <div class="backup-card">
          <strong>备份与恢复</strong>
          <p>正式数据迁移前必须创建并校验备份；当前页面不连接真实数据目录。</p>
        </div>
        <div class="backup-card">
          <strong>密钥边界</strong>
          <p>前端不保存 API Key，构建产物和测试快照不得包含完整密钥。</p>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            治理规则
          </p>
          <h2>不可破坏的业务边界</h2>
        </div>
        <StatusTag
          label="展示壳"
          tone="cyan"
        />
      </div>
      <div class="rule-grid">
        <article
          v-for="rule in study.governanceRules"
          :key="rule.title"
          class="rule-card"
        >
          <StatusTag
            :label="rule.status"
            :tone="rule.tone"
          />
          <h3>{{ rule.title }}</h3>
          <p>{{ rule.description }}</p>
        </article>
      </div>
    </section>
  </section>
</template>
