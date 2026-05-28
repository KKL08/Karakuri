import { readFile, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import type { GateIssue, GateStatus, SkillTarget } from "./types.js";
import type { Frontmatter } from "./frontmatter.js";
import { parseSkillFrontmatter } from "./frontmatter.js";
import { msg } from "./i18n.js";

export type ValidationResult = {
  target: SkillTarget;
  status: GateStatus;
  frontmatter: Frontmatter;
  body: string;
  issues: GateIssue[];
};

export async function validateSkill(target: SkillTarget): Promise<ValidationResult> {
  const raw = await readFile(target.skillFile, "utf8");
  const parsed = parseSkillFrontmatter(raw);
  const issues: GateIssue[] = [];

  if (!parsed.ok) {
    issues.push({
      id: "invalid-frontmatter",
      status: "fail",
      message: msg("gate.invalidFrontmatter", { reason: parsed.reason }),
      file: target.skillFile,
    });
    return { target, status: "fail", frontmatter: {}, body: raw, issues };
  }

  if (!parsed.frontmatter.name) {
    issues.push({ id: "missing-name", status: "fail", message: "缺少 frontmatter name", file: target.skillFile });
  }

  if (!parsed.frontmatter.description) {
    issues.push({ id: "missing-description", status: "fail", message: "缺少 frontmatter description", file: target.skillFile });
  }

  for (const ref of findMarkdownReferences(parsed.body)) {
    const absolute = join(dirname(target.skillFile), ref);
    if (!(await existsPath(absolute))) {
      issues.push({
        id: "missing-reference",
        status: "warn",
        message: `引用文件不存在：${ref}`,
        file: target.skillFile,
      });
    }
  }

  const status = mergeStatus(issues.map((issue) => issue.status));
  return { target, status, frontmatter: parsed.frontmatter, body: parsed.body, issues };
}

function findMarkdownReferences(body: string): string[] {
  const refs = new Set<string>();
  const regex = /(?:references|scripts|assets)\/[A-Za-z0-9._/-]+/g;
  for (const match of body.matchAll(regex)) {
    refs.add(match[0]);
  }
  return [...refs];
}

async function existsPath(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

function mergeStatus(statuses: GateStatus[]): GateStatus {
  if (statuses.includes("fail")) return "fail";
  if (statuses.includes("warn")) return "warn";
  return "pass";
}
