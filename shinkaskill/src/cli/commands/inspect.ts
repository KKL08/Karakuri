import { Command } from "commander";
import { discoverSkills } from "../../core/discover.js";
import { getProfileFromString } from "../../core/profiles.js";
import { renderInspectJson, renderInspectMarkdown, type InspectReport } from "../../core/report.js";
import { scoreStaticSkill } from "../../core/static-rubric.js";
import { validateSkill } from "../../core/validate.js";

type InspectOptions = {
  profile?: string;
  json?: boolean;
};

export function registerInspectCommand(program: Command): void {
  program
    .command("inspect")
    .argument("[paths...]", "skill 路径")
    .option("--profile <profile>", "评分 profile", "agent-skills")
    .option("--json", "输出 JSON")
    .description("检查 skill 并生成中文报告")
    .action(async (paths: string[], options: InspectOptions) => {
      const reports = await inspect(paths, options);
      process.stdout.write(options.json ? renderInspectJson(reports) : renderInspectMarkdown(reports));
    });
}

export async function inspect(paths: string[], options: InspectOptions = {}): Promise<InspectReport[]> {
  const profile = getProfileFromString(options.profile ?? "agent-skills");
  const targets = await discoverSkills(paths);
  const reports: InspectReport[] = [];

  for (const target of targets) {
    const validation = await validateSkill(target);
    const missingReferences = validation.issues
      .filter((issue) => issue.id === "missing-reference")
      .map((issue) => issue.message);
    const staticScore = scoreStaticSkill({
      name: validation.frontmatter.name,
      description: validation.frontmatter.description,
      body: validation.body,
      missingReferences,
      profile,
    });

    reports.push({
      target,
      gate: {
        status: validation.status,
        issues: validation.issues,
      },
      staticScore: {
        total: staticScore.total,
        profile: profile.name,
        dimensions: staticScore.dimensions,
      },
    });
  }

  return reports;
}
