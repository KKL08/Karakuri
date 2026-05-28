import YAML from "yaml";

export type Frontmatter = {
  name?: string;
  description?: string;
};

export type ParsedFrontmatter = { ok: true; frontmatter: Frontmatter; body: string } | { ok: false; reason: string };

export function parseSkillFrontmatter(raw: string): ParsedFrontmatter {
  if (!raw.startsWith("---\n")) {
    return { ok: false, reason: "文件必须以 YAML frontmatter 开头" };
  }

  const end = raw.indexOf("\n---", 4);
  if (end === -1) {
    return { ok: false, reason: "frontmatter 缺少结束标记" };
  }

  try {
    const frontmatter = normalizeFrontmatter(YAML.parse(raw.slice(4, end)));
    return { ok: true, frontmatter, body: raw.slice(end + 4).trimStart() };
  } catch (error) {
    return { ok: false, reason: error instanceof Error ? error.message : String(error) };
  }
}

export function parseOptionalSkillFrontmatter(raw: string): Frontmatter {
  const parsed = parseSkillFrontmatter(raw);
  return parsed.ok ? parsed.frontmatter : {};
}

function normalizeFrontmatter(value: unknown): Frontmatter {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return {};
  const record = value as Record<string, unknown>;
  return {
    name: typeof record.name === "string" ? record.name : undefined,
    description: typeof record.description === "string" ? record.description : undefined,
  };
}
