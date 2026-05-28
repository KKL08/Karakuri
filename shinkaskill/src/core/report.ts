import { msg } from "./i18n.js";
import { compareBlind } from "../eval/comparator.js";
import type { Confidence } from "../eval/grader.js";
import type { EvalFeedback, ExpectationResult, GradingSummary, RubricScore } from "../eval/adapters/types.js";
import type { GateIssue, GateStatus, Locale, SkillTarget, StaticDimensionScore } from "./types.js";

const LARGE_IMPROVEMENT_DELTA = 20;

export type InspectReport = {
  target: SkillTarget;
  gate: {
    status: GateStatus;
    issues: GateIssue[];
  };
  staticScore: {
    total: number;
    profile: string;
    dimensions: StaticDimensionScore[];
  };
};

export type PromptDelta = {
  promptId: string;
  delta: number;
};

export type OverfittingRiskLevel = "low" | "medium" | "high";

export type OverfittingResult = {
  risk: OverfittingRiskLevel;
  evidence: string;
};

export type EvalMarkdownReportResult = {
  promptId: string;
  mode: "baseline" | "with_skill" | "candidate";
  status: "completed" | "failed" | "unavailable";
  output: string;
  evidence: string[];
  errors: string[];
  score?: number;
  passed?: boolean;
  winner?: "baseline" | "with_skill" | "candidate" | "tie" | "output_a" | "output_b" | "output_c";
  expectationResults?: ExpectationResult[];
  rubricScores?: RubricScore[];
  gradingSummary?: GradingSummary;
  evalFeedback?: EvalFeedback;
};

export type EvalMarkdownComparisonResult = {
  promptId: string;
  status: "completed" | "failed" | "unavailable";
  output: string;
  evidence: string[];
  errors: string[];
  winner?: "baseline" | "with_skill" | "candidate" | "tie" | "output_a" | "output_b" | "output_c";
};

export type EvalMarkdownReportPrompt = {
  id: string;
  prompt: string;
  expected: string;
};

export type EvalMarkdownReportInput = {
  locale: Locale;
  runId: string;
  targetName: string;
  status: "completed" | "failed" | "unavailable";
  confidence: Confidence;
  adapter: string;
  promptCount: number;
  planCount: number;
  maxConcurrentAgents?: number;
  prompts: EvalMarkdownReportPrompt[];
  results: EvalMarkdownReportResult[];
  graderResults?: EvalMarkdownReportResult[];
  comparisons?: EvalMarkdownComparisonResult[];
};

export function renderInspectMarkdown(reports: InspectReport[]): string {
  const lines: string[] = [`# ${msg("inspect.summaryTitle")}`, ""];

  for (const report of reports) {
    lines.push(`## ${report.target.name}`);
    lines.push("");
    lines.push(`- Gate：${report.gate.status}`);
    lines.push(`- Static Score：${report.staticScore.total}`);
    lines.push(`- Profile：${report.staticScore.profile}`);

    if (report.gate.issues.length > 0) {
      lines.push("");
      lines.push("### Gate 问题");
      for (const issue of report.gate.issues) {
        lines.push(`- [${issue.status}] ${issue.message}`);
      }
    }

    lines.push("");
    lines.push("### 静态评分维度");
    for (const dimension of report.staticScore.dimensions) {
      lines.push(`- ${dimension.label}：${dimension.score} / 100（权重 ${dimension.weight}）`);
    }
    lines.push("");
  }

  return `${lines.join("\n").trim()}\n`;
}

export function renderInspectJson(reports: InspectReport[]): string {
  return `${JSON.stringify({ locale: "zh-CN", reports }, null, 2)}\n`;
}

