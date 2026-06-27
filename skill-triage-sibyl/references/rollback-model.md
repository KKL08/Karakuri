# 快照与冲突检测语义

回退分两层：keeper 负责「还原快照里的内容」，apply 负责「判断这个还原现在做安不安全」。这一篇说明每层的语义和冲突检测的边界。

## 快照存放在哪

`$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/keeper/repo/` 是一个独立的 git 仓库，每次 snap 创建一个 commit。文件以绝对路径编码后存入：leading `/` 替换成 `_root_/` 目录名，避免不同源路径在仓库内撞名。

每条 run 还有 `$CLAUDE_PLUGIN_DATA/skill-triage-sibyl/runs/<run-id>/actions.jsonl`，按时间顺序记录所有 archive / rewrite 动作。rollback 倒序读这个日志。

## rewrite 的回退：内容哈希一致性

rewrite 流程：

1. keeper.snap 原 SKILL.md → 拿到 `pre_commit`
2. 写新内容
3. 记录 `post_content_hash = sha256(new_content)`

rollback 时：

1. 读当前 SKILL.md 内容 → 算 `current_hash`
2. 比较 `current_hash` 和 `post_content_hash`
   - **一致** → 说明我们写入后没人动过，安全 restore：keeper.restore(pre_commit, force=True)
   - **不一致** → 用户（或别的进程）手动改过文件，conflict
3. conflict 默认拒绝覆盖；`--force` 才覆盖

为什么不直接用 keeper 自带的 mtime 检测？因为我们的顺序是 `snap → 写`，commit 时间戳早于文件 mtime，mtime 检测会误报「被修改过」。hash 检测才符合「我们写入的内容是否仍完整」这个真实判断。

## archive 的回退：原路径必须空

archive 流程：mv skill 目录到 archive 区。

rollback 时：

1. 检查原路径 (`original_path`) 是否被占用
   - **空** → mv 归档物回原位，清掉 `_sibyl_origin.json`
   - **被占用** → conflict（默认）；`--force` 时把占用物移到 `<original>.sibyl-conflict` 后缀，再把归档物 mv 回原位

如果归档物本身丢了（被用户手动删除等），记为 skipped。

## --force 的语义边界

`--force` 是「我已经知道有冲突，仍然按 rollback 意图执行」的明示。具体行为：

- rewrite + force：哪怕 hash 不一致，也用 pre_commit 的内容覆盖当前文件
- archive + force：把原路径上的占用物搬到 `.sibyl-conflict` 后缀保留，再把归档物搬回原位

force 不静默丢数据 —— archive 冲突时占用物总是留一份 backup 而不是直接覆盖。

## 不会回退什么

- 偏好（`preferences.json`）：偏好不参与 rollback。回退某次 run 的物理动作不会影响「用户上次怎么选」这个事实记录。
- 报告（`runs/<run-id>/report.md`）：报告是历史产物，rollback 不删它。
- 自动巡检的 cron / automations 配置：rollback 不动调度配置，只动 skill 文件。

## 一次性回退多步

`rollback --run-id <id>` 一次回退一个 run 的全部动作（倒序）。如果中间有 conflict 也会继续处理其他动作，最后返回 `status: partial` + 列出 conflicts / undone / skipped 三类清单，让用户决定要不要 `--force` 重跑。
