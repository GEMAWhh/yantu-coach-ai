export type PrimaryRouteName = "today" | "planning" | "learning" | "progress" | "settings";

export type PrimaryNavItem = {
  name: PrimaryRouteName;
  path: string;
  label: string;
  icon: string;
  description: string;
};

export const primaryNavItems: PrimaryNavItem[] = [
  {
    name: "today",
    path: "/today",
    label: "今日",
    icon: "今",
    description: "今日计划、执行记录、学习证据、AI 复盘",
  },
  {
    name: "planning",
    path: "/planning",
    label: "规划",
    icon: "规",
    description: "学期、季度、月、周、日目标及风险",
  },
  {
    name: "learning",
    path: "/learning",
    label: "学习",
    icon: "学",
    description: "资料、题库、错题、复习卡片和知识图谱",
  },
  {
    name: "progress",
    path: "/progress",
    label: "进度",
    icon: "进",
    description: "计划偏差、掌握阶段、正确率、错因和风险",
  },
  {
    name: "settings",
    path: "/settings",
    label: "设置",
    icon: "设",
    description: "考试信息、学习画像、规则、AI 配置和数据管理",
  },
];
