import type { EvalAdapter, EvalAdapterCapability } from "./types.js";
import type { AgentProcessOptions } from "./process.js";
import { commandCanRun, runClaudeProcess } from "./process.js";
import { buildComparatorAgentPrompt, buildEvalAgentPrompt, buildGraderAgentPrompt } from "./prompt.js";

export type ClaudeCodeEvalAdapterOptions = Partial<AgentProcessOptions>;

export function createClaudeCodeEvalAdapter(options: ClaudeCodeEvalAdapterOptions = {}): EvalAdapter {
  const processOptions: AgentProcessOptions = {
    command: options.command ?? "claude",
    prefixArgs: options.prefixArgs ?? [],
    timeoutMs: options.timeoutMs,
  };
  return {
    name: "claude-code",
    async canSpawn() {
      if (await commandCanRun({ ...processOptions })) return { ok: true };
      return { ok: false, reason: `无法启动 Claude Code agent 命令：${processOptions.command}` };
    },
    async preflight(task) {
      const result = await runClaudeProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: `你是 ShinkaSkill 的 Claude Code adapter preflight。不要读取文件，不要运行命令，只输出 JSON：{"status":"completed","output":"preflight ok","evidence":["claude-code preflight completed"],"errors":[]}`,
        role: "preflight",
        agent: {
          name: "shinka-preflight",
          description: "Checks whether Claude Code can run isolated ShinkaSkill eval tasks.",
          prompt: "You are an isolated preflight checker. Return JSON only and do not edit files.",
        },
      });
      if (result.status === "completed") return { ok: true };
      return classifyClaudeCodePreflightFailure(result);
    },
    async spawnEvalAgent(task) {
      return runClaudeProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildEvalAgentPrompt(task),
        role: "eval",
      });
    },
    async spawnGraderAgent(task) {
      return runClaudeProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildGraderAgentPrompt(task),
        role: "grader",
        agent: {
          name: "shinka-grader",
          description: "Scores isolated ShinkaSkill eval outputs and returns JSON.",
          prompt: "You are an isolated grader. Score only the supplied output, do not edit files, and return JSON only.",
        },
      });
    },
    async spawnComparatorAgent(task) {
      return runClaudeProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildComparatorAgentPrompt(task),
        role: "comparator",
        agent: {
          name: "shinka-comparator",
          description: "Compares isolated ShinkaSkill eval outputs and returns JSON.",
          prompt: "You are an isolated comparator. Compare only the supplied outputs, do not edit files, and return JSON only.",
        },
      });
    },
    async close() {},
  };
}

function classifyClaudeCodePreflightFailure(result: { errors: string[]; evidence: string[] }): EvalAdapterCapability {
  const errorText = result.errors.join("\n");
  if (/\bauthenticat(?:e|ion)|unauthorized|401|invalid credentials/i.test(errorText)) {
    return {
      ok: false,
      reason: "Claude Code adapter preflight 失败：Claude Code CLI 认证不可用。",
      remediation: "先在当前机器完成 Claude Code 登录或认证，再重新运行真实 eval。",
    };
  }

  if (/permission|operation not permitted|EACCES|EPERM/i.test(errorText)) {
    return {
      ok: false,
      reason: "Claude Code adapter preflight 失败：当前环境权限不足。",
      remediation: "在 agent 环境中请求允许运行 Claude Code CLI，或让用户在本地终端直接运行同一条 shinka eval 命令。",
    };
  }

  return {
    ok: false,
    reason: `Claude Code adapter preflight 失败：${errorText || result.evidence.join("；") || "未知错误"}`,
    remediation: "先用 claude -p 运行一个最小任务确认 Claude Code CLI 可用，再重新运行 shinka eval。",
  };
}
