import { readdir, readFile, rm } from "node:fs/promises";
import { join } from "node:path";

export type CleanupPlan = {
  keepRunDirs: string[];
  deleteRunDirs: string[];
};

const KEEP_LAST_ERROR = "keepLast 必须是大于等于 0 的整数";
const KEEP_LAST_CLI_ERROR = "keep-last 必须是大于等于 0 的整数";
const OLDER_THAN_ERROR = "older-than 必须使用 Nd 格式，例如 30d";
const DAY_MS = 24 * 60 * 60 * 1000;

export function parseKeepLast(value: string): number {
  const normalized = value.trim();
  const keepLast = Number(normalized);
  if (normalized === "" || !Number.isInteger(keepLast) || keepLast < 0) {
    throw new Error(KEEP_LAST_CLI_ERROR);
  }
  return keepLast;
}

export function parseOlderThan(value: string): number {
  const normalized = value.trim();
  const match = /^(\d+)d$/.exec(normalized);
  if (!match) {
    throw new Error(OLDER_THAN_ERROR);
  }

  const days = Number(match[1]);
  if (!Number.isSafeInteger(days) || days <= 0) {
    throw new Error(OLDER_THAN_ERROR);
  }
  return days * DAY_MS;
}

export async function planCleanup(input: { runsDir: string; keepLast: number; olderThanMs?: number; now?: Date }): Promise<CleanupPlan> {
  assertValidKeepLast(input.keepLast);
  assertValidOlderThan(input.olderThanMs);
  const entries = await safeReaddir(input.runsDir);
  const runs = await Promise.all(
    entries.map(async (entry) => {
      const runDir = join(input.runsDir, entry);
      const manifest = await readManifest(runDir);
      return { runDir, createdAt: manifest.createdAt ?? "" };
    }),
  );

  runs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const protectedRuns = runs.slice(0, input.keepLast);
  const deletionCandidates = runs.slice(input.keepLast);
  const deleteRunDirs =
    input.olderThanMs === undefined
      ? deletionCandidates.map((run) => run.runDir)
      : deletionCandidates.filter((run) => isOlderThan(run.createdAt, input.olderThanMs as number, input.now ?? new Date())).map((run) => run.runDir);

  return {
    keepRunDirs: [
      ...protectedRuns.map((run) => run.runDir),
      ...deletionCandidates.filter((run) => !deleteRunDirs.includes(run.runDir)).map((run) => run.runDir),
    ],
    deleteRunDirs,
  };
}

export async function executeCleanup(plan: CleanupPlan): Promise<void> {
  for (const runDir of plan.deleteRunDirs) {
    await rm(runDir, { recursive: true, force: true });
  }
}

function assertValidKeepLast(keepLast: number): void {
  if (!Number.isInteger(keepLast) || keepLast < 0) {
    throw new Error(KEEP_LAST_ERROR);
  }
}

function assertValidOlderThan(olderThanMs: number | undefined): void {
  if (olderThanMs === undefined) return;
  if (!Number.isSafeInteger(olderThanMs) || olderThanMs <= 0) {
    throw new Error("olderThanMs 必须是大于 0 的整数毫秒数");
  }
}

function isOlderThan(createdAt: string, olderThanMs: number, now: Date): boolean {
  const timestamp = Date.parse(createdAt);
  if (Number.isNaN(timestamp)) return false;
  return now.getTime() - timestamp > olderThanMs;
}

async function safeReaddir(path: string): Promise<string[]> {
  try {
    return await readdir(path);
  } catch {
    return [];
  }
}

async function readManifest(runDir: string): Promise<{ createdAt?: string }> {
  try {
    return JSON.parse(await readFile(join(runDir, "manifest.json"), "utf8"));
  } catch {
    return {};
  }
}