export function renderEvalMarkdownReport(input: EvalMarkdownReportInput): string {
  validateEvalMarkdownReportInput(input);
  const promptsById = new Map(input.prompts.map((prompt) => [prompt.id, prompt]));
  const comparisonsByPrompt = new Map((input.comparisons ?? []).map((comparison) => [comparison.promptId, comparison]));

  const lines: string[] = [
    "# ShinkaSkill Eval 报告",
    "",
    `判断：${evalJudgement(input)}`,
    "",
    "## 运行概况",
    "",
    `- 目标 skill：${input.targetName}`,
    `- Run：${input.runId}`,
    `- Adapter：${input.adapter}`,
    `- 状态：${input.status}`,
    `- Confidence：${input.confidence}`,
    `- Prompt 数：${input.promptCount}`,
    `- 任务数：${input.planCount}`,
    ...(typeof input.maxConcurrentAgents === "number" ? [`- Subagent 并发上限：${input.maxConcurrentAgents}`] : []),
    "",
    "## 结果对照",
  ];

  for (const [promptId, results] of groupResultsByPrompt(input.results)) {
    const prompt = promptsById.get(promptId);
    lines.push("", `### Prompt：${promptId}`);
    if (prompt) {
      lines.push("");
      lines.push(`测试请求：${brief(prompt.prompt, 180)}`);
      lines.push(`期望：${brief(prompt.expected, 180)}`);
    }
    lines.push(`差异判断：${promptPairJudgement({ prompt, results, comparison: comparisonsByPrompt.get(promptId) })}`);
    for (const result of sortResultsByMode(results)) {
      lines.push("", `- ${result.mode}：${result.status}`);
      if (result.output.trim()) {
        lines.push(`  输出：${brief(result.output)}`);
      }
      if (result.evidence.length > 0) {
        lines.push(`  证据：${result.evidence.map((item) => brief(item, 120)).join("；")}`);
      }
      if (result.errors.length > 0) {
        lines.push(`  错误：${result.errors.map((item) => brief(item, 120)).join("；")}`);
      }
    }
  }

  if ((input.graderResults?.length ?? 0) > 0 || (input.comparisons?.length ?? 0) > 0) {
    lines.push("", "## Grader / Comparator");
    if (input.graderResults && input.graderResults.length > 0) {
      lines.push("", "### Grader");
      for (const result of input.graderResults) {
        const score = typeof result.score === "number" ? `，score ${result.score}` : "";
        const passed = typeof result.passed === "boolean" ? `，passed ${result.passed}` : "";
        const summary = result.gradingSummary
          ? `，pass_rate ${formatRate(result.gradingSummary.passRate)}（${result.gradingSummary.passed}/${result.gradingSummary.total}）`
          : "";
        lines.push(`- ${result.promptId} / ${result.mode}：${result.status}${score}${passed}${summary}`);
        if (result.output.trim()) {
          lines.push(`  理由：${brief(result.output)}`);
        }
        if (result.expectationResults && result.expectationResults.length > 0) {
          lines.push("  期望逐条检查：");
          for (const item of result.expectationResults) {
            lines.push(`  - ${item.passed ? "PASS" : "FAIL"} ${brief(item.text, 120)}：${brief(item.evidence, 160)}`);
          }
        }
        if (result.rubricScores && result.rubricScores.length > 0) {
          lines.push("  Rubric 逐项打分：");
          for (const item of result.rubricScores) {
            const source = item.source ? `，来源：${item.source}` : "";
            lines.push(
              `  - ${item.label}（${item.key}）：${item.score}/${item.maxScore}，${item.passed ? "PASS" : "FAIL"}${source}；证据：${brief(item.evidence, 160)}`,
            );
          }
        }
        if (result.evalFeedback?.overall) {
          lines.push(`  Eval 反馈：${brief(result.evalFeedback.overall, 180)}`);
        }
      }
    }
    if (input.comparisons && input.comparisons.length > 0) {
      lines.push("", "### Comparator");
      for (const result of input.comparisons) {
        const winner = result.winner ? `，winner ${result.winner}` : "";
        lines.push(`- ${result.promptId}：${result.status}${winner}`);
        if (result.output.trim()) {
          lines.push(`  理由：${brief(result.output)}`);
        }
      }
    }
  }

  const recommendations = reportRecommendations(input);
  if (recommendations.length > 0) {
    lines.push("", "## 优化建议", "");
    for (const item of recommendations) {
      lines.push(`- ${item}`);
    }
  }

  const followUps = reportFollowUps(input);
  if (followUps.length > 0) {
    lines.push("", "## 需要关注", "");
    for (const item of followUps) {
      lines.push(`- ${item}`);
    }
  }

  return `${lines.join("\n").trim()}\n`;
}

export function overfittingRisk(deltas: PromptDelta[]): OverfittingResult {
  const normalized = validatePromptDeltas(deltas);
  const bigWins = normalized.filter((item) => item.delta >= LARGE_IMPROVEMENT_DELTA);
  const nonWins = normalized.filter((item) => item.delta <= 0);

  if (bigWins.length === 1 && nonWins.length >= 1) {
    return {
      risk: "medium",
      evidence: `candidate 只在 ${bigWins[0].promptId} 上大幅提升，另有 ${nonWins.length} 个 prompt 无提升或变差。`,
    };
  }

  if (nonWins.length >= 2) {
    return {
      risk: "high",
      evidence: `candidate 在 ${nonWins.length} 个 prompt 上无提升或变差，泛化风险较高。`,
    };
  }

  return {
    risk: "low",
    evidence: "candidate 的提升分布较均衡，没有明显集中在单一 prompt。",
  };
}

