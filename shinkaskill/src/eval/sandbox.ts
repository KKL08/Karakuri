import { cp, mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

export const RUN_STATUSES = [
  "created",
  "authorized",
  "running",
  "completed",
  "failed",
  "interrupted",
  "applying",
  "applied",
] as const;

export type RunStatus = (typeof RUN_STATUSES)[number];

export type SandboxRun = {
  id: string;
  runDir: string;
  originalDir: string;
  sandboxDir: string;
};

export async function createSandboxRun(input: {
  workspaceDir: string;
  targetName: string;
  sourceDir: string;
}): Promise<SandboxRun> {
  const id = `${new Date().toISOString().replace(/[:.]/g, "-")}-${slug(input.targetName)}-${Math.random().toString(36).slice(2, 8)}`;
  const runDir = join(input.workspaceDir, ".shinka", "runs", id);
  const originalDir = join(runDir, "original");
  const sandboxDir = join(runDir, "sandbox");
  await mkdir(runDir, { recursive: true });
  await copySkillSnapshot(input.sourceDir, originalDir);
  await copySkillSnapshot(input.sourceDir, sandboxDir);
  await writeManifest(runDir, {
    id,
    status: "created",
    targetName: input.targetName,
    sourceDir: input.sourceDir,
    createdAt: new Date().toISOString(),
  });
  return { id, runDir, originalDir, sandboxDir };
}

export async function updateRunStatus(runDir: string, status: RunStatus): Promise<void> {
  await updateRunManifest(runDir, { status });
}

export async function updateRunManifest(runDir: string, updates: Record<string, unknown>): Promise<void> {
  const manifestPath = join(runDir, "manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  Object.assign(manifest, updates, { updatedAt: new Date().toISOString() });
  await writeManifest(runDir, manifest);
}

export function isRunStatus(value: unknown): value is RunStatus {
  return typeof value === "string" && RUN_STATUSES.includes(value as RunStatus);
}

async function writeManifest(runDir: string, manifest: Record<string, unknown>): Promise<void> {
  await writeFile(join(runDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
}

async function copySkillSnapshot(sourceDir: string, targetDir: string): Promise<void> {
  await mkdir(targetDir, { recursive: true });
  const entries = await readdir(sourceDir);
  for (const entry of entries) {
    if (entry === ".shinka") continue;
    await cp(join(sourceDir, entry), join(targetDir, entry), { recursive: true });
  }
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-|-$/g, "") || "skill";
}
