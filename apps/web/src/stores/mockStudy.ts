import { defineStore } from "pinia";

export type Tone = "neutral" | "blue" | "green" | "yellow" | "red" | "cyan";

export type TodayTask = {
  id: string;
  subject: string;
  title: string;
  source: string;
  reason: string;
  estimateMinutes: number;
  status: string;
  tone: Tone;
};

export type PlanLevel = {
  level: string;
  title: string;
  status: string;
  detail: string;
  tone: Tone;
};

export type LearningResource = {
  title: string;
  meta: string;
  status: string;
  tone: Tone;
};

export type MasteryItem = {
  node: string;
  stage: string;
  accuracy: string;
  evidence: string;
  tone: Tone;
};

export type RuleItem = {
  title: string;
  description: string;
  status: string;
  tone: Tone;
};

export const useMockStudyStore = defineStore("mockStudy", {
  state: () => ({
    todayTasks: [
      {
        id: "task-1",
        subject: "数学一",
        title: "线性代数：矩阵秩与线性方程组闭卷回忆",
        source: "本周目标：线代基础应用",
        reason: "昨天错因集中在秩条件遗漏，需要用闭卷回忆补足前置判断。",
        estimateMinutes: 35,
        status: "训练中",
        tone: "blue",
      },
      {
        id: "task-2",
        subject: "841",
        title: "控制系统稳定性判据例题 2 组",
        source: "月目标：经典控制基础",
        reason: "综合题正确率低于阈值，先回到基础应用阶段。",
        estimateMinutes: 45,
        status: "待完成",
        tone: "neutral",
      },
      {
        id: "task-3",
        subject: "数学一",
        title: "错题 2026-07-13-A 无提示重做",
        source: "错题闭环：条件遗漏",
        reason: "原题即时正确不能标记解决，需要隔日无提示重做。",
        estimateMinutes: 25,
        status: "待巩固",
        tone: "yellow",
      },
      {
        id: "task-4",
        subject: "复盘",
        title: "确认昨日 2 份学习证据草稿",
        source: "每日证据闭环",
        reason: "AI 草稿未确认前，不写入正式学习记录或掌握判定。",
        estimateMinutes: 20,
        status: "待确认",
        tone: "yellow",
      },
    ] satisfies TodayTask[],
    planLevels: [
      {
        level: "学期",
        title: "大连理工大学控制科学与工程学硕一轮基础完成",
        status: "进行中",
        detail: "数学一与 841 保持双主线，先保证核心闭环稳定运行。",
        tone: "blue",
      },
      {
        level: "季度",
        title: "数学一基础应用 + 841 经典控制框架",
        status: "风险可控",
        detail: "本季度目标预留 18% 机动时间，不排满全天。",
        tone: "green",
      },
      {
        level: "月",
        title: "线代、概率基础题型与控制稳定性",
        status: "轻微偏差",
        detail: "841 例题进度慢 1 天，需要减少低价值整理。",
        tone: "yellow",
      },
      {
        level: "周",
        title: "闭卷回忆 + 基础应用 + 错题隔日重做",
        status: "需复盘",
        detail: "错因重复出现，优先提升条件识别训练。",
        tone: "red",
      },
      {
        level: "日",
        title: "4 项任务，预计 125 分钟，保留 35 分钟机动",
        status: "可执行",
        detail: "今日不新增其他科目，遵守单科选择约束。",
        tone: "cyan",
      },
    ] satisfies PlanLevel[],
    resources: [
      {
        title: "线性代数基础讲义第 3 章",
        meta: "已上传，待整理；阅读证据最多进入“已接触”。",
        status: "待整理",
        tone: "neutral",
      },
      {
        title: "控制系统稳定性课堂笔记",
        meta: "已整理 8 个知识点，2 个前置不足。",
        status: "需补前置",
        tone: "yellow",
      },
      {
        title: "错题附件：条件遗漏与符号误判",
        meta: "7 类附件按题目归档，等待用户确认结构化草稿。",
        status: "AI 草稿",
        tone: "yellow",
      },
    ] satisfies LearningResource[],
    mastery: [
      {
        node: "矩阵秩与解的判定",
        stage: "基础应用",
        accuracy: "72%",
        evidence: "闭卷回忆 2 次，基础题 18/25",
        tone: "blue",
      },
      {
        node: "劳斯判据",
        stage: "待巩固",
        accuracy: "61%",
        evidence: "综合题错误集中在符号条件",
        tone: "yellow",
      },
      {
        node: "特征值稳定性直觉",
        stage: "薄弱/衰退",
        accuracy: "48%",
        evidence: "抽测失败，需回退并生成补救任务",
        tone: "red",
      },
      {
        node: "一阶线性微分方程",
        stage: "稳定掌握",
        accuracy: "91%",
        evidence: "多时间点通过，进入间隔复习",
        tone: "green",
      },
    ] satisfies MasteryItem[],
    governanceRules: [
      {
        title: "用户确认必需",
        description: "AI 识别、复盘和计划调整在确认前只作为草稿显示。",
        status: "启用",
        tone: "green",
      },
      {
        title: "证据边界",
        description: "阅读、听课和拍照最多支持进入“已接触”，不能直接提升到掌握。",
        status: "强制",
        tone: "blue",
      },
      {
        title: "状态回退",
        description: "抽测失败或重复错因出现时，稳定掌握允许回退并生成补救任务。",
        status: "强制",
        tone: "red",
      },
    ] satisfies RuleItem[],
  }),
});
