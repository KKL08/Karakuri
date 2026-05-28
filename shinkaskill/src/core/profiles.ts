import type { StaticDimensionKey } from "./types.js";

export const profileNames = ["agent-skills", "general", "text-only", "workflow", "scripted"] as const;

export type ProfileName = (typeof profileNames)[number];
type ConcreteProfileName = Exclude<ProfileName, "general">;

export type StaticProfile = {
  name: ConcreteProfileName;
  weights: Record<StaticDimensionKey, number>;
};

const agentSkills: StaticProfile = {
  name: "agent-skills",
  weights: {
    metadata: 12,
    progressiveDisclosure: 12,
    workflowClarity: 16,
    instructionSpecificity: 16,
    boundaryHandling: 12,
    resourceIntegrity: 10,
    runtimeNeutrality: 12,
    maintainability: 10,
  },
};

const textOnly: StaticProfile = {
  name: "text-only",
  weights: {
    metadata: 16,
    progressiveDisclosure: 12,
    workflowClarity: 12,
    instructionSpecificity: 20,
    boundaryHandling: 10,
    resourceIntegrity: 4,
    runtimeNeutrality: 12,
    maintainability: 14,
  },
};

const workflow: StaticProfile = {
  name: "workflow",
  weights: {
    metadata: 10,
    progressiveDisclosure: 10,
    workflowClarity: 22,
    instructionSpecificity: 18,
    boundaryHandling: 16,
    resourceIntegrity: 8,
    runtimeNeutrality: 8,
    maintainability: 8,
  },
};

const scripted: StaticProfile = {
  name: "scripted",
  weights: {
    metadata: 10,
    progressiveDisclosure: 10,
    workflowClarity: 12,
    instructionSpecificity: 14,
    boundaryHandling: 18,
    resourceIntegrity: 18,
    runtimeNeutrality: 10,
    maintainability: 8,
  },
};

const profiles: Record<ConcreteProfileName, StaticProfile> = {
  "agent-skills": agentSkills,
  "text-only": textOnly,
  workflow,
  scripted,
};

const profileNameSet: ReadonlySet<string> = new Set(profileNames);

export function parseProfileName(value: string): ProfileName {
  if (profileNameSet.has(value)) return value as ProfileName;
  throw new Error(`Unknown profile ${JSON.stringify(value)}. Allowed profiles: ${profileNames.join(", ")}.`);
}

export function getProfileFromString(value: string): StaticProfile {
  return getProfile(parseProfileName(value));
}

export function getProfile(name: ProfileName = "agent-skills"): StaticProfile {
  return name === "general" ? agentSkills : profiles[name];
}
