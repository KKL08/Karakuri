#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { cp, mkdir, rm, writeFile, chmod } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";

const repoDir = dirname(fileURLToPath(import.meta.url));
const args = parseArgs(process.argv.slice(2));

if (args.help) {
  process.stdout.write(`Usage: node install.mjs [--codex-home DIR | --skills-dir DIR] [--force]

Installs the ShinkaSkill wrapper and a shinka launcher into an agent skills directory.

Options:
  --codex-home DIR  Install to DIR/skills/shinkaskill.
  --skills-dir DIR  Install directly to DIR/shinkaskill.
  --force           Replace an existing shinkaskill install.
  --help            Show this help.
`);
  process.exit(0);
}

const cliPath = join(repoDir, "dist", "cli", "index.js");
if (!existsSync(cliPath)) {
  process.stdout.write("ShinkaSkill CLI 尚未构建，正在运行 npm run build...\n");
  const build = spawnSync("npm", ["run", "build"], {
    cwd: repoDir,
    env: process.env,
    stdio: "inherit",
  });
  if (build.error || build.status !== 0) {
    fail("ShinkaSkill CLI 构建失败。请先确认已运行 npm install。");
  }
}

if (!existsSync(cliPath)) {
  fail("ShinkaSkill CLI 构建后仍不可用。请检查 dist/cli/index.js。");
}

const sourceSkillDir = repoDir;
if (!existsSync(join(sourceSkillDir, "SKILL.md"))) {
  fail(`找不到 skill wrapper：${sourceSkillDir}`);
}

const skillsDir = resolveSkillsDir(args);
const targetSkillDir = join(skillsDir, "shinkaskill");

if (existsSync(targetSkillDir)) {
  if (!args.force) {
    fail(`目标已存在：${targetSkillDir}\n如需覆盖，请加 --force。`);
  }
  await rm(targetSkillDir, { recursive: true, force: true });
}

await mkdir(skillsDir, { recursive: true });
await mkdir(targetSkillDir, { recursive: true });
await cp(join(sourceSkillDir, "SKILL.md"), join(targetSkillDir, "SKILL.md"));
await cp(join(sourceSkillDir, "references"), join(targetSkillDir, "references"), { recursive: true });
if (existsSync(join(sourceSkillDir, "README.md"))) {
  await cp(join(sourceSkillDir, "README.md"), join(targetSkillDir, "README.md"));
}
await mkdir(join(targetSkillDir, "scripts"), { recursive: true });

const installMeta = {
  sourceDir: repoDir,
  cliPath,
  installedAt: new Date().toISOString(),
  launcher: "scripts/shinka",
};

await writeFile(join(targetSkillDir, ".shinka-install.json"), `${JSON.stringify(installMeta, null, 2)}\n`);
await writeFile(join(targetSkillDir, "scripts", "shinka"), launcherSource(), { mode: 0o755 });
await chmod(join(targetSkillDir, "scripts", "shinka"), 0o755);

process.stdout.write(`ShinkaSkill 已安装：${targetSkillDir}
CLI 启动器：${join(targetSkillDir, "scripts", "shinka")}
下一步：重启或刷新 agent，让它重新读取 skill 列表。
`);

function parseArgs(values) {
  const parsed = {
    help: false,
    force: false,
    codexHome: undefined,
    skillsDir: undefined,
  };

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (value === "--help" || value === "-h") {
      parsed.help = true;
    } else if (value === "--force") {
      parsed.force = true;
    } else if (value === "--codex-home") {
      parsed.codexHome = requireValue(values, index, value);
      index += 1;
    } else if (value === "--skills-dir") {
      parsed.skillsDir = requireValue(values, index, value);
      index += 1;
    } else {
      fail(`未知参数：${value}`);
    }
  }

  if (parsed.codexHome && parsed.skillsDir) {
    fail("不能同时传入 --codex-home 和 --skills-dir。");
  }

  return parsed;
}

function requireValue(values, index, flag) {
  const next = values[index + 1];
  if (!next || next.startsWith("--")) {
    fail(`${flag} 需要一个路径参数。`);
  }
  return next;
}

function resolveSkillsDir(input) {
  if (input.skillsDir) return resolve(input.skillsDir);
  if (input.codexHome) return resolve(input.codexHome, "skills");
  if (process.env.CODEX_HOME) return resolve(process.env.CODEX_HOME, "skills");
  return resolve(homedir(), ".codex", "skills");
}

function launcherSource() {
  return `#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const skillDir = dirname(scriptsDir);
const metaPath = join(skillDir, ".shinka-install.json");

if (!existsSync(metaPath)) {
  console.error("ShinkaSkill CLI 不可用：缺少 .shinka-install.json。请重新运行 node install.mjs。");
  process.exit(1);
}

const meta = JSON.parse(readFileSync(metaPath, "utf8"));
if (!meta.cliPath || !existsSync(meta.cliPath)) {
  if (meta.sourceDir && existsSync(meta.sourceDir)) {
    console.error("ShinkaSkill CLI 不可用，正在尝试重新构建...");
    const build = spawnSync("npm", ["run", "build"], {
      cwd: meta.sourceDir,
      env: process.env,
      stdio: "inherit",
    });
    if (build.error || build.status !== 0) {
      console.error("ShinkaSkill CLI 构建失败。请回到源码目录运行 npm install && npm run build。");
      process.exit(1);
    }
  }
}

if (!meta.cliPath || !existsSync(meta.cliPath)) {
  if (meta.sourceDir && !existsSync(meta.sourceDir)) {
    console.error("ShinkaSkill CLI 不可用：源码目录可能已被移动或删除。请重新运行 node install.mjs。");
    process.exit(1);
  }
  console.error(\`ShinkaSkill CLI 不可用：\${meta.cliPath ?? "未记录 cliPath"}。请回到源码目录运行 npm install && npm run build，或重新运行 node install.mjs。\`);
  process.exit(1);
}

const result = spawnSync(process.execPath, [meta.cliPath, ...process.argv.slice(2)], {
  cwd: process.cwd(),
  env: process.env,
  stdio: "inherit",
});

if (result.error) {
  console.error(\`ShinkaSkill CLI 启动失败：\${result.error.message}\`);
  process.exit(1);
}

process.exit(result.status ?? 1);
`;
}

function fail(message) {
  process.stderr.write(`Error: ${message}\n`);
  process.exit(1);
}
