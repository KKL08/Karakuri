import { readdir, readFile, stat } from "node:fs/promises";
import { basename, join, resolve } from "node:path";
import type { SkillTarget } from "./types.js";
import { parseOptionalSkillFrontmatter } from "./frontmatter.js";

export async function discoverSkills(paths: string[]): Promise<SkillTarget[]> {
  const roots = paths.length > 0 ? paths : [process.cwd()];
  const targets: SkillTarget[] = [];

  for (const input of roots) {
    const root = resolve(input);
    const direct = join(root, "SKILL.md");
    if (await existsFile(direct)) {
      targets.push(await targetFromSkillFile(root, direct));
      continue;
    }

    for (const entry of await safeReaddir(root)) {
      const candidateRoot = join(root, entry);
      const candidateSkill = join(candidateRoot, "SKILL.md");
      if (await existsFile(candidateSkill)) {
        targets.push(await targetFromSkillFile(candidateRoot, candidateSkill));
      }
    }
  }

  return targets;
}

async function targetFromSkillFile(rootDir: string, skillFile: string): Promise<SkillTarget> {
  const raw = await readFile(skillFile, "utf8");
  const frontmatter = parseOptionalSkillFrontmatter(raw);
  return {
    name: frontmatter.name ?? basename(rootDir),
    description: frontmatter.description,
    rootDir,
    skillFile,
  };
}

async function existsFile(path: string): Promise<boolean> {
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}

async function safeReaddir(path: string): Promise<string[]> {
  try {
    return await readdir(path);
  } catch {
    return [];
  }
}
