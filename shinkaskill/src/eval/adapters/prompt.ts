import type { ComparatorTaskSpec, EvalTaskSpec, GraderTaskSpec } from "./types.js";

const GRADER_RUBRICS = [
  {
    key: "expected_coverage",
    label: "期望覆盖",
    source: "agent-skills-evals",
    description: "是否满足 expected 中可观察的成功标准，并对每条期望给出证据。",
  },
  {
    key: "evidence_quality",
    label: "证据质量",
    source: "anthropic-skill-creator-grader",
    description: "评分是否基于输出中的具体文本、文件或执行证据，而不是主观猜测。",
  },
  {
    key: "instruction_following",
    label: "指令遵循",
    source: "anthropic-skill-creator-grader",
    description: "是否遵循测试请求、运行模式和安全边界，没有做无关或越界动作。",
  },
  {
    key: "skill_grounding",
    label: "Skill grounding",
    source: "anthropic-claude-skills",
    description: "with_skill/candidate 是否体现读取并使用 SKILL.md；baseline 是否避免使用 skill。",
  },
  {
    key: "output_usability",
    label: "输出可用性",
    source: "anthropic-skill-creator-comparator",
    description: "输出是否结构清楚、可执行、对用户有用。",
  },
  {
    key: "progressive_disclosure_fit",
    label: "渐进披露适配",
    source: "agent-skills-open-standard",
    description: "输出是否只使用必要上下文，没有暴露无关长说明或把 skill 内部细节强塞给用户。",
  },
] as const;

export function buildEvalAgentPrompt(task: EvalTaskSpec): string {
  const modeInstruction = modeInstructionFor(task.mode);
  return `你是 ShinkaSkill 的隔离 eval agent。请只做评估运行，不修改任何文件，不运行写入命令，不访问网络。

运行信息：
- runId: ${task.runId}
- promptId: ${task.promptId}
- mode: ${task.mode}
- sandboxDir: ${task.sandboxDir}

${modeInstruction}

用户测试请求：
${task.prompt}

期望行为：
${task.expected}

请输出 JSON，且不要输出 JSON 以外的解释：
{
  "status": "completed",
  "output": "你对用户测试请求的实际回答",
  "evidence": ["简短说明你如何使用或未使用 skill"],
  "errors": []
}`;
}

export function buildGraderAgentPrompt(task: GraderTaskSpec): string {
  return `你是 ShinkaSkill 的隔离 grader agent。只评估给定输出，不修改任何文件，不运行写入命令，不访问网络。

你要做逐项 rubric 打分。标准综合来自：
- Anthropic Claude Code Skills：description 决定触发，SKILL.md body 在触发后加载，复杂 skill 可用 supporting files 和 subagent 隔离执行。
- Anthropic skill-creator：grader 要逐条验证 expectation，PASS 必须有具体证据；comparator 用内容和结构 rubric 做 1-5 分盲审。
- Agent Skills / OpenAI Codex 兼容标准：skill 是包含 SKILL.md 的目录，agent 先读 name/description，触发后再读取正文，eval 应比较 with_skill 和 baseline。

运行信息：
- runId: ${task.runId}
- promptId: ${task.promptId}
- mode: ${task.mode}
- sandboxDir: ${task.sandboxDir}

用户测试请求：
${task.prompt}

期望行为：
${task.expected}

待评分输出：
${task.output}

逐项 rubric（每项 0-5 分，4 分及以上算 passed）：
${GRADER_RUBRICS.map((rubric) => `- ${rubric.key} / ${rubric.label} / ${rubric.source}：${rubric.description}`).join("\n")}

评分规则：
- 先把“期望行为”拆成至少 1 条 expectation，并逐条给出 passed 和 evidence。
- PASS 的证据必须具体引用待评分输出或 evidence；缺证据时判 FAIL。
- 不给模糊好评，不给半分通过；如果只能部分满足，rubric 可以给 2-3 分，但 passed 应为 false。
- with_skill/candidate 的 skill_grounding 要看是否有读取或使用 skill 的证据；baseline 则看是否避免使用 skill。

请输出 JSON，且不要输出 JSON 以外的解释：
{
  "status": "completed",
  "score": 0.0,
  "passed": false,
  "output": "简短说明评分理由",
  "expectationResults": [
    {
      "text": "一条从期望行为中拆出的可验证 expectation",
      "passed": false,
      "evidence": "引用或描述支持判断的具体证据"
    }
  ],
  "rubricScores": [
    {
      "key": "expected_coverage",
      "label": "期望覆盖",
      "score": 0,
      "maxScore": 5,
      "passed": false,
      "evidence": "具体证据",
      "source": "agent-skills-evals"
    }
  ],
  "gradingSummary": {
    "passed": 0,
    "failed": 1,
    "total": 1,
    "passRate": 0.0
  },
  "evidence": ["引用输出中支持评分的证据"],
  "errors": []
}`;
}

export function buildComparatorAgentPrompt(task: ComparatorTaskSpec): string {
  const candidateBlock = task.candidateOutput
    ? `
output_c：
${task.candidateOutput}
`
    : "";
  return `你是 ShinkaSkill 的隔离 comparator agent。请盲审多份输出，只比较哪份更符合期望，不修改任何文件，不运行写入命令，不访问网络。

运行信息：
- runId: ${task.runId}
- promptId: ${task.promptId}
- sandboxDir: ${task.sandboxDir}

用户测试请求：
${task.prompt}

期望行为：
${task.expected}

output_a：
${task.baselineOutput}

output_b：
${task.withSkillOutput}
${candidateBlock}
请输出 JSON，且不要输出 JSON 以外的解释：
{
  "status": "completed",
  "winner": "output_b",
  "output": "简短说明选择理由",
  "evidence": ["引用输出中支持判断的证据"],
  "errors": []
}`;
}

function modeInstructionFor(mode: EvalTaskSpec["mode"]): string {
  if (mode === "baseline") {
    return "baseline 模式：不要读取或使用 SKILL.md，把自己当作没有安装该 skill 的普通 agent。";
  }

  if (mode === "with_skill") {
    return "with_skill 模式：请读取 sandboxDir 中的 SKILL.md，并按该 skill 的指令处理用户测试请求。";
  }

  return "candidate 模式：请读取 sandboxDir 中的候选 skill 文件，并按候选版本处理用户测试请求。";
}
