import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { renderEvalMarkdownReport } from "../core/report.js";
import type { SkillTarget } from "../core/types.js";
import { generatePromptSuite, loadPromptSuite, metaCheckPrompt } from "../core/test-prompts.js";
import { confidenceForExecution, type Confidence } from "./grader.js";
import { buildRunPlan } from "./run-plan.js";
import { createSandboxRun, updateRunManifest } from "./sandbox.js";
import type { EvalAdapter, EvalAdapterCapability, EvalTaskResult } from "./adapters/types.js";

export const MAX_CONCURRENT_AGENTS = 8;
const DEFAULT_CONCURRENT_AGENTS = 1;

export type EvalPipelineStatus = "completed" | "failed" | "unavailable";

export type EvalRunSummary = {
  runId: string;
  runDir: string;
  targetName: string;
  adapterName: string;
  status: EvalPipelineStatus;
  confidence: Confidence;
  promptCount: number;
  planCount: number;
  maxConcurrentAgents: number;
  resultPath: string;
  reportPath: string;
};

export type EvalProgressStage = "preflight" | "eval" | "grader" | "comparator" | "report";
export type EvalProgressStatus = "started" | "completed" | "failed" | "skipped";

export type EvalProgressEvent = {
  stage: EvalProgressStage;
  status: EvalProgressStatus;
  current?: number;
  total?: number;
  promptId?: string;
  mode?: "baseline" | "with_skill" | "candidate";
  message?: string;
};

type EvalResultRecord = EvalTaskResult & {
  promptId: string;
  mode: "baseline" | "with_skill" | "candidate";
};

type GraderResultRecord = EvalTaskResult & {
  promptId: string;
  mode: "baseline" | "with_skill" | "candidate";
};

type ComparatorResultRecord = EvalTaskResult & {
  promptId: string;
};

