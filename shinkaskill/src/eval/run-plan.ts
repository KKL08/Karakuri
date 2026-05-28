export type EvalMode = "baseline" | "with_skill" | "candidate";

export type EvalRunPlanItem = {
  promptId: string;
  mode: EvalMode;
};

export function buildRunPlan(input: { promptIds: string[]; includeCandidate: boolean }): EvalRunPlanItem[] {
  validatePromptIds(input.promptIds);

  const modes: EvalMode[] = input.includeCandidate ? ["baseline", "with_skill", "candidate"] : ["baseline", "with_skill"];

  return input.promptIds.flatMap((promptId) => modes.map((mode) => ({ promptId, mode })));
}

function validatePromptIds(promptIds: string[]): void {
  if (promptIds.length === 0) {
    throw new Error("promptIds must include at least one prompt id.");
  }

  const seen = new Set<string>();
  for (const promptId of promptIds) {
    if (promptId.trim().length === 0) {
      throw new Error("promptIds must be non-empty strings.");
    }

    if (seen.has(promptId)) {
      throw new Error(`promptIds must be unique. Duplicate prompt id: ${promptId}`);
    }

    seen.add(promptId);
  }
}
