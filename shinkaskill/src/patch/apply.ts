import { constants } from "node:fs";
import { access, cp, readdir, realpath, rm, stat } from "node:fs/promises";
import { isAbsolute, join, parse, relative, resolve } from "node:path";
import { withApplyLock } from "../storage/locks.js";

export type ApplySandboxSkillInput = {
  sandboxDir: string;
  targetDir: string;
};

export async function applySandboxSkill(input: ApplySandboxSkillInput): Promise<void> {
  const sandboxDir = await requireSkillDirectory(input.sandboxDir, "sandboxDir");
  const targetDir = await requireSkillDirectory(input.targetDir, "targetDir");

  if (sandboxDir.realPath === targetDir.realPath) {
    throw new Error("sandboxDir 和 targetDir 不能相同，避免把沙箱直接写回自身。");
  }

  if (isNestedPath(sandboxDir.realPath, targetDir.realPath) || isNestedPath(targetDir.realPath, sandboxDir.realPath)) {
    throw new Error("sandboxDir 和 targetDir 不能互为父子目录，避免镜像写回时删除或污染输入。");
  }

  const lockPath = join(targetDir.realPath, ".shinka-apply.lock");
  await withApplyLock(lockPath, async () => {
    await mirrorDirectory({ fromDir: sandboxDir.realPath, toDir: targetDir.realPath, lockPath });
  });
}

type SkillDirectory = {
  realPath: string;
};

async function requireSkillDirectory(path: string, label: string): Promise<SkillDirectory> {
  if (path.trim() === "") {
    throw new Error(`${label} 不能为空，避免危险写回。`);
  }

  const resolved = resolve(path);
  if (parse(resolved).root === resolved) {
    throw new Error(`${label} 是危险目标：不能使用根目录。`);
  }

  const realPath = await resolveExistingPath(resolved, label);
  if (parse(realPath).root === realPath) {
    throw new Error(`${label} 是危险目标：不能使用根目录。`);
  }

  const pathStat = await stat(realPath);
  if (!pathStat.isDirectory()) {
    throw new Error(`${label} 必须是已存在目录：${path}`);
  }

  const skillPath = join(realPath, "SKILL.md");
  try {
    await access(skillPath, constants.R_OK);
    const skillStat = await stat(skillPath);
    if (!skillStat.isFile()) {
      throw new Error(`${label} 不是 skill 目录：SKILL.md 必须是文件。`);
    }
  } catch (error) {
    if (error instanceof Error && error.message.includes("不是 skill 目录")) {
      throw error;
    }
    throw new Error(`${label} 不是 skill 目录：缺少可读 SKILL.md。`);
  }

  return { realPath };
}

async function resolveExistingPath(path: string, label: string): Promise<string> {
  try {
    return await realpath(path);
  } catch {
    throw new Error(`${label} 必须是已存在目录：${path}`);
  }
}

function isNestedPath(childPath: string, parentPath: string): boolean {
  const pathFromParent = relative(parentPath, childPath);
  return pathFromParent !== "" && !pathFromParent.startsWith("..") && !isAbsolute(pathFromParent);
}

async function mirrorDirectory(input: { fromDir: string; toDir: string; lockPath: string }): Promise<void> {
  const existingEntries = await readdir(input.toDir);
  await Promise.all(
    existingEntries.map(async (entry) => {
      const targetPath = join(input.toDir, entry);
      if (targetPath === input.lockPath) return;
      await rm(targetPath, { recursive: true, force: true });
    }),
  );

  await cp(input.fromDir, input.toDir, { recursive: true, force: true });
}
