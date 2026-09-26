export type StudyPromptTemplate = {
  id: string;
  version: string;
  title: string;
  summary: string;
  materialHint: string;
  attemptHint: string;
  focusHint: string;
  outputRequirements: string[];
};

export const studyPromptTemplates: StudyPromptTemplate[] = [
  {
    id: "problem-explanation",
    version: "study-prompt-v1.0.0",
    title: "题目讲解",
    summary: "检查前置知识并分步讲解题目，不直接跳到答案。",
    materialHint: "粘贴完整题目、公式或图片中可辨认的文字",
    attemptHint: "写下你已经尝试的步骤、卡住的位置或已有答案",
    focusHint: "例如：先判断缺少哪些前置知识，再提示第一步",
    outputRequirements: [
      "先检查题目信息是否完整，并列出缺失或歧义。",
      "列出解题所需的前置知识，再给出分步提示。",
      "把关键推理和最终答案分开，最后给一道同类自测题。",
    ],
  },
  {
    id: "wrong-answer-diagnosis",
    version: "study-prompt-v1.0.0",
    title: "错因诊断",
    summary: "比较题目、作答和答案，定位表层错误与深层知识缺口。",
    materialHint: "粘贴题目、标准答案或解析；没有的部分明确写“未提供”",
    attemptHint: "粘贴你的完整作答过程，并标出你认为可能出错的位置",
    focusHint: "例如：判断是审题、概念、计算还是方法选择问题",
    outputRequirements: [
      "分别给出表层错因、深层错因和可能的前置知识缺口。",
      "引用作答中的具体步骤作为诊断依据，不要只给通用评价。",
      "给出无提示重做要求、两道变式方向和间隔复测建议。",
    ],
  },
  {
    id: "material-to-recall",
    version: "study-prompt-v1.0.0",
    title: "资料整理",
    summary: "把讲义或笔记整理成知识结构和闭卷回忆题。",
    materialHint: "粘贴讲义、课堂笔记、教材段落或识别后的文字",
    attemptHint: "写下你已经理解和仍然模糊的部分；没有可留空",
    focusHint: "例如：优先整理高频考点、易混概念和公式使用条件",
    outputRequirements: [
      "按概念、条件、公式、典型用途和易错点整理，不遗漏适用边界。",
      "把原文明确事实与模型补充说明分开标记。",
      "生成由浅入深的闭卷回忆题，并把答案单独放在最后。",
    ],
  },
  {
    id: "daily-review",
    version: "study-prompt-v1.0.0",
    title: "每日复盘",
    summary: "根据当天事实复盘偏差，并形成需要用户确认的次日建议。",
    materialHint: "粘贴今日任务、实际用时、完成结果和未完成原因",
    attemptHint: "写下你的主观状态、精力变化和最需要解决的问题",
    focusHint: "例如：明天只有 3 小时，只保留数学一任务",
    outputRequirements: [
      "先列已确认事实，再给教学判断和当前风险。",
      "解释计划偏差的原因，不把完成任务等同于掌握。",
      "给出次日任务、预计用时和验收标准，并保留机动时间。",
      "所有计划调整都标记为建议，等待用户确认。",
    ],
  },
];

export const promptDestinations = [
  { id: "deepseek", label: "DeepSeek", url: "https://chat.deepseek.com/" },
  { id: "qwen", label: "通义千问", url: "https://qwen.ai/qwenchat" },
  { id: "kimi", label: "Kimi", url: "https://www.kimi.ai/" },
] as const;