export function renderEvalJson(input: {
  locale: Locale;
  runId: string;
  confidence: Confidence;
  overfitting: OverfittingResult;
}): string {
  validateEvalJsonInput(input);

  return `${JSON.stringify(
    {
      locale: input.locale,
      run_id: input.runId,
      confidence: input.confidence,
      overfitting_risk: input.overfitting.risk,
      overfitting_evidence: input.overfitting.evidence,
    },
    null,
    2,
  )}\n`;
}

function evalJudgement(input: EvalMarkdownReportInput): string {
  if (input.status === "unavailable") {
    return "这次没有运行真实 eval。先处理 adapter 能力，再判断 skill 效果。";
  }

  if (input.status === "failed") {
    return "这次 eval 没有全部跑通。先看失败项，再讨论 skill 效果。";
  }

  const improvedPrompts = countWithSkillImprovements(input.results);
  if (improvedPrompts > 0) {
    return hasCompletedReview(input)
      ? `with_skill 的回答更贴近 skill 目标。当前有 ${improvedPrompts} 个 prompt 出现可见差异，grader 和 comparator 已完成复核。`
      : `with_skill 的回答更贴近 skill 目标。当前有 ${improvedPrompts} 个 prompt 出现可见差异，后续还需要 grader 和 comparator 复核。`;
  }

  return "这次 eval 跑通了，但 baseline 和 with_skill 的差异不明显。建议补更有区分度的 prompt。";
}

function hasCompletedReview(input: EvalMarkdownReportInput): boolean {
  return (
    (input.graderResults?.length ?? 0) > 0 &&
    (input.comparisons?.length ?? 0) > 0 &&
    input.graderResults?.every((result) => result.status === "completed") === true &&
    input.comparisons?.every((result) => result.status === "completed") === true
  );
}

function countWithSkillImprovements(results: EvalMarkdownReportResult[]): number {
  let count = 0;
  for (const [, group] of groupResultsByPrompt(results)) {
    const baseline = group.find((item) => item.mode === "baseline");
    const withSkill = group.find((item) => item.mode === "with_skill");
    if (!baseline || !withSkill) continue;
    if (baseline.status !== "completed" || withSkill.status !== "completed") continue;
    const outputChanged = normalizeText(baseline.output) !== normalizeText(withSkill.output);
    const usedSkill = withSkill.evidence.some((item) => /SKILL\.md|skill|读取/i.test(item));
    if (outputChanged && usedSkill) count += 1;
  }
  return count;
}

function reportFollowUps(input: EvalMarkdownReportInput): string[] {
  const items: string[] = [];
  if (input.confidence !== "high") {
    items.push("当前 confidence 还不是 high，原因是 grader 或 comparator 还没有完整接入。");
  }
  if (input.results.some((result) => result.status === "failed")) {
    items.push("先处理 failed 结果里的错误，再扩展 prompt suite。");
  }
  if (input.results.every((result) => result.status === "unavailable")) {
    items.push("这份报告只记录授权和沙箱状态，不能当作真实效果评测。");
  }
  return items;
}

function reportRecommendations(input: EvalMarkdownReportInput): string[] {
  const promptsById = new Map(input.prompts.map((prompt) => [prompt.id, prompt]));
  const comparisonsByPrompt = new Map((input.comparisons ?? []).map((comparison) => [comparison.promptId, comparison]));
  const items: string[] = [];

  for (const [promptId, results] of groupResultsByPrompt(input.results)) {
    const judgement = promptPairJudgement({ prompt: promptsById.get(promptId), results, comparison: comparisonsByPrompt.get(promptId) });
    if (judgement.includes("没有真实执行结果")) {
      items.push(`${promptId}：先接通真实 adapter，再评估 skill 内容。`);
    } else if (judgement.includes("至少一侧没有跑通")) {
      items.push(`${promptId}：先修复 eval 失败项，再判断 skill 内容。`);
    } else if (judgement.includes("输出一致")) {
      items.push(`${promptId}：补一个更能区分 skill 行为的 prompt，最好覆盖触发条件、边界和反例。`);
    } else if (judgement.includes("baseline 更贴近")) {
      items.push(`${promptId}：检查 skill 是否过早假设用户意图，必要时补一条追问边界。`);
    } else if (judgement.includes("with_skill 更贴近")) {
      items.push(`${promptId}：保留这个方向，把相关行为写进 skill 的工作流或边界说明。`);
    } else {
      items.push(`${promptId}：补充更明确的 expected，方便后续 grader 和 comparator 判断。`);
    }
  }

  return items;
}

