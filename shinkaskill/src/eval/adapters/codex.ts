import type { EvalAdapter, EvalAdapterCapability } from "./types.js";
import type { AgentProcessOptions } from "./process.js";
import { commandCanRun, runCodexProcess } from "./process.js";
import { buildComparatorAgentPrompt, buildEvalAgentPrompt, buildGraderAgentPrompt } from "./prompt.js";

export type CodexEvalAdapterOptions = Partial<AgentProcessOptions>;

export function createCodexEvalAdapter(options: CodexEvalAdapterOptions = {}): EvalAdapter {
  const processOptions: AgentProcessOptions = {
    command: options.command ?? "codex",
    prefixArgs: options.prefixArgs ?? [],
    timeoutMs: options.timeoutMs,
  };
  return {
    name: "codex",
    async canSpawn() {
      if (await commandCanRun({ ...processOptions })) return { ok: true };
      return { ok: false, reason: `无法启动 Codex agent 命令：${processOptions.command}` };
    },
    async preflight(task) {
      const result = await runCodexProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: `你是 ShinkaSkill 的 Codex adapter preflight。不要读取文件，不要运行命令，只输出 JSON：{"status":"completed","output":"preflight ok","evidence":["codex preflight completed"],"errors":[]}`,
        role: "preflight",
      });
      if (result.status === "completed") return { ok: true };
      return classifyCodexPreflightFailure(result);
    },
    async spawnEvalAgent(task) {
      return runCodexProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildEvalAgentPrompt(task),
        role: "eval",
      });
    },
    async spawnGraderAgent(task) {
      return runCodexProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildGraderAgentPrompt(task),
        role: "grader",
      });
    },
    async spawnComparatorAgent(task) {
      return runCodexProcess({
        options: processOptions,
        sandboxDir: task.sandboxDir,
        prompt: buildComparatorAgentPrompt(task),
        role: "comparator",
      });
    },
    async close() {},
  };
}

function classifyCodexPreflightFailure(result: { errors: string[]; evidence: string[] }): EvalAdapterCapability {
  const errorText = result.errors.join("\n");
  if (/readonly database|Operation not permitted|failed to initialize in-process app-server client/i.test(errorText)) {
    return {
      ok: false,
      reason: "Codex adapter preflight 失败：外层 Codex 工具沙箱阻止 Codex CLI 写入自身状态目录。",
      remediation: "在 Codex agent 中请求提权运行同一条 shinka eval 命令，或让用户在本地终端直接运行；ShinkaSkill 的 run sandbox 和被测 skill 都不需要写回原始目录。",
    };
  }

  if (/\bauthenticat(?:e|ion)|unauthorized|401|invalid credentials/i.test(errorText)) {
    return {
      ok: false,
      reason: "Codex adapter preflight 失败：Codex CLI 认证不可用。",
      remediation: "先在当前机器完成 Codex CLI 登录或认证，再重新运行真实 eval。",
    };
  }

  return {
    ok: false,
    reason: `Codex adapter preflight 失败：${errorText || result.evidence.join("；") || "未知错误"}`,
    remediation: "先用 codex exec 运行一个最小任务确认 Codex CLI 可用，再重新运行 shinka eval。",
  };
}
