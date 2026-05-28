import type { Locale } from "./types.js";

type MessageKey =
  | "inspect.summaryTitle"
  | "gate.missingSkillFile"
  | "gate.invalidFrontmatter"
  | "gate.pass"
  | "gate.warn"
  | "gate.fail"
  | "report.nextSteps"
  | "eval.unavailable";

const zhCN: Record<MessageKey, string> = {
  "inspect.summaryTitle": "检查总览",
  "gate.missingSkillFile": "缺少 SKILL.md：{path}",
  "gate.invalidFrontmatter": "frontmatter YAML 无效：{reason}",
  "gate.pass": "通过",
  "gate.warn": "警告",
  "gate.fail": "失败",
  "report.nextSteps": "下一步建议",
  "eval.unavailable": "当前 runtime 不支持隔离 subagent eval，未运行真实 eval。",
};

const enUS: Record<MessageKey, string> = {
  "inspect.summaryTitle": "Inspection Summary",
  "gate.missingSkillFile": "Missing SKILL.md: {path}",
  "gate.invalidFrontmatter": "Invalid frontmatter YAML: {reason}",
  "gate.pass": "pass",
  "gate.warn": "warn",
  "gate.fail": "fail",
  "report.nextSteps": "Next steps",
  "eval.unavailable": "The current runtime does not support isolated subagent eval. Real eval was not run.",
};

const catalogs: Record<Locale, Record<MessageKey, string>> = {
  "zh-CN": zhCN,
  "en-US": enUS,
};

export function msg(
  key: MessageKey,
  values: Record<string, string | number> = {},
  locale: Locale = "zh-CN",
): string {
  const template = catalogs[locale][key];
  return template.replace(/\{([^}]+)\}/g, (_, name: string) => String(values[name] ?? `{${name}}`));
}
