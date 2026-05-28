import { readFile, realpath, stat, writeFile } from "node:fs/promises";
import { isAbsolute, join, relative, resolve } from "node:path";
import { createUnifiedDiff } from "./diff.js";

export type ProposedPatch = {
  patchPath: string;
  diff: string;
};

export type ProposeSkillPatchInput = {
  runDir: string;
  originalDir: string;
  sandboxDir: string;
  summary: string;
};

export async function proposeSkillPatch(input: ProposeSkillPatchInput): Promise<ProposedPatch> {
  const runDir = await requireDirectory(input.runDir, "runDir");
  const originalDir = await requireDirectory(input.originalDir, "originalDir");
  const sandboxDir = await requireDirectory(input.sandboxDir, "sandboxDir");
  const originalSkill = join(originalDir, "SKILL.md");
  const sandboxSkill = join(sandboxDir, "SKILL.md");
  const before = await readFile(originalSkill, "utf8");
  const after = await readFile(sandboxSkill, "utf8");
  const diff = createUnifiedDiff({
    fromFile: "original/SKILL.md",
    toFile: "sandbox/SKILL.md",
    before,
    after,
  });
  const patchPath = resolve(runDir, "patch.diff");

  if (!isPathInside(runDir, patchPath)) {
    throw new Error(`patchPath 必须留在 runDir 内：${patchPath}`);
  }

  try {
    await writeFile(patchPath, `${formatSummary(input.summary)}\n\n${diff}`, { flag: "wx" });
  } catch (error) {
    if (isNodeError(error) && error.code === "EEXIST") {
      throw new Error(`patch.diff 已存在：${patchPath}。请先审阅或清理旧 patch。`);
    }
    throw error;
  }

  return {
    patchPath,
    diff,
  };
}

async function requireDirectory(path: string, label: string): Promise<string> {
  if (path.trim() === "") {
    throw new Error(`${label} 不能为空`);
  }

  const resolved = await realpath(resolve(path));
  const pathStat = await stat(resolved);
  if (!pathStat.isDirectory()) {
    throw new Error(`${label} 必须是目录：${path}`);
  }

  return resolved;
}

function formatSummary(summary: string): string {
  return summary.replace(/\r\n/g, "\n").split("\n").map((line) => `# ${line}`).join("\n");
}

function isPathInside(parentPath: string, childPath: string): boolean {
  const pathFromParent = relative(parentPath, childPath);
  return pathFromParent !== "" && !pathFromParent.startsWith("..") && !isAbsolute(pathFromParent);
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
