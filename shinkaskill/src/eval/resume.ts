import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { isRunStatus } from "./sandbox.js";

export type ResumeDecision =
  | { action: "resume"; reason: string }
  | { action: "restart"; reason: string };

export async function decideResume(runDir: string): Promise<ResumeDecision> {
  try {
    const manifest = JSON.parse(await readFile(join(runDir, "manifest.json"), "utf8"));
    if (typeof manifest.id !== "string") {
      return { action: "restart", reason: "manifest id 必须是字符串" };
    }
    if (typeof manifest.status !== "string") {
      return { action: "restart", reason: "manifest status 必须是字符串" };
    }
    if (!isRunStatus(manifest.status)) {
      return { action: "restart", reason: `manifest status 无效: ${manifest.status}` };
    }
    if (manifest.status === "completed" || manifest.status === "applied") {
      return { action: "restart", reason: "run 已完成，不重复 resume" };
    }
    return { action: "resume", reason: `run 状态为 ${manifest.status}` };
  } catch {
    return { action: "restart", reason: "manifest 不可读取" };
  }
}
