import { execFile, spawn } from "node:child_process";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import type { EvalFeedback, EvalTaskResult, ExpectationResult, GradingSummary, RubricScore } from "./types.js";

const execFileAsync = promisify(execFile);

export type ProcessAgentJson = {
  status?: "completed" | "failed";
  output?: string;
  evidence?: string[];
  errors?: string[];
  score?: number;
  passed?: boolean;
  winner?: "baseline" | "with_skill" | "candidate" | "tie" | "output_a" | "output_b" | "output_c";
  expectationResults?: unknown;
  expectation_results?: unknown;
  expectations?: unknown;
  rubricScores?: unknown;
  rubric_scores?: unknown;
  gradingSummary?: unknown;
  grading_summary?: unknown;
  summary?: unknown;
  evalFeedback?: unknown;
  eval_feedback?: unknown;
};

export type AgentProcessOptions = {
  command: string;
  prefixArgs?: string[];
  timeoutMs?: number;
};

export async function commandCanRun(input: {
  command: string;
  prefixArgs?: string[];
  versionArgs?: string[];
  timeoutMs?: number;
}): Promise<boolean> {
  try {
    await execFileAsync(input.command, [...(input.prefixArgs ?? []), ...(input.versionArgs ?? ["--version"])], {
      timeout: input.timeoutMs ?? 10_000,
    });
    return true;
  } catch {
    return false;
  }
}

export async function runCodexProcess(input: {
  options: AgentProcessOptions;
  sandboxDir: string;
  prompt: string;
  role?: "preflight" | "eval" | "grader" | "comparator";
}): Promise<EvalTaskResult> {
  const outputDir = await mkdtemp(join(tmpdir(), "shinka-codex-eval-"));
  const outputPath = join(outputDir, "last-message.txt");
  const args = [
    ...(input.options.prefixArgs ?? []),
    "exec",
    "--sandbox",
    "read-only",
    "--ephemeral",
    "--skip-git-repo-check",
    "--cd",
    input.sandboxDir,
    "--output-last-message",
    outputPath,
    "-",
  ];

  try {
    const { stdout, stderr } = await spawnWithInput({
      command: input.options.command,
      args,
      stdin: input.prompt,
      cwd: input.sandboxDir,
      timeout: input.options.timeoutMs ?? 120_000,
      role: input.role,
    });
    const raw = await readOptionalFile(outputPath) ?? stdout;
    return parseAgentResult(raw, stderr);
  } catch (error) {
    return failedProcessResult(error);
  }
}

export async function runClaudeProcess(input: {
  options: AgentProcessOptions;
  sandboxDir: string;
  prompt: string;
  role?: "preflight" | "eval" | "grader" | "comparator";
  agent?: {
    name: string;
    description: string;
    prompt: string;
  };
}): Promise<EvalTaskResult> {
  const agent = input.agent ?? {
    name: "shinka-evaluator",
    description: "Runs isolated ShinkaSkill eval tasks and returns JSON.",
    prompt: "You are an isolated evaluator. Follow the user prompt exactly, do not edit files, and return JSON only.",
  };
  const args = [
    ...(input.options.prefixArgs ?? []),
    "-p",
    "--output-format",
    "json",
    "--permission-mode",
    "dontAsk",
    "--tools",
    "",
    "--agents",
    JSON.stringify({
      [agent.name]: {
        description: agent.description,
        prompt: agent.prompt,
      },
    }),
    "--agent",
    agent.name,
    "--add-dir",
    input.sandboxDir,
  ];

  try {
    const { stdout, stderr } = await spawnWithInput({
      command: input.options.command,
      args,
      stdin: input.prompt,
      cwd: input.sandboxDir,
      timeout: input.options.timeoutMs ?? 120_000,
      role: input.role,
    });
    return parseAgentResult(stdout, stderr);
  } catch (error) {
    return failedProcessResult(error);
  }
}

export function parseAgentResult(raw: string, stderr = ""): EvalTaskResult {
  const text = raw.trim();
  if (text.length === 0) {
    return {
      status: "failed",
      output: "",
      evidence: ["agent 进程未返回可评估输出。"],
      errors: [stderr.trim() || "agent 输出为空。"],
    };
  }

  const parsed = tryParseAgentJson(text);
  if (!parsed) {
    return {
      status: "completed",
      output: text,
      evidence: ["agent 进程已返回纯文本输出。"],
      errors: [],
    };
  }

  return resultFromParsedAgentJson(parsed, stderr);
}

