import { constants } from "node:fs";
import { access } from "node:fs/promises";
import { Command } from "commander";
import { buildEvalConsentRequest, createCliConfirmation, createNonInteractiveConfirmation } from "../../core/confirm.js";
import { discoverSkills } from "../../core/discover.js";
import { createClaudeCodeEvalAdapter } from "../../eval/adapters/claude-code.js";
import { createCodexEvalAdapter } from "../../eval/adapters/codex.js";
import { createGenericEvalAdapter } from "../../eval/adapters/generic.js";
import type { EvalAdapter } from "../../eval/adapters/types.js";
import { MAX_CONCURRENT_AGENTS, runSkillEval } from "../../eval/run.js";

type EvalOptions = {
  yes?: boolean;
  adapter: "generic" | "codex" | "claude-code";
  maxConcurrentAgents: string;
  agentTimeoutMs: string;
  consentJson?: boolean;
};

export function registerEvalCommand(program: Command): void {
  program
    .command("eval")
    .argument("[paths...]", "skill 路径")
    .option("--yes", "非交互模式下允许 eval gate")
    .option("--adapter <name>", "eval adapter：generic、codex、claude-code", "generic")
    .option("--max-concurrent-agents <count>", "真实 eval 同时启动的 subagent 数，1-8", "1")
    .option("--agent-timeout-ms <ms>", "单个 subagent 任务超时时间，默认 120000", "120000")
    .option("--consent-json", "只输出可供 runtime adapter 使用的结构化授权请求，不创建 run")
    .description("准备 skill eval，并在真实运行前请求授权")
    .action(async (paths: string[], options: EvalOptions) => {
      const adapterName = parseAdapterName(options.adapter);
      const maxConcurrentAgents = parseMaxConcurrentAgents(options.maxConcurrentAgents);
      const agentTimeoutMs = parseAgentTimeoutMs(options.agentTimeoutMs);
      const readable = await ensureExplicitPathsReadable(paths);
      if (!readable) return;

      const targets = await discoverSkills(paths);
      if (targets.length === 0) {
        process.stderr.write("没有发现可 eval 的 skill。请传入包含 SKILL.md 的目录，或包含 skill 子目录的目录。\n");
        process.exitCode = 1;
        return;
      }

      if (options.consentJson) {
        process.stdout.write(
          `${JSON.stringify(
            buildEvalConsentRequest({
              targetNames: targets.map((target) => target.name),
              targetPaths: targets.map((target) => target.rootDir),
              adapterName,
              maxConcurrentAgents,
              mayRunCommands: adapterName !== "generic",
            }),
            null,
            2,
          )}\n`,
        );
        return;
      }

      if (!options.yes && process.stdin.isTTY !== true) {
        process.stdout.write(
          "已取消 eval：当前是非交互环境。请显式传入 --yes 才能授权 eval；没有复制到沙箱，也没有修改原始 skill。\n",
        );
        process.exitCode = 1;
        return;
      }

      const confirmation = options.yes
        ? createNonInteractiveConfirmation({ allowEval: true, allowApply: false })
        : createCliConfirmation();
      const approved = await confirmation.confirmEval({
        targetNames: targets.map((target) => target.name),
        targetPaths: targets.map((target) => target.rootDir),
        adapterName,
        maxConcurrentAgents,
        mayRunCommands: adapterName !== "generic",
      });

      if (!approved) {
        process.stdout.write("已取消 eval，没有复制到沙箱，也没有修改原始 skill。\n");
        return;
      }

      process.stdout.write(`已授权 eval：${targets.map((target) => target.name).join(", ")}\n`);
      for (const target of targets) {
        const adapter = createEvalAdapter(adapterName, agentTimeoutMs);
        const summary = await runSkillEval({
          target,
          workspaceDir: process.cwd(),
          adapter,
          includeCandidate: false,
          maxConcurrentAgents,
          onProgress(event) {
            process.stdout.write(formatProgressEvent(event));
          },
        });
        process.stdout.write(`Adapter：${summary.adapterName}\n`);
        process.stdout.write(`Subagent 并发上限：${summary.maxConcurrentAgents}\n`);
        process.stdout.write(`已创建 eval run：${summary.runId}\n`);
        process.stdout.write(`Run 目录：${summary.runDir}\n`);
        process.stdout.write(`结果文件：${summary.resultPath}\n`);
        process.stdout.write(`报告文件：${summary.reportPath}\n`);
        process.stdout.write(`Eval 状态：${summary.status}\n`);
      }
      process.stdout.write("原始 skill 已复制到沙箱（本地 run 目录），原始目录不会被修改。\n");
      if (adapterName === "generic") {
        process.stdout.write("当前 runtime 尚未提供真实 subagent adapter，尚未运行真实 eval；尚未运行真实 subagent eval。\n");
      }
    });
}

function parseAdapterName(value: string): EvalOptions["adapter"] {
  if (value === "generic" || value === "codex" || value === "claude-code") return value;
  throw new Error(`未知 eval adapter：${value}。可选值：generic、codex、claude-code。`);
}

function parseMaxConcurrentAgents(value: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_CONCURRENT_AGENTS) {
    throw new Error(`--max-concurrent-agents 必须是 1 到 ${MAX_CONCURRENT_AGENTS} 之间的整数。`);
  }
  return parsed;
}

function parseAgentTimeoutMs(value: string): number {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 30_000) {
    throw new Error("--agent-timeout-ms 必须是大于等于 30000 的整数毫秒数。");
  }
  return parsed;
}

function createEvalAdapter(name: EvalOptions["adapter"], timeoutMs: number): EvalAdapter {
  if (name === "codex") {
    return createCodexEvalAdapter({
      command: process.env.SHINKA_CODEX_COMMAND,
      prefixArgs: parseJsonStringArray(process.env.SHINKA_CODEX_PREFIX_ARGS_JSON),
      timeoutMs,
    });
  }

  if (name === "claude-code") {
    return createClaudeCodeEvalAdapter({
      command: process.env.SHINKA_CLAUDE_COMMAND,
      prefixArgs: parseJsonStringArray(process.env.SHINKA_CLAUDE_PREFIX_ARGS_JSON),
      timeoutMs,
    });
  }

  return createGenericEvalAdapter();
}

function formatProgressEvent(event: {
  stage: string;
  status: string;
  current?: number;
  total?: number;
  promptId?: string;
  mode?: string;
  message?: string;
}): string {
  const count = typeof event.current === "number" && typeof event.total === "number" ? ` ${event.current}/${event.total}` : "";
  const target = [event.promptId, event.mode].filter(Boolean).join(" / ");
  const targetText = target ? ` ${target}` : "";
  const message = event.message ? `：${event.message}` : "";
  return `[${event.stage}] ${event.status}${count}${targetText}${message}\n`;
}

function parseJsonStringArray(value: string | undefined): string[] | undefined {
  if (!value) return undefined;
  const parsed = JSON.parse(value) as unknown;
  if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== "string")) {
    throw new Error("adapter prefix args 必须是 JSON 字符串数组。");
  }
  return parsed;
}

async function ensureExplicitPathsReadable(paths: string[]): Promise<boolean> {
  for (const path of paths) {
    try {
      await access(path, constants.R_OK);
    } catch {
      process.stderr.write(`无法读取 eval 路径：${path}。请确认路径存在且当前用户可访问。\n`);
      process.exitCode = 1;
      return false;
    }
  }

  return true;
}
