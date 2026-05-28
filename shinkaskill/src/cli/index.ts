#!/usr/bin/env node
import { Command } from "commander";
import { registerApplyCommand } from "./commands/apply.js";
import { registerCleanCommand } from "./commands/clean.js";
import { registerEvalCommand } from "./commands/eval.js";
import { registerInspectCommand } from "./commands/inspect.js";
import { registerProposeCommand } from "./commands/propose.js";

const program = new Command();

program
  .name("shinka")
  .description("中文优先的 Agent Skill 检查与优化辅助工具")
  .version("0.1.0");

registerInspectCommand(program);
registerEvalCommand(program);
registerProposeCommand(program);
registerApplyCommand(program);
registerCleanCommand(program);

try {
  await program.parseAsync(process.argv);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Error: ${message}`);
  process.exitCode = 1;
}
