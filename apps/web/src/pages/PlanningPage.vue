<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiClient } from "../api/client";
import type { GoalPayload, GoalTreePayload, TaskPayload } from "../api/contracts";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import type { Tone } from "../stores/mockStudy";

const goals = ref<GoalTreePayload[]>([]);
const tasks = ref<TaskPayload[]>([]);
const loading = ref(true);
const busy = ref(false);
const pageError = ref<string | null>(null);
const pageMessage = ref<string | null>(null);
const editor = ref<"goal" | "task" | null>(null);
const editingGoal = ref<GoalPayload | null>(null);
const editingTask = ref<TaskPayload | null>(null);
const goalForm = reactive({
  title: "",
  level: "week" as GoalPayload["level"],
  subjectId: "",
  startDate: "",
  endDate: "",
  estimatedMinutes: 0,
  description: "",
  completionStandard: "",
});
const taskForm = reactive({
  title: "",
  goalId: "",
  subjectId: "",
  plannedDate: todayString(),
  estimatedMinutes: 30,
  priority: "normal",
  reason: "",
  completionStandard: "",
});

const flatGoals = computed(() => flattenGoals(goals.value));
const activeTasks = computed(() => tasks.value.filter((task) => task.status !== "withdrawn"));

function toneForGoal(goal: GoalPayload): Tone {
  if (goal.status === "completed") return "green";
  if (goal.risk_status === "blocked" || goal.status === "delayed") return "red";
  if (goal.risk_status === "slow" || goal.risk_status === "delayed") return "yellow";
  return "blue";
}

function goalLevelLabel(level: GoalPayload["level"]): string {
  return {
    semester: "学期",
    quarter: "季度",
    month: "月",
    week: "周",
    day: "日",
  }[level];
}

function statusLabel(status: string): string {
  return {
    active: "进行中",
    delayed: "已延期",
    completed: "已完成",
    pending: "待执行",
    in_progress: "进行中",
    skipped: "已跳过",
    withdrawn: "已撤回",
  }[status] ?? status;
}

function flattenGoals(items: GoalTreePayload[]): GoalTreePayload[] {
  return items.flatMap((goal) => [goal, ...flattenGoals(goal.children)]);
}

function openGoalEditor(goal?: GoalPayload): void {
  editingGoal.value = goal ?? null;
  goalForm.title = goal?.title ?? "";
  goalForm.level = goal?.level ?? "week";
  goalForm.subjectId = goal?.subject_id ?? "";
  goalForm.startDate = goal?.start_date ?? "";
  goalForm.endDate = goal?.end_date ?? "";
  goalForm.estimatedMinutes = goal?.estimated_minutes ?? 0;
  goalForm.description = goal?.description ?? "";
  goalForm.completionStandard = goal?.completion_standard ?? "";
  editor.value = "goal";
  clearFeedback();
}

function openTaskEditor(task?: TaskPayload): void {
  editingTask.value = task ?? null;
  taskForm.title = task?.title ?? "";
  taskForm.goalId = task?.goal_id ?? "";
  taskForm.subjectId = task?.subject_id ?? "";
  taskForm.plannedDate = task?.planned_date ?? todayString();
  taskForm.estimatedMinutes = task?.estimated_minutes ?? 30;
  taskForm.priority = task?.priority ?? "normal";
  taskForm.reason = task?.reason ?? "";
  taskForm.completionStandard = task?.completion_standard ?? "";
  editor.value = "task";
  clearFeedback();
}

function closeEditor(): void {
  editor.value = null;
  editingGoal.value = null;
  editingTask.value = null;
  pageError.value = null;
}

async function saveGoal(): Promise<void> {
  if (!goalForm.title.trim()) return fail("请填写目标名称。");
  busy.value = true;
  clearFeedback();
  try {
    const client = new ApiClient();
    if (editingGoal.value) {
      await client.updateGoal(editingGoal.value.id, editingGoal.value.version, {
        title: goalForm.title.trim(),
        description: goalForm.description.trim() || null,
        start_date: goalForm.startDate || null,
        end_date: goalForm.endDate || null,
        estimated_minutes: Math.max(0, goalForm.estimatedMinutes),
        completion_standard: goalForm.completionStandard.trim() || null,
      });
    } else {
      await client.createGoal({
        level: goalForm.level,
        title: goalForm.title.trim(),
        subject_id: goalForm.subjectId.trim() || null,
        description: goalForm.description.trim() || null,
        start_date: goalForm.startDate || null,
        end_date: goalForm.endDate || null,
        estimated_minutes: Math.max(0, goalForm.estimatedMinutes),
        completion_standard: goalForm.completionStandard.trim() || null,
      });
    }
    await loadPlanning();
    editor.value = null;
    pageMessage.value = editingGoal.value ? "目标已更新。" : "目标已创建。";
  } catch {
    fail("目标保存失败，请刷新后重试。");
  } finally {
    busy.value = false;
  }
}