function resultFromParsedAgentJson(
  parsed: ProcessAgentJson & Record<string, unknown>,
  stderr = "",
  processFailed = false,
): EvalTaskResult {
  if (!processFailed && parsed.is_error !== true && typeof parsed.result === "string") {
    const nested = tryParseAgentJson(parsed.result.trim());
    if (nested) {
      return resultFromParsedAgentJson(nested, stderr);
    }
  }

  const failed = parsed.status === "failed" || parsed.is_error === true || processFailed;
  const hasExplicitOutput = typeof parsed.output === "string";
  const extractedOutput = hasExplicitOutput ? parsed.output as string : extractClaudeResult(parsed);
  const parsedErrors = Array.isArray(parsed.errors)
    ? parsed.errors.filter((item): item is string => typeof item === "string")
    : [];
  const errors = [...parsedErrors];
  if (failed && !hasExplicitOutput && extractedOutput.trim()) {
    errors.push(extractedOutput);
  }
  if (failed && stderr.trim()) {
    errors.push(stderr.trim());
  }

  return {
    status: failed ? "failed" : "completed",
    output: failed && !hasExplicitOutput ? "" : extractedOutput,
    evidence: Array.isArray(parsed.evidence) ? parsed.evidence.filter((item): item is string => typeof item === "string") : [],
    errors: errors.length > 0 ? errors : failed ? ["agent 进程返回失败状态。"] : [],
    score: typeof parsed.score === "number" && Number.isFinite(parsed.score) ? parsed.score : undefined,
    passed: typeof parsed.passed === "boolean" ? parsed.passed : undefined,
    winner: isAgentWinner(parsed.winner) ? parsed.winner : undefined,
    expectationResults: parseExpectationResults(parsed),
    rubricScores: parseRubricScores(parsed),
    gradingSummary: parseGradingSummary(parsed),
    evalFeedback: parseEvalFeedback(parsed),
  };
}

function isAgentWinner(value: unknown): value is NonNullable<EvalTaskResult["winner"]> {
  return (
    value === "baseline" ||
    value === "with_skill" ||
    value === "candidate" ||
    value === "tie" ||
    value === "output_a" ||
    value === "output_b" ||
    value === "output_c"
  );
}

