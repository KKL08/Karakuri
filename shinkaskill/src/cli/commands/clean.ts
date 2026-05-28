import { Command } from "commander";
import { join } from "node:path";
import { executeCleanup, parseKeepLast, parseOlderThan, planCleanup } from "../../storage/cleanup.js";

export function registerCleanCommand(program: Command): void {
  program
    .command("clean")
    .option("--keep-last <count>", "保留最近 N 个 run", "10")
    .option("--older-than <duration>", "只删除早于指定时间的 run，例如 30d")
    .option("--dry-run", "只展示将删除的 run")
    .description("清理 .shinka/runs 历史记录")
    .action(async (options: { keepLast: string; olderThan?: string; dryRun?: boolean }) => {
      const keepLast = parseKeepLast(options.keepLast);
      const olderThanMs = options.olderThan ? parseOlderThan(options.olderThan) : undefined;
      const runsDir = join(process.cwd(), ".shinka", "runs");
      const plan = await planCleanup({ runsDir, keepLast, olderThanMs });
      if (options.dryRun) {
        process.stdout.write(`dry-run：将删除 ${plan.deleteRunDirs.length} 个 run\n`);
        return;
      }
      await executeCleanup(plan);
      process.stdout.write(`已删除 ${plan.deleteRunDirs.length} 个 run\n`);
    });
}
