import { stdin as input, stdout as output } from "node:process";
import { createInterface } from "node:readline/promises";

export type EvalConfirmationRequest = {
  targetNames: string[];
  targetPaths?: string[];
  adapterName?: "generic" | "codex" | "claude-code" | string;
  maxConcurrentAgents?: number;
  mayRunCommands: boolean;
};

export type ApplyConfirmationRequest = {
  targetPath: string;
  patchPath: string;
};

export type ConfirmationAdapter = {
  confirmEval(request: EvalConfirmationRequest): Promise<boolean>;
  confirmApply(request: ApplyConfirmationRequest): Promise<boolean>;
};

export type StructuredConsentOption = {
  id: "approve" | "deny";
  label: string;
  description: string;
};

export type StructuredEvalConsentRequest = {
  kind: "eval";
  title: string;
  question: string;
  targetNames: string[];
  targetPaths: string[];
  adapterName: string;
  maxConcurrentAgents?: number;
  riskItems: string[];
  options: StructuredConsentOption[];
  runtime_adapter_hint: {
    preferred_tool: "request_user_input";
    portable_adapters: {
      codex: "request_user_input";
      claude_code: "AskUserQuestion";
    };
    plain_text_fallback: string;
  };
};

export function buildEvalConsentRequest(request: EvalConfirmationRequest): StructuredEvalConsentRequest {
  const adapterName = request.adapterName ?? "generic";
  const realAgentEval = request.mayRunCommands;
  const adapterLabel = adapterDisplayName(adapterName);
  const targetNames = request.targetNames.length > 0 ? request.targetNames : ["当前路径中的 skill"];
  const targetPaths = request.targetPaths ?? [];
  const riskItems = [
    "会把目标 skill 复制到本地 sandbox。",
    realAgentEval
      ? `会启动当前环境中的 ${adapterLabel} subagent 进行真实测试。`
      : "默认 generic adapter 不会启动真实 agent，也不会运行外部评测任务。",
    ...(realAgentEval
      ? [
          "真实 eval 会启动 subagent，所有步骤都在当前 ShinkaSkill run 的 sandbox 内完成。",
          `同一时间最多启动 ${request.maxConcurrentAgents ?? 1} 个 subagent 任务。`,
          "不会触发 apply、commit 或其他写回链路。",
          "所选 agent runtime 仍会按当前环境配置完成推理。",
        ]
      : []),
    "原始 skill 不会被直接修改。",
  ];

  const structuredRequest: Omit<StructuredEvalConsentRequest, "runtime_adapter_hint"> = {
    kind: "eval",
    title: "是否运行真实 eval？",
    question: realAgentEval
      ? `是否同意启动 ${adapterLabel} agent 运行 ShinkaSkill eval？`
      : "是否同意创建 ShinkaSkill eval run？",
    targetNames,
    targetPaths,
    adapterName,
    maxConcurrentAgents: request.maxConcurrentAgents,
    riskItems,
    options: [
      {
        id: "approve",
        label: "同意运行",
        description: realAgentEval ? "启动真实 eval，在当前 run sandbox 内完成。" : "创建 eval run。",
      },
      {
        id: "deny",
        label: "取消",
        description: "不启动真实 eval，也不复制或修改原始 skill。",
      },
    ],
  };
  return {
    ...structuredRequest,
    runtime_adapter_hint: {
      preferred_tool: "request_user_input",
      portable_adapters: {
        codex: "request_user_input",
        claude_code: "AskUserQuestion",
      },
      plain_text_fallback: formatCliConsentQuestion(structuredRequest),
    },
  };
}

export function createNonInteractiveConfirmation(policy: {
  allowEval: boolean;
  allowApply: boolean;
}): ConfirmationAdapter {
  return {
    async confirmEval() {
      return policy.allowEval;
    },
    async confirmApply() {
      return policy.allowApply;
    },
  };
}

export function createCliConfirmation(): ConfirmationAdapter {
  return {
    async confirmEval(request) {
      const consent = buildEvalConsentRequest(request);
      return askYes(formatCliConsentQuestion(consent));
    },
    async confirmApply(request) {
      return askYes(
        `将把 patch ${request.patchPath} 应用到 ${request.targetPath}。这是单独的 apply 授权，不会因为 eval 授权自动通过。是否继续？ [y/N] `,
      );
    },
  };
}

function adapterDisplayName(adapterName: string): string {
  if (adapterName === "codex") return "Codex";
  if (adapterName === "claude-code") return "Claude Code";
  return adapterName;
}

function formatCliConsentQuestion(request: Omit<StructuredEvalConsentRequest, "runtime_adapter_hint">): string {
  const targetText = request.targetNames.join(", ");
  const pathText = request.targetPaths.length > 0 ? `\n路径：${request.targetPaths.join(", ")}` : "";
  const risks = request.riskItems.map((item) => `- ${item}`).join("\n");
  return `${request.title}
${request.question}
目标：${targetText}${pathText}
风险：
${risks}
是否继续？ [y/N] `;
}

async function askYes(question: string): Promise<boolean> {
  if (input.isTTY !== true) {
    return false;
  }

  const rl = createInterface({ input, output });
  try {
    const answer = await rl.question(question);
    const normalized = answer.trim().toLowerCase();
    return normalized === "y" || normalized === "yes";
  } finally {
    rl.close();
  }
}
