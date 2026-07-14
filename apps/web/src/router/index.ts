import { createRouter, createWebHistory, type RouterHistory, type RouteRecordRaw } from "vue-router";

import LearningPage from "../pages/LearningPage.vue";
import PlanningPage from "../pages/PlanningPage.vue";
import ProgressPage from "../pages/ProgressPage.vue";
import SettingsPage from "../pages/SettingsPage.vue";
import TodayPage from "../pages/TodayPage.vue";

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/today",
  },
  {
    path: "/today",
    name: "today",
    component: TodayPage,
    meta: { title: "今日" },
  },
  {
    path: "/planning",
    name: "planning",
    component: PlanningPage,
    meta: { title: "规划" },
  },
  {
    path: "/learning",
    name: "learning",
    component: LearningPage,
    meta: { title: "学习" },
  },
  {
    path: "/progress",
    name: "progress",
    component: ProgressPage,
    meta: { title: "进度" },
  },
  {
    path: "/settings",
    name: "settings",
    component: SettingsPage,
    meta: { title: "设置" },
  },
];

export function createAppRouter(history: RouterHistory = createWebHistory(import.meta.env.BASE_URL)) {
  return createRouter({
    history,
    routes,
    scrollBehavior() {
      return { top: 0 };
    },
  });
}

export const router = createAppRouter();
