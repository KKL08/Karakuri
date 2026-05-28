export type EvalAdapterCapability =
  | { ok: true }
  | { ok: false; reason: string; remediation?: string };

export type EvalAdapterPreflightSpec = {
  runId: string;
  sandboxDir: string;
};

export type EvalTaskSpec = {
  runId: string;
  promptId: string;
  mode: "baseline" | "with_skill" | "candidate";
  prompt: string;
  expected: string;
  sandboxDir: string;
};

export type EvalTaskResult = {
  status: "completed" | "failed" | "unavailable";
  output: string;
  evidence: string[];
  errors: string[];
  score?: number;
  passed?: boolean;
  winner?: "baseline" | "with_skill" | "candidate" | "tie" | "output_a" | "output_b" | "output_c";
  expectationResults?: ExpectationResult[];
  rubricScores?: RubricScore[];
  gradingSummary?: GradingSummary;
  evalFeedback?: EvalFeedback;
};

export type ExpectationResult = {
  text: string;
  passed: boolean;
  evidence: string;
};

export type RubricScore = {
  key: string;
  label: string;
  score: number;
  maxScore: number;
  passed: boolean;
  evidence: string;
  source?: string;
};

export type GradingSummary = {
  passed: number;
  failed: number;
  total: number;
  passRate: number;
};

export type EvalFeedback = {
  overall: string;
  suggestions: Array<{
    reason: string;
    assertion?: string;
  }>;
};

export type GraderTaskSpec = {
  runId: string;
  promptId: string;
  mode: "baseline" | "with_skill" | "candidate";
  prompt: string;
  expected: string;
  output: string;
  sandboxDir: string;
};

export type ComparatorTaskSpec = {
  runId: string;
  promptId: string;
  prompt: string;
  expected: string;
  baselineOutput: string;
  withSkillOutput: string;
  candidateOutput?: string;
  sandboxDir: string;
};

export type EvalAdapter = {
  name: string;
  canSpawn(): Promise<EvalAdapterCapability>;
  preflight?(task: EvalAdapterPreflightSpec): Promise<EvalAdapterCapability>;
  spawnEvalAgent(task: EvalTaskSpec): Promise<EvalTaskResult>;
  spawnGraderAgent(task: GraderTaskSpec): Promise<EvalTaskResult>;
  spawnComparatorAgent(task: ComparatorTaskSpec): Promise<EvalTaskResult>;
  close(): Promise<void>;
};
