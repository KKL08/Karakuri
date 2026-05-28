import { z } from "zod";

export const LocaleSchema = z.enum(["zh-CN", "en-US"]);
export type Locale = z.infer<typeof LocaleSchema>;

export const GateStatusSchema = z.enum(["pass", "warn", "fail"]);
export type GateStatus = z.infer<typeof GateStatusSchema>;

export type GateIssue = {
  id: string;
  status: GateStatus;
  message: string;
  file?: string;
};

export type StaticDimensionKey =
  | "metadata"
  | "progressiveDisclosure"
  | "workflowClarity"
  | "instructionSpecificity"
  | "boundaryHandling"
  | "resourceIntegrity"
  | "runtimeNeutrality"
  | "maintainability";

export type StaticDimensionScore = {
  key: StaticDimensionKey;
  label: string;
  weight: number;
  score: number;
  reasons: string[];
};

export type SkillTarget = {
  name: string;
  description?: string;
  rootDir: string;
  skillFile: string;
};
