# Recovery Model

Version 1 stores original snapshots and may optionally execute approved actions through a staged flow. Use 恢复, 回退, and 找回原始版本 in user-facing text.

## Backup Requirement

If `backup=off`, execution is blocked. Say:

"本次扫描没有保存执行所需备份。为了保证可恢复，建议使用 targeted 或 full backup 重新扫描后再进入整理执行流程。"

## Manual Recovery Text

When backup is targeted or full, name the snapshot path and original hash. When backup is off, say: "这次没有保存原始快照；如果你手动采用了草案，恢复需要依赖你自己的 git、备份或原始来源。"

## Applied Action Recovery Text

When actions were applied, say:

"本次执行保留了恢复材料。若之后想恢复，可以让当前 Agent 读取这个 run 目录并执行恢复流程。恢复前会再次检查目标路径和文件 hash；如果发现你后来又手动改过相关文件，SkillTriage 会停下来让你确认，而不是直接覆盖。"

Rollback may stop if a target path already exists, if a file changed after apply, if the run directory was deleted, or if permissions changed.
