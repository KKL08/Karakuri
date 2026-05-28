import { Command } from "commander";

type ApplyOptions = {
  yes?: boolean;
  commit?: boolean;
};

export function registerApplyCommand(program: Command): void {
  program
    .command("apply")
    .argument("<run-id>", "要应用的 run id")
    .option("--yes", "进入 apply guard 的显式确认；当前不会真实写回")
    .option("--commit", "预留参数：当前不会创建 commit")
    .description("进入 apply guard；当前不会真实写回")
    .action(async (runId: string, options: ApplyOptions) => {
      if (!options.yes) {
        process.stdout.write("apply 需要显式确认。请重新运行并传入 --yes，或在 Agent 模式中确认。\n");
        return;
      }

      process.stdout.write(`准备应用 run：${runId}\n`);
      if (options.commit) {
        process.stdout.write("已收到 --commit 预留参数；当前不会创建 commit。\n");
      }
      process.stdout.write("当前 run 读取和最终确认流程还没接入，本次不会真的写回原始 skill。\n");
    });
}
