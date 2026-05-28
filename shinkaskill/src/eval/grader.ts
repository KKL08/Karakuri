export type Confidence = "high" | "medium" | "low" | "unavailable";

export function confidenceForExecution(input: {
  evalSubagent: boolean;
  graderSubagent: boolean;
  comparatorSubagent: boolean;
}): Confidence {
  if (!input.evalSubagent) return "unavailable";
  if (input.graderSubagent && input.comparatorSubagent) return "high";

  return "medium";
}
