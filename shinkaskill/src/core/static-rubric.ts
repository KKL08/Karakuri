import type { StaticDimensionScore } from "./types.js";
import type { StaticProfile } from "./profiles.js";

type StaticInput = {
  name?: string;
  description?: string;
  body: string;
  missingReferences: string[];
  profile: StaticProfile;
};

export type StaticScoreResult = {
  total: number;
  profile: StaticProfile;
  dimensions: StaticDimensionScore[];
};

export function scoreStaticSkill(input: StaticInput): StaticScoreResult {
  const dimensions: StaticDimensionScore[] = [
    dimension("metadata", "元数据", input.profile.weights.metadata, scoreMetadata(input)),
    dimension(
      "progressiveDisclosure",
      "渐进加载",
      input.profile.weights.progressiveDisclosure,
      scoreProgressiveDisclosure(input.body),
    ),
    dimension("workflowClarity", "工作流清晰度", input.profile.weights.workflowClarity, scoreWorkflow(input.body)),
    dimension(
      "instructionSpecificity",
      "指令具体性",
      input.profile.weights.instructionSpecificity,
      scoreSpecificity(input.body),
    ),
    dimension("boundaryHandling", "边界处理", input.profile.weights.boundaryHandling, scoreBoundary(input.body)),
    dimension("resourceIntegrity", "资源完整性", input.profile.weights.resourceIntegrity, scoreResources(input.missingReferences)),
    dimension(
      "runtimeNeutrality",
      "Runtime 中立性",
      input.profile.weights.runtimeNeutrality,
      scoreRuntimeNeutrality(input.body),
    ),
    dimension("maintainability", "可维护性", input.profile.weights.maintainability, scoreMaintainability(input.body)),
  ];

  const total = dimensions.reduce((sum, item) => sum + (item.score * item.weight) / 100, 0);
  return { total: Math.round(total * 10) / 10, profile: input.profile, dimensions };
}

function dimension(
  key: StaticDimensionScore["key"],
  label: string,
  weight: number,
  value: { score: number; reasons: string[] },
): StaticDimensionScore {
  return { key, label, weight, score: value.score, reasons: value.reasons };
}

function scoreMetadata(input: StaticInput): { score: number; reasons: string[] } {
  const reasons: string[] = [];
  let score = 100;
  if (!input.name) {
    score -= 40;
    reasons.push("缺少 name。");
  }
  if (!input.description) {
    score -= 40;
    reasons.push("缺少 description。");
  } else if (input.description.length > 1024) {
    score -= 20;
    reasons.push("description 超过 1024 字符。");
  }
  return { score: clamp(score), reasons };
}

function scoreProgressiveDisclosure(body: string): { score: number; reasons: string[] } {
  const lines = body.split("\n").length;
  if (lines > 500) return { score: 60, reasons: ["SKILL.md 超过 500 行，入口文件偏重。"] };
  if (/references\//.test(body)) return { score: 95, reasons: ["入口文件使用 references 做渐进加载。"] };
  return { score: 82, reasons: ["未发现 references 渐进加载结构。"] };
}

function scoreWorkflow(body: string): { score: number; reasons: string[] } {
  const hasSteps = /(^|\n)\s*(\d+\.|-\s+\*\*Step|###\s+Phase)/i.test(body);
  return hasSteps ? { score: 92, reasons: ["包含明确步骤或阶段。"] } : { score: 68, reasons: ["缺少明确步骤或阶段。"] };
}

function scoreSpecificity(body: string): { score: number; reasons: string[] } {
  const hasCode = /```/.test(body);
  const hasFormat = /format|schema|json|输出|格式/i.test(body);
  return hasCode || hasFormat ? { score: 90, reasons: ["包含格式、schema 或代码示例。"] } : { score: 70, reasons: ["缺少具体格式或示例。"] };
}

function scoreBoundary(body: string): { score: number; reasons: string[] } {
  const hasBoundary = /失败|错误|fallback|确认|授权|如果|when.*fail/i.test(body);
  return hasBoundary ? { score: 90, reasons: ["覆盖失败、确认或 fallback。"] } : { score: 58, reasons: ["缺少失败、权限或 fallback 说明。"] };
}

function scoreResources(missingReferences: string[]): { score: number; reasons: string[] } {
  return missingReferences.length === 0
    ? { score: 100, reasons: ["引用资源完整。"] }
    : { score: 50, reasons: [`存在 ${missingReferences.length} 个断裂引用。`] };
}

function scoreRuntimeNeutrality(body: string): { score: number; reasons: string[] } {
  const redFlags = [/Claude Code 用户/, /Codex 中使用/, /~\/\.claude\/skills/, /~\/\.codex\/skills/].filter((pattern) =>
    pattern.test(body),
  );
  return redFlags.length === 0
    ? { score: 95, reasons: ["未发现明显单 runtime 绑定。"] }
    : { score: 55, reasons: [`发现 ${redFlags.length} 个 runtime 绑定信号。`] };
}

function scoreMaintainability(body: string): { score: number; reasons: string[] } {
  if (body.length > 40_000) return { score: 60, reasons: ["正文过长，维护成本高。"] };
  return { score: 88, reasons: ["正文长度可维护。"] };
}

function clamp(score: number): number {
  return Math.max(0, Math.min(100, score));
}