function tryParseAgentJson(text: string): (ProcessAgentJson & Record<string, unknown>) | undefined {
  try {
    const value = JSON.parse(text) as unknown;
    return value && typeof value === "object" && !Array.isArray(value) ? (value as ProcessAgentJson & Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}

function parseExpectationResults(parsed: ProcessAgentJson & Record<string, unknown>): ExpectationResult[] | undefined {
  const raw = parsed.expectationResults ?? parsed.expectation_results ?? parsed.expectations;
  if (!Array.isArray(raw)) return undefined;

  const results = raw.flatMap((item): ExpectationResult[] => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    if (typeof record.text !== "string" || typeof record.passed !== "boolean" || typeof record.evidence !== "string") {
      return [];
    }
    return [
      {
        text: record.text,
        passed: record.passed,
        evidence: record.evidence,
      },
    ];
  });

  return results.length > 0 ? results : undefined;
}

function parseRubricScores(parsed: ProcessAgentJson & Record<string, unknown>): RubricScore[] | undefined {
  const raw = parsed.rubricScores ?? parsed.rubric_scores;
  if (!Array.isArray(raw)) return undefined;

  const scores = raw.flatMap((item): RubricScore[] => {
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    if (
      typeof record.key !== "string" ||
      typeof record.label !== "string" ||
      typeof record.score !== "number" ||
      !Number.isFinite(record.score) ||
      typeof record.passed !== "boolean" ||
      typeof record.evidence !== "string"
    ) {
      return [];
    }

    return [
      {
        key: record.key,
        label: record.label,
        score: record.score,
        maxScore: typeof record.maxScore === "number" && Number.isFinite(record.maxScore)
          ? record.maxScore
          : typeof record.max_score === "number" && Number.isFinite(record.max_score)
            ? record.max_score
            : 5,
        passed: record.passed,
        evidence: record.evidence,
        source: typeof record.source === "string" ? record.source : undefined,
      },
    ];
  });

  return scores.length > 0 ? scores : undefined;
}

function parseGradingSummary(parsed: ProcessAgentJson & Record<string, unknown>): GradingSummary | undefined {
  const raw = parsed.gradingSummary ?? parsed.grading_summary ?? parsed.summary;
  if (!raw || typeof raw !== "object") return undefined;
  const record = raw as Record<string, unknown>;
  const passRate = typeof record.passRate === "number" && Number.isFinite(record.passRate)
    ? record.passRate
    : typeof record.pass_rate === "number" && Number.isFinite(record.pass_rate)
      ? record.pass_rate
      : undefined;

  if (
    typeof record.passed !== "number" ||
    !Number.isFinite(record.passed) ||
    typeof record.failed !== "number" ||
    !Number.isFinite(record.failed) ||
    typeof record.total !== "number" ||
    !Number.isFinite(record.total) ||
    typeof passRate !== "number"
  ) {
    return undefined;
  }

  return {
    passed: record.passed,
    failed: record.failed,
    total: record.total,
    passRate,
  };
}

function parseEvalFeedback(parsed: ProcessAgentJson & Record<string, unknown>): EvalFeedback | undefined {
  const raw = parsed.evalFeedback ?? parsed.eval_feedback;
  if (!raw || typeof raw !== "object") return undefined;
  const record = raw as Record<string, unknown>;
  if (typeof record.overall !== "string" || !Array.isArray(record.suggestions)) return undefined;
  const suggestions = record.suggestions.flatMap((item): EvalFeedback["suggestions"] => {
    if (!item || typeof item !== "object") return [];
    const suggestion = item as Record<string, unknown>;
    if (typeof suggestion.reason !== "string") return [];
    return [
      {
        reason: suggestion.reason,
        assertion: typeof suggestion.assertion === "string" ? suggestion.assertion : undefined,
      },
    ];
  });
  return {
    overall: record.overall,
    suggestions,
  };
}

function extractClaudeResult(parsed: Record<string, unknown>): string {
  if (typeof parsed.result === "string") return parsed.result;
  if (typeof parsed.response === "string") return parsed.response;
  if (typeof parsed.content === "string") return parsed.content;
  return JSON.stringify(parsed);
}

async function readOptionalFile(path: string): Promise<string | undefined> {
  try {
    return await readFile(path, "utf8");
  } catch {
    return undefined;
  }
}

function failedProcessResult(error: unknown): EvalTaskResult {
  const stdout = error && typeof error === "object" && "stdout" in error && typeof error.stdout === "string" ? error.stdout : "";
  const stderr = error && typeof error === "object" && "stderr" in error && typeof error.stderr === "string" ? error.stderr : "";
  const parsedStdout = stdout.trim() ? tryParseAgentJson(stdout.trim()) : undefined;
  if (parsedStdout) {
    return resultFromParsedAgentJson(parsedStdout, stderr, true);
  }

  const message = error instanceof Error ? error.message : String(error);
  return {
    status: "failed",
    output: "",
    evidence: ["agent 进程执行失败。"],
    errors: [stderr.trim() || message],
  };
}

async function spawnWithInput(input: {
  command: string;
  args: string[];
  stdin: string;
  cwd: string;
  timeout: number;
  role?: "preflight" | "eval" | "grader" | "comparator";
}): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(input.command, input.args, {
      cwd: input.cwd,
      env: {
        ...process.env,
        ...(input.role ? { SHINKA_AGENT_ROLE: input.role } : {}),
      },
      stdio: ["pipe", "pipe", "pipe"],
    });
    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`agent 进程超时：${input.timeout}ms`));
    }, input.timeout);

    child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      const result = {
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      };
      if (code === 0) {
        resolve(result);
      } else {
        const error = new Error(`agent 进程退出码：${code}`) as Error & { stdout?: string; stderr?: string };
        error.stdout = result.stdout;
        error.stderr = result.stderr;
        reject(error);
      }
    });

    child.stdin.end(input.stdin);
  });
}