export async function runSkillEval(input: {
  target: SkillTarget;
  workspaceDir: string;
  adapter: EvalAdapter;
  includeCandidate: boolean;
  maxConcurrentAgents?: number;
  onProgress?: (event: EvalProgressEvent) => void;
}): Promise<EvalRunSummary> {
  const maxConcurrentAgents = normalizeMaxConcurrentAgents(input.maxConcurrentAgents ?? DEFAULT_CONCURRENT_AGENTS);
  const run = await createSandboxRun({
    workspaceDir: input.workspaceDir,
    targetName: input.target.name,
    sourceDir: input.target.rootDir,
  });

  await updateRunManifest(run.runDir, { status: "authorized", evalStatus: "authorized" });

  try {
    await updateRunManifest(run.runDir, { status: "running", evalStatus: "running" });

    const prompts = await promptsForTarget(input.target);
    const promptChecks = prompts.map((prompt) => ({ promptId: prompt.id, ...metaCheckPrompt(prompt) }));
    const plan = buildRunPlan({ promptIds: prompts.map((prompt) => prompt.id), includeCandidate: input.includeCandidate });
    input.onProgress?.({ stage: "preflight", status: "started", message: "检查 adapter 是否可运行。" });
    const spawnCapability = await input.adapter.canSpawn();
    const capability = spawnCapability.ok && input.adapter.preflight
      ? await input.adapter.preflight({ runId: run.id, sandboxDir: run.sandboxDir })
      : spawnCapability;
    input.onProgress?.({
      stage: "preflight",
      status: capability.ok ? "completed" : spawnCapability.ok ? "failed" : "skipped",
      message: capability.ok ? "adapter preflight 通过。" : capability.reason,
    });
    const results = capability.ok
      ? await runPlanWithAdapter({
          adapter: input.adapter,
          runId: run.id,
          sandboxDir: run.sandboxDir,
          prompts,
          plan,
          maxConcurrentAgents,
          onProgress: input.onProgress,
        })
      : unavailableResults({ capability, plan });
    const evalCompleted = results.every((result) => result.status === "completed");
    const graderResults = capability.ok && evalCompleted
      ? await runGraderWithAdapter({
          adapter: input.adapter,
          runId: run.id,
          sandboxDir: run.sandboxDir,
          prompts,
          results,
          maxConcurrentAgents,
          onProgress: input.onProgress,
        })
      : [];
    const comparisons = capability.ok && evalCompleted
      ? await runComparatorWithAdapter({
          adapter: input.adapter,
          runId: run.id,
          sandboxDir: run.sandboxDir,
          prompts,
          results,
          maxConcurrentAgents,
          onProgress: input.onProgress,
        })
      : [];
    const status = summarizeStatus([...results, ...graderResults, ...comparisons]);
    const confidence = confidenceForExecution({
      evalSubagent: capability.ok && evalCompleted,
      graderSubagent: graderResults.length > 0 && graderResults.every((result) => result.status === "completed"),
      comparatorSubagent: comparisons.length > 0 && comparisons.every((result) => result.status === "completed"),
    });
    const resultPath = join(run.runDir, "eval-results.json");
    const reportPath = join(run.runDir, "eval-report.md");
    const evalDocument = {
      locale: "zh-CN" as const,
      run_id: run.id,
      target_name: input.target.name,
      status,
      confidence,
      adapter: input.adapter.name,
      adapter_capability: capability,
      max_concurrent_agents: maxConcurrentAgents,
      prompt_count: prompts.length,
      plan_count: plan.length,
      prompts,
      prompt_checks: promptChecks,
      plan,
      results,
      grader_results: graderResults,
      comparisons,
    };

    await writeFile(
      resultPath,
      `${JSON.stringify(evalDocument, null, 2)}\n`,
    );
    await writeFile(
      reportPath,
      renderEvalMarkdownReport({
        locale: "zh-CN",
        runId: run.id,
        targetName: input.target.name,
        status,
        confidence,
        adapter: input.adapter.name,
        promptCount: prompts.length,
        planCount: plan.length,
        maxConcurrentAgents,
        prompts,
        results,
        graderResults,
        comparisons,
      }),
    );

    input.onProgress?.({ stage: "report", status: "started", message: "写入 eval-results.json 和 eval-report.md。" });
    await updateRunManifest(run.runDir, {
      status: manifestStatusForEval(status),
      evalStatus: status,
      artifactsWritten: true,
      adapter: input.adapter.name,
      promptCount: prompts.length,
      planCount: plan.length,
      maxConcurrentAgents,
      resultPath: "eval-results.json",
      reportPath: "eval-report.md",
    });
    input.onProgress?.({ stage: "report", status: "completed", message: "报告已写入。" });

    return {
      runId: run.id,
      runDir: run.runDir,
      targetName: input.target.name,
      adapterName: input.adapter.name,
      status,
      confidence,
      promptCount: prompts.length,
      planCount: plan.length,
      maxConcurrentAgents,
      resultPath,
      reportPath,
    };
  } catch (error) {
    await updateRunManifest(run.runDir, {
      status: "failed",
      evalStatus: "failed",
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  } finally {
    await input.adapter.close();
  }
}

async function promptsForTarget(target: SkillTarget) {
  const loaded = await loadPromptSuite(target.rootDir);
  if (loaded.length > 0) return loaded;
  const skillBody = await readSkillBody(target.skillFile);
  return generatePromptSuite({ skillName: target.name, description: target.description, skillBody });
}

async function readSkillBody(skillFile: string): Promise<string | undefined> {
  try {
    return await readFile(skillFile, "utf8");
  } catch {
    return undefined;
  }
}

async function runPlanWithAdapter(input: {
  adapter: EvalAdapter;
  runId: string;
  sandboxDir: string;
  prompts: Awaited<ReturnType<typeof promptsForTarget>>;
  plan: ReturnType<typeof buildRunPlan>;
  maxConcurrentAgents: number;
  onProgress?: (event: EvalProgressEvent) => void;
}): Promise<EvalResultRecord[]> {
  const promptsById = new Map(input.prompts.map((prompt) => [prompt.id, prompt]));

  return runBounded(input.plan, input.maxConcurrentAgents, async (item, index) => {
    const prompt = promptsById.get(item.promptId);
    if (!prompt) throw new Error(`找不到 eval prompt：${item.promptId}`);
    input.onProgress?.({ stage: "eval", status: "started", current: index + 1, total: input.plan.length, promptId: item.promptId, mode: item.mode });
    const result = await input.adapter.spawnEvalAgent({
      runId: input.runId,
      promptId: item.promptId,
      mode: item.mode,
      prompt: prompt.prompt,
      expected: prompt.expected,
      sandboxDir: input.sandboxDir,
    });
    input.onProgress?.({ stage: "eval", status: result.status === "failed" ? "failed" : "completed", current: index + 1, total: input.plan.length, promptId: item.promptId, mode: item.mode });
    return { promptId: item.promptId, mode: item.mode, ...result };
  });
}

async function runGraderWithAdapter(input: {
  adapter: EvalAdapter;
  runId: string;
  sandboxDir: string;
  prompts: Awaited<ReturnType<typeof promptsForTarget>>;
  results: EvalResultRecord[];
  maxConcurrentAgents: number;
  onProgress?: (event: EvalProgressEvent) => void;
}): Promise<GraderResultRecord[]> {
  const promptsById = new Map(input.prompts.map((prompt) => [prompt.id, prompt]));

  return runBounded(input.results, input.maxConcurrentAgents, async (result, index) => {
    const prompt = promptsById.get(result.promptId);
    if (!prompt) throw new Error(`找不到 grader prompt：${result.promptId}`);
    input.onProgress?.({ stage: "grader", status: "started", current: index + 1, total: input.results.length, promptId: result.promptId, mode: result.mode });
    const graded = await input.adapter.spawnGraderAgent({
      runId: input.runId,
      promptId: result.promptId,
      mode: result.mode,
      prompt: prompt.prompt,
      expected: prompt.expected,
      output: result.output,
      sandboxDir: input.sandboxDir,
    });
    input.onProgress?.({ stage: "grader", status: graded.status === "failed" ? "failed" : "completed", current: index + 1, total: input.results.length, promptId: result.promptId, mode: result.mode });
    return { promptId: result.promptId, mode: result.mode, ...graded };
  });
}

async function runComparatorWithAdapter(input: {
  adapter: EvalAdapter;
  runId: string;
  sandboxDir: string;
  prompts: Awaited<ReturnType<typeof promptsForTarget>>;
  results: EvalResultRecord[];
  maxConcurrentAgents: number;
  onProgress?: (event: EvalProgressEvent) => void;
}): Promise<ComparatorResultRecord[]> {
  const promptsById = new Map(input.prompts.map((prompt) => [prompt.id, prompt]));
  const grouped = new Map<string, EvalResultRecord[]>();
  for (const result of input.results) {
    grouped.set(result.promptId, [...(grouped.get(result.promptId) ?? []), result]);
  }

  const groupedEntries = Array.from(grouped);
  const comparisons = await runBounded(groupedEntries, input.maxConcurrentAgents, async ([promptId, results], index): Promise<ComparatorResultRecord | undefined> => {
    const prompt = promptsById.get(promptId);
    if (!prompt) throw new Error(`找不到 comparator prompt：${promptId}`);
    const baseline = results.find((result) => result.mode === "baseline");
    const withSkill = results.find((result) => result.mode === "with_skill");
    const candidate = results.find((result) => result.mode === "candidate");
    if (!baseline || !withSkill) return undefined;
    input.onProgress?.({ stage: "comparator", status: "started", current: index + 1, total: groupedEntries.length, promptId });
    const comparison = await input.adapter.spawnComparatorAgent({
      runId: input.runId,
      promptId,
      prompt: prompt.prompt,
      expected: prompt.expected,
      baselineOutput: baseline.output,
      withSkillOutput: withSkill.output,
      candidateOutput: candidate?.status === "completed" ? candidate.output : undefined,
      sandboxDir: input.sandboxDir,
    });
    input.onProgress?.({ stage: "comparator", status: comparison.status === "failed" ? "failed" : "completed", current: index + 1, total: groupedEntries.length, promptId });
    return { promptId, ...comparison, winner: decodeComparatorWinner(comparison.winner) };
  });

  return comparisons.filter((item): item is ComparatorResultRecord => Boolean(item));
}

function manifestStatusForEval(status: EvalPipelineStatus): "completed" | "failed" {
  return status === "failed" ? "failed" : "completed";
}

function decodeComparatorWinner(winner: EvalTaskResult["winner"]): EvalTaskResult["winner"] {
  if (winner === "output_a") return "baseline";
  if (winner === "output_b") return "with_skill";
  if (winner === "output_c") return "candidate";
  return winner;
}

function unavailableResults(input: {
  capability: Extract<EvalAdapterCapability, { ok: false }>;
  plan: ReturnType<typeof buildRunPlan>;
}): EvalResultRecord[] {
  return input.plan.map((item) => ({
    promptId: item.promptId,
    mode: item.mode,
    status: "unavailable",
    output: "",
    evidence: [`${input.capability.reason} 未运行真实 eval。`],
    errors: [],
  }));
}

function summarizeStatus(results: EvalTaskResult[]): EvalPipelineStatus {
  if (results.every((result) => result.status === "unavailable")) return "unavailable";
  if (results.some((result) => result.status === "failed")) return "failed";
  return "completed";
}

function normalizeMaxConcurrentAgents(value: number): number {
  if (!Number.isInteger(value) || value < 1 || value > MAX_CONCURRENT_AGENTS) {
    throw new Error(`maxConcurrentAgents 必须是 1 到 ${MAX_CONCURRENT_AGENTS} 之间的整数。`);
  }
  return value;
}

async function runBounded<T, Result>(
  items: T[],
  maxConcurrent: number,
  worker: (item: T, index: number) => Promise<Result>,
): Promise<Result[]> {
  if (items.length === 0) return [];

  const results = new Array<Result>(items.length);
  let nextIndex = 0;
  let firstError: unknown;
  const workerCount = Math.min(maxConcurrent, items.length);

  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (true) {
        if (firstError) return;
        const index = nextIndex;
        nextIndex += 1;
        if (index >= items.length) return;
        try {
          results[index] = await worker(items[index], index);
        } catch (error) {
          firstError ??= error;
          return;
        }
      }
    }),
  );

  if (firstError) throw firstError;
  return results;
}
