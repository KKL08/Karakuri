import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";

export type EvalPrompt = {
  id: string;
  prompt: string;
  expected: string;
};

export type PromptCheck = {
  status: "pass" | "warn" | "fail";
  messages: string[];
};

const EvalPromptSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  expected: z.string(),
});

export async function loadPromptSuite(skillRoot: string): Promise<EvalPrompt[]> {
  const promptDir = join(skillRoot, "shinka", "prompts");
  const files = (await safeReaddir(promptDir)).filter((file) => file.endsWith(".json")).sort();
  const prompts: EvalPrompt[] = [];

  for (const file of files) {
    const parsed = parsePromptJson(file, await readPromptFile(file, join(promptDir, file)));
    const result = EvalPromptSchema.safeParse(parsed);
    if (!result.success) throw new Error(formatPromptSchemaError(file, result.error));
    prompts.push(result.data);
  }

  return prompts;
}

export function generatePromptSuite(input: { skillName: string; description?: string; skillBody?: string }): EvalPrompt[] {
  const skillText = `${input.skillName}\n${input.description ?? ""}\n${input.skillBody ?? ""}`;
  if (looksLikeChineseDeslopSkill(skillText)) {
    return [
      {
        id: "happy-path",
        prompt: [
          `请用 ${input.skillName} 改写下面这段中文，让它更自然。`,
          "",
          "原文：通过本次能力升级，我们进一步优化用户反馈处理链路，完善标准化处理流程，从而显著提升整体协同效率。",
        ].join("\n"),
        expected: "输出应保留事实和动作关系，去掉 AI 腔、黑话和总结腔，改成自然中文；不要新增原文没有的信息。",
      },
      {
        id: "missing-source",
        prompt: `用户只说“帮我润色自然一点”，但原文缺失。请判断 ${input.skillName} 应该追问还是继续。`,
        expected: "如果缺少待改写原文，应追问用户补充原文；不要自行编造一段改写结果。",
      },
    ];
  }

  return [
    {
      id: "happy-path",
      prompt: `请用 ${input.skillName} 处理一个最常见的用户请求。`,
      expected: input.description ? `输出应体现 skill 描述中的能力：${input.description}` : "输出应完成 skill 声明的核心任务。",
    },
    {
      id: "ambiguous-task",
      prompt: `用户给了一个不完整请求，请判断 ${input.skillName} 是否应该追问或继续。`,
      expected: "如果关键信息缺失，应说明缺口并提出一个明确问题。",
    },
  ];
}

function looksLikeChineseDeslopSkill(skillText: string): boolean {
  return /去\s*AI|AI\s*腔|AI\s*味|改写|润色|中文写作|自然一点|像人写/u.test(skillText);
}

export function metaCheckPrompt(prompt: EvalPrompt): PromptCheck {
  const messages: string[] = [];
  let status: PromptCheck["status"] = "pass";
  const promptText = prompt.prompt.trim();
  const expectedText = prompt.expected.trim();

  const addIssue = (severity: PromptCheck["status"], message: string): void => {
    messages.push(message);
    if (severity === "fail" || (severity === "warn" && status === "pass")) status = severity;
  };

  if (promptText.length < 12) addIssue("warn", "prompt 太短，不像真实用户请求。");
  if (!expectedText) addIssue("fail", "缺少 expected 行为描述。");
  if (looksLikeFixedAnswer(promptText, expectedText)) addIssue("warn", "prompt 像固定答案测试，容易过拟合。");
  if (looksOverlyNarrow(promptText)) addIssue("warn", "prompt 覆盖面过窄。");
  if (looksOverlyBroadOrUnjudgeable(promptText, expectedText)) addIssue("warn", "prompt 过宽或不可判定。");
  if (looksLikeCandidateLeak(promptText)) {
    addIssue("warn", "prompt 可能泄露 candidate patch 方向。");
  }

  return { status, messages };
}

async function safeReaddir(path: string): Promise<string[]> {
  try {
    return await readdir(path);
  } catch {
    return [];
  }
}

function parsePromptJson(file: string, raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    throw new Error(`${file}：JSON 格式无效。`);
  }
}

async function readPromptFile(file: string, path: string): Promise<string> {
  try {
    return await readFile(path, "utf8");
  } catch {
    throw new Error(`${file}：读取失败。`);
  }
}

function formatPromptSchemaError(file: string, error: z.ZodError<EvalPrompt>): string {
  const issue = error.issues[0];
  if (!issue || issue.path.length === 0) return `${file}：顶层必须是对象。`;
  const field = String(issue.path[0]);
  return `${file}：${field} 必须是字符串。`;
}

function looksLikeFixedAnswer(promptText: string, expectedText: string): boolean {
  const combined = `${promptText}\n${expectedText}`;
  if (/固定答案|硬编码答案|固定文本|字面答案/.test(combined)) return true;

  const promptLiterals = literalAnswerCandidates(promptText);
  const expectedLiterals = new Set(literalAnswerCandidates(expectedText));
  return promptLiterals.some((literal) => expectedLiterals.has(literal));
}

function looksOverlyNarrow(promptText: string): boolean {
  const hasNarrowQualifier = /只|仅|单一|特定/.test(promptText);
  if (!hasNarrowQualifier) return false;

  const hasQuotedInput = /(用户输入|输入|请求).{0,4}[「"“'`](.{1,40})[」"”'`]/u.test(promptText);
  const hasShortLiteralInput =
    /(用户输入|输入|请求)(?!一段|一份|多个|任意|下面|这段)([\p{Script=Han}A-Za-z0-9_-]{1,8})(时|为|是|回复)/u.test(
      promptText,
    );

  return hasQuotedInput || hasShortLiteralInput;
}

function looksOverlyBroadOrUnjudgeable(promptText: string, expectedText: string): boolean {
  return (
    /帮我看看|评价一下|好不好|整体如何|随便|任意/.test(promptText) ||
    /看情况|视情况|自行判断|合理即可|尽量好|根据需要/.test(expectedText)
  );
}

function looksLikeCandidateLeak(promptText: string): boolean {
  return /candidate|候选方案|候选补丁/i.test(promptText) || /修改后的\s*(skill|candidate|候选)/i.test(promptText);
}

function literalAnswerCandidates(text: string): string[] {
  const quoted = Array.from(text.matchAll(/[「"“'`]([^「」"“”'`]{1,40})[」"”'`]/g), (match) => match[1].trim());
  const hardcodedTokens = Array.from(
    text.matchAll(/\b(?=[A-Za-z0-9_-]{4,}\b)(?=[A-Za-z0-9_-]*[A-Za-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+\b/g),
    (match) => match[0],
  );
  return [...quoted, ...hardcodedTokens].filter((literal) => literal.length > 0);
}
