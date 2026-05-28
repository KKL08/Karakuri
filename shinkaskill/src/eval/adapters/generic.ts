import type { EvalAdapter, EvalTaskResult } from "./types.js";

const unavailableReason = "当前 runtime 未提供隔离 subagent 能力。";
const unavailableEvidence = "当前 runtime 未提供隔离 subagent 能力，未运行真实 eval。";

export function createGenericEvalAdapter(): EvalAdapter {
  return {
    name: "generic",
    async canSpawn() {
      return { ok: false, reason: unavailableReason };
    },
    async spawnEvalAgent(): Promise<EvalTaskResult> {
      return {
        status: "unavailable",
        output: "",
        evidence: [unavailableEvidence],
        errors: [],
      };
    },
    async spawnGraderAgent(): Promise<EvalTaskResult> {
      return {
        status: "unavailable",
        output: "",
        evidence: ["当前 runtime 未提供隔离 grader subagent 能力，未运行真实评分。"],
        errors: [],
      };
    },
    async spawnComparatorAgent(): Promise<EvalTaskResult> {
      return {
        status: "unavailable",
        output: "",
        evidence: ["当前 runtime 未提供隔离 comparator subagent 能力，未运行真实盲审。"],
        errors: [],
      };
    },
    async close() {},
  };
}