function promptPairJudgement(input: {
  prompt?: EvalMarkdownReportPrompt;
  results: EvalMarkdownReportResult[];
  comparison?: EvalMarkdownComparisonResult;
}): string {
  const baseline = input.results.find((item) => item.mode === "baseline");
  const withSkill = input.results.find((item) => item.mode === "with_skill");

  if (!baseline || !withSkill) {
    return "缺少 baseline 或 with_skill，先补齐成对结果。";
  }

  if (baseline.status === "unavailable" && withSkill.status === "unavailable") {
    return "没有真实执行结果，当前只能确认 run 已创建。";
  }

  if (baseline.status !== "completed" || withSkill.status !== "completed") {
    return "至少一侧没有跑通，先处理错误，再判断 skill 效果。";
  }

  if (normalizeText(baseline.output) === normalizeText(withSkill.output)) {
    return "baseline 和 with_skill 输出一致，当前 prompt 区分度不够。";
  }

  if (input.comparison?.status === "completed") {
    if (input.comparison.winner === "with_skill") {
      return "comparator 复核后判定 with_skill 更贴近期望。";
    }
    if (input.comparison.winner === "baseline") {
      return "comparator 复核后判定 baseline 更贴近期望，需要检查 skill 是否过早假设用户意图。";
    }
    if (input.comparison.winner === "candidate") {
      return "comparator 复核后判定 candidate 更贴近期望。";
    }
    if (input.comparison.winner === "tie") {
      return "comparator 复核后未判出明显胜负，建议补更有区分度的 prompt。";
    }
  }

  const usedSkill = withSkill.evidence.some((item) => /SKILL\.md|skill|读取/i.test(item));
  if (input.prompt?.expected.trim()) {
    const comparison = compareBlind({
      outputA: baseline.output,
      outputB: withSkill.output,
      expected: input.prompt.expected,
    });
    if (comparison.winner === "output_b") {
      return usedSkill
        ? "with_skill 更贴近期望，并且证据显示它读取了 skill。"
        : "with_skill 更贴近期望，但证据还不足以说明差异来自 skill。";
    }
    if (comparison.winner === "output_a") {
      return "baseline 更贴近期望，需要检查 skill 是否把回答带偏。";
    }
  }

  return usedSkill
    ? "with_skill 读取了 skill，输出也发生变化。还需要更强的 expected 或 comparator 复核。"
    : "两侧输出不同，但证据还不足以说明差异来自 skill。";
}

function groupResultsByPrompt(results: EvalMarkdownReportResult[]): Map<string, EvalMarkdownReportResult[]> {
  const grouped = new Map<string, EvalMarkdownReportResult[]>();
  for (const result of results) {
    const promptId = result.promptId.trim() || "unknown";
    grouped.set(promptId, [...(grouped.get(promptId) ?? []), result]);
  }
  return grouped;
}

function sortResultsByMode(results: EvalMarkdownReportResult[]): EvalMarkdownReportResult[] {
  const order = new Map<EvalMarkdownReportResult["mode"], number>([
    ["baseline", 0],
    ["with_skill", 1],
    ["candidate", 2],
  ]);
  return [...results].sort((a, b) => (order.get(a.mode) ?? 99) - (order.get(b.mode) ?? 99));
}

function brief(value: string, limit = 260): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 1)}…`;
}

function formatRate(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function validatePromptDeltas(deltas: PromptDelta[]): PromptDelta[] {
  if (deltas.length === 0) {
    throw new Error("无法判断过拟合风险：prompt delta 不能为空。");
  }

  const seenPromptIds = new Set<string>();
  return deltas.map((item) => {
    const promptId = item.promptId.trim();

    if (promptId.length === 0) {
      throw new Error("无法判断过拟合风险：promptId 不能为空。");
    }

    if (seenPromptIds.has(promptId)) {
      throw new Error(`无法判断过拟合风险：promptId "${promptId}" 重复。`);
    }
    seenPromptIds.add(promptId);

    if (!Number.isFinite(item.delta)) {
      throw new Error(`无法判断过拟合风险：${promptId} 的 delta 必须是有限数字。`);
    }

    return { promptId, delta: item.delta };
  });
}

function validateEvalJsonInput(input: {
  locale: Locale;
  runId: string;
  confidence: Confidence;
  overfitting: OverfittingResult;
}): void {
  if (input.locale !== "zh-CN" && input.locale !== "en-US") {
    throw new Error(`不支持的 locale：${input.locale}`);
  }

  if (input.runId.trim().length === 0) {
    throw new Error("runId 不能为空。");
  }
}

function validateEvalMarkdownReportInput(input: EvalMarkdownReportInput): void {
  validateEvalJsonInput({
    locale: input.locale,
    runId: input.runId,
    confidence: input.confidence,
    overfitting: { risk: "low", evidence: "报告渲染输入检查。" },
  });

  if (input.targetName.trim().length === 0) {
    throw new Error("targetName 不能为空。");
  }

  if (input.adapter.trim().length === 0) {
    throw new Error("adapter 不能为空。");
  }
}
