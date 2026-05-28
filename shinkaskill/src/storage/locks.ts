import { open, readFile, rm } from "node:fs/promises";

export async function withApplyLock<T>(lockPath: string, work: () => Promise<T>): Promise<T> {
  const handle = await openApplyLock(lockPath);

  try {
    await handle.writeFile(`${process.pid}\n`);
    return await work();
  } finally {
    await handle.close();
    await rm(lockPath, { force: true });
  }
}

async function openApplyLock(lockPath: string) {
  try {
    return await open(lockPath, "wx");
  } catch (error) {
    if (isNodeError(error) && error.code === "EEXIST") {
      if (await removeStaleLock(lockPath)) {
        return open(lockPath, "wx");
      }
      throw new Error(`已有 apply 锁：${lockPath}。请确认没有其他写回流程正在运行。`);
    }
    throw error;
  }
}

async function removeStaleLock(lockPath: string): Promise<boolean> {
  const pid = await readLockPid(lockPath);
  if (pid === undefined || isProcessAlive(pid)) return false;
  await rm(lockPath, { force: true });
  return true;
}

async function readLockPid(lockPath: string): Promise<number | undefined> {
  try {
    const raw = await readFile(lockPath, "utf8");
    const pid = Number(raw.trim());
    return Number.isSafeInteger(pid) && pid > 0 ? pid : undefined;
  } catch {
    return undefined;
  }
}

function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (isNodeError(error) && error.code === "ESRCH") return false;
    return true;
  }
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && "code" in error;
}
