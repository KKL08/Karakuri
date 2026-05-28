import { Command } from "commander";

type ProposeOptions = {
  verifyPatch?: boolean;
};

export function registerProposeCommand(program: Command): void {
  program
    .command("propose")
    .argument("[paths...]", "skill 路径")
    .option("--verify-patch", "预留参数：当前不会运行 candidate eval")
    .description("进入 propose guard；当前不会生成 patch")
    .action(async (_paths: string[], options: ProposeOptions) => {
      process.stdout.write("propose CLI 写入流程尚未接入，本次不会生成 patch；candidate eval 需要显式传入 --verify-patch。\n");
      if (options.verifyPatch) {
        process.stdout.write("已收到 --verify-patch，但真实 candidate eval 流程还没接入；本次不会声称已经运行。\n");
      }
    });
}
