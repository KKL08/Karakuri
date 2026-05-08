# Reconciliation Run 生命周期

只要流程进入候选文件、真实应用或回滚，就必须使用 reconciliation run。它让每次记忆整理都有记录、有快照、能预览、能撤回。

## 状态

```txt
planned -> staged -> applied -> rolled_back
```

- `planned`：已有整理计划和 `plan_id`，但没有 run 目录，也没有写候选文件。
- `staged`：`stage <plan_id>` 已生成 `run_id`、原始快照和候选文件；Hermes 源文件还没改。
- `applied`：用户明确批准后，`run_id` 对应的修改已经应用。
- `rolled_back`：同一个 `run_id` 已经恢复原内容，或已生成并执行反向操作。

`plan_id` 属于计划阶段。`run_id` 属于 staged run 阶段。真实 apply 和 rollback 都必须使用 `run_id`，不要对 `plan_id` 执行真实写入。

## 目录

```txt
~/.memory-reconciler/runs/run_YYYYMMDD_NNN/
├── original/
│   ├── USER.md
│   └── MEMORY.md
├── proposed/
│   ├── USER.md
│   └── MEMORY.md
├── diffs/
│   ├── USER.diff
│   └── MEMORY.diff
├── plan.json
├── manifest.json
└── apply-log.jsonl
```

`manifest.json` 至少要记录：

```json
{
  "run_id": "run_20260509_001",
  "system": "hermes",
  "state": "staged",
  "created_at": "2026-05-09T10:00:00+08:00",
  "source_files": [
    "${HERMES_HOME:-$HOME/.hermes}/memories/USER.md",
    "${HERMES_HOME:-$HOME/.hermes}/memories/MEMORY.md"
  ],
  "plan_id": "plan_001",
  "apply_mode": "not_applied"
}
```

`plan_id` 在 manifest 里只是历史外键，用来追溯这个 run 来自哪个计划。`run_id` 才是 apply、rollback、扫描检查和清理 staged artifacts 时使用的主 ID。

## Staging 规则

真实 apply 前先 staged。

可以说：

```txt
我已经生成候选文件，原来的 Hermes 记忆还没有改。你可以先看 proposed/ 和 diffs/，再决定要不要应用。
```

不要说：

```txt
我先直接改了，不满意再恢复。
```

如果 CLI 还不支持 `stage`，就停在 dry-run plan。不要手动伪造 run 目录、run ID 或 `manifest.json`。

如果用户在 `planned` 阶段反悔，丢弃 plan 即可。如果用户在 `staged` 阶段反悔，说明 Hermes 源文件未改，丢弃或忽略 run 目录即可。

## Apply 规则

只有同时满足这些条件，才允许真实 apply：

1. 用户明确批准。
2. 已有 `run_id`。
3. 已有 `original/` 快照。
4. 已有 `manifest.json`。
5. 已展示 dry-run preview。
6. 高风险修改已有用户裁决。

能用 Hermes memory tool actions 时，优先用 action 语义。直接覆盖 `USER.md` 或 `MEMORY.md` 前，必须说明这会绕过 Hermes memory tool 的保护。

## Rollback 规则

rollback 必须先 dry-run：

```bash
memory-reconciler rollback <run_id> --dry-run
```

`preview <run_id>` 是正向预览，用来看 staged 或 applied run 的原始变更；`rollback <run_id> --dry-run` 是反向预览，用来看回滚会改什么。回滚前不能用 `preview <run_id>` 替代 rollback dry-run。

用户批准后才执行：

```bash
memory-reconciler rollback <run_id>
```

两种可接受模式：

- Snapshot restore：恢复 `original/USER.md` 和 `original/MEMORY.md`。
- Inverse actions：生成反向 Hermes memory actions。

执行前告诉用户当前用哪种模式。run 只是 `staged` 时，不需要 rollback，因为源文件没改。