async function saveTask(): Promise<void> {
  if (!taskForm.title.trim()) return fail("请填写任务名称。");
  if (!taskForm.plannedDate) return fail("请选择计划日期。");
  busy.value = true;
  clearFeedback();
  try {
    const client = new ApiClient();
    if (editingTask.value) {
      await client.updateTask(editingTask.value.id, editingTask.value.version, {
        title: taskForm.title.trim(),
        planned_date: taskForm.plannedDate,
        estimated_minutes: Math.max(0, taskForm.estimatedMinutes),
        priority: taskForm.priority,
        reason: taskForm.reason.trim() || null,
        completion_standard: taskForm.completionStandard.trim() || null,
      });
    } else {
      await client.createTask({
        title: taskForm.title.trim(),
        planned_date: taskForm.plannedDate,
        estimated_minutes: Math.max(0, taskForm.estimatedMinutes),
        source_type: taskForm.goalId ? "goal" : "manual",
        source_id: taskForm.goalId || null,
        goal_id: taskForm.goalId || null,
        subject_id: taskForm.subjectId.trim() || null,
        priority: taskForm.priority,
        reason: taskForm.reason.trim() || null,
        completion_standard: taskForm.completionStandard.trim() || null,
      });
    }
    await loadPlanning();
    editor.value = null;
    pageMessage.value = editingTask.value ? "任务已更新。" : "任务已创建。";
  } catch {
    fail("任务保存失败，请刷新后重试。");
  } finally {
    busy.value = false;
  }
}

async function deleteGoal(goal: GoalPayload): Promise<void> {
  if (!window.confirm(`删除“${goal.title}”及其下级目标和关联任务？`)) return;
  busy.value = true;
  try {
    await new ApiClient().deleteGoal(goal.id);
    await loadPlanning();
    pageMessage.value = "目标已删除。";
  } catch {
    fail("目标删除失败，请稍后重试。");
  } finally {
    busy.value = false;
  }
}

async function deleteTask(task: TaskPayload): Promise<void> {
  if (!window.confirm(`删除待执行任务“${task.title}”？`)) return;
  busy.value = true;
  try {
    await new ApiClient().deleteTask(task.id);
    await loadPlanning();
    pageMessage.value = "任务已删除。";
  } catch {
    fail("只有尚未开始且没有结果的任务可以删除。");
  } finally {
    busy.value = false;
  }
}

async function loadPlanning(): Promise<void> {
  const client = new ApiClient();
  const [goalResponse, taskResponse] = await Promise.allSettled([
    client.goalsTree(),
    client.tasks(),
  ]);
  if (goalResponse.status === "fulfilled") {
    goals.value = goalResponse.value.data.items;
  }
  if (taskResponse.status === "fulfilled") {
    tasks.value = taskResponse.value.data.items;
  }
  if (goalResponse.status === "rejected" || taskResponse.status === "rejected") {
    fail("规划数据读取失败，请刷新后重试。");
  }
  loading.value = false;
}

function clearFeedback(): void {
  pageError.value = null;
  pageMessage.value = null;
}

function fail(message: string): void {
  pageError.value = message;
  pageMessage.value = null;
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

onMounted(loadPlanning);
</script>

<template>
  <section
    class="page-stack"
    data-testid="page-planning"
  >
    <PageHeader
      kicker="规划"
      title="目标与任务"
      description="先建立目标，再把目标拆成有日期和预计用时的任务。"
      action-label="新建目标"
      @action="openGoalEditor()"
    />
    <p
      v-if="pageError"
      class="form-message error"
      role="alert"
    >
      {{ pageError }}
    </p>
    <p
      v-if="pageMessage"
      class="form-message success"
      role="status"
    >
      {{ pageMessage }}
    </p>

    <section
      v-if="editor"
      class="panel editor-panel"
    >
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            {{ editor === 'goal' ? '目标编辑' : '任务编辑' }}
          </p><h2>{{ editor === 'goal' ? (editingGoal ? '修改目标' : '新建目标') : (editingTask ? '修改任务' : '新建任务') }}</h2>
        </div>
        <button
          class="task-action-button secondary"
          type="button"
          @click="closeEditor"
        >
          关闭
        </button>
      </div>
      <form
        v-if="editor === 'goal'"
        class="editor-form"
        @submit.prevent="saveGoal"
      >
        <label><span>目标名称</span><input
          v-model="goalForm.title"
          required
          maxlength="240"
        ></label>
        <label><span>层级</span><select
          v-model="goalForm.level"
          :disabled="Boolean(editingGoal)"
        ><option value="semester">学期</option><option value="quarter">季度</option><option value="month">月</option><option value="week">周</option><option value="day">日</option></select></label>
        <label><span>科目</span><input
          v-model="goalForm.subjectId"
          :disabled="Boolean(editingGoal)"
          placeholder="例如 math"
        ></label>
        <label><span>预计分钟</span><input
          v-model.number="goalForm.estimatedMinutes"
          type="number"
          min="0"
        ></label>
        <label><span>开始日期</span><input
          v-model="goalForm.startDate"
          type="date"
        ></label>
        <label><span>结束日期</span><input
          v-model="goalForm.endDate"
          type="date"
        ></label>
        <label class="full-width"><span>目标说明</span><textarea
          v-model="goalForm.description"
          rows="3"
        /></label>
        <label class="full-width"><span>完成标准</span><textarea
          v-model="goalForm.completionStandard"
          rows="2"
        /></label>
        <div class="form-actions">
          <button
            class="task-action-button"
            type="submit"
            :disabled="busy"
          >
            保存目标
          </button><button
            class="task-action-button secondary"
            type="button"
            @click="closeEditor"
          >
            取消
          </button>
        </div>
      </form>
      <form
        v-else
        class="editor-form"
        @submit.prevent="saveTask"
      >
        <label><span>任务名称</span><input
          v-model="taskForm.title"
          required
          maxlength="240"
        ></label>
        <label><span>计划日期</span><input
          v-model="taskForm.plannedDate"
          type="date"
          required
        ></label>
        <label><span>关联目标</span><select
          v-model="taskForm.goalId"
          :disabled="Boolean(editingTask)"
        ><option value="">不关联</option><option
          v-for="goal in flatGoals"
          :key="goal.id"
          :value="goal.id"
        >{{ goal.title }}</option></select></label>
        <label><span>科目</span><input
          v-model="taskForm.subjectId"
          :disabled="Boolean(editingTask)"
          placeholder="例如 math"
        ></label>
        <label><span>预计分钟</span><input
          v-model.number="taskForm.estimatedMinutes"
          type="number"
          min="0"
        ></label>
        <label><span>优先级</span><select v-model="taskForm.priority"><option value="low">低</option><option value="normal">普通</option><option value="high">高</option></select></label>
        <label class="full-width"><span>安排原因</span><textarea
          v-model="taskForm.reason"
          rows="2"
        /></label>
        <label class="full-width"><span>完成标准</span><textarea
          v-model="taskForm.completionStandard"
          rows="2"
        /></label>
        <div class="form-actions">
          <button
            class="task-action-button"
            type="submit"
            :disabled="busy"
          >
            保存任务
          </button><button
            class="task-action-button secondary"
            type="button"
            @click="closeEditor"
          >
            取消
          </button>
        </div>
      </form>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            目标拆解
          </p><h2>你的目标</h2>
        </div><button
          class="task-action-button"
          type="button"
          @click="openGoalEditor()"
        >
          新建目标
        </button>
      </div>
      <p v-if="loading">
        正在读取规划...
      </p>
      <div
        v-else-if="flatGoals.length === 0"
        class="empty-action"
      >
        <h3>还没有目标</h3><p>先创建一个周目标，再安排具体任务。</p><button
          class="task-action-button"
          type="button"
          @click="openGoalEditor()"
        >
          创建第一个目标
        </button>
      </div>
      <ol
        v-else
        class="timeline"
      >
        <li
          v-for="goal in flatGoals"
          :key="goal.id"
          class="timeline-item"
        >
          <span class="timeline-level">{{ goalLevelLabel(goal.level) }}</span>
          <div class="timeline-content">
            <div class="timeline-title">
              <h3>{{ goal.title }}</h3><StatusTag
                :label="statusLabel(goal.status)"
                :tone="toneForGoal(goal)"
              />
            </div><p>{{ goal.progress }}% · {{ goal.actual_minutes }}/{{ goal.estimated_minutes }} 分钟</p><div class="task-actions">
              <button
                class="task-action-button secondary"
                type="button"
                @click="openGoalEditor(goal)"
              >
                编辑
              </button><button
                class="task-action-button danger"
                type="button"
                :disabled="busy"
                @click="deleteGoal(goal)"
              >
                删除
              </button>
            </div>
          </div>
        </li>
      </ol>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">
            执行安排
          </p><h2>全部任务</h2>
        </div><button
          class="task-action-button"
          type="button"
          @click="openTaskEditor()"
        >
          新建任务
        </button>
      </div>
      <div
        v-if="activeTasks.length === 0"
        class="empty-action"
      >
        <h3>还没有任务</h3><p>任务需要明确日期和预计用时，届时会出现在“今日”页面。</p><button
          class="task-action-button"
          type="button"
          @click="openTaskEditor()"
        >
          添加第一项任务
        </button>
      </div>
      <div
        v-else
        class="task-list planning-task-list"
      >
        <article
          v-for="task in activeTasks"
          :key="task.id"
          class="task-card"
        >
          <div class="task-card-header">
            <span class="subject-chip">{{ task.subject_id || '未分科' }}</span><StatusTag
              :label="statusLabel(task.status)"
              :tone="task.status === 'pending' ? 'neutral' : 'blue'"
            />
          </div><h3>{{ task.title }}</h3><p>{{ task.planned_date }} · {{ task.estimated_minutes }} 分钟 · {{ task.reason || '未填写安排原因' }}</p><div class="task-actions">
            <button
              class="task-action-button secondary"
              type="button"
              @click="openTaskEditor(task)"
            >
              编辑
            </button><button
              class="task-action-button danger"
              type="button"
              :disabled="task.status !== 'pending' || busy"
              @click="deleteTask(task)"
            >
              删除
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>
