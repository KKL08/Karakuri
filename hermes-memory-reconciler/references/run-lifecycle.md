# Reconciliation Run 生命周期

只要流程进入候选文件、真实应用或回滚，就必须使用 reconciliation run。它让每次记忆整理都有记录、有快照、能预览、能撤回。

## 状态

```txt
planned -> staged -> applied -> rolled_back
```

- `planned`：已有整理计划，但没有写候选文件。
- `staged`：已有原始快照和候选文件；Hermes 源文件还没改。
- `applied`：用户明确批准后，修改已经应用。
- `rolled_back`：已经恢复原内容，或已生成并执行反向操作。

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

## Apply 规则

只有同时满足这些条件，才允许真实 apply：

1. 用户明确批准。
2. 已有 `original/` 快照。
3. 已有 `manifest.json`。
4. 已展示 dry-run preview。
5. 高风险修改已有用户裁决。

能用 Hermes memory tool actions 时，优先用 action 语义。直接覆盖 `USER.md` 或 `MEMORY.md` 前，必须说明这会绕过 Hermes memory tool 的保护。

## Rollback 规则

rollback 必须先 dry-run：

```bash
memory-reconciler rollback <run_id> --dry-run
```

用户批准后才执行：

```bash
memory-reconciler rollback <run_id>
```

两种可接受模式：

- Snapshot restore：恢复 `original/USER.md` 和 `original/MEMORY.md`。
- Inverse actions：生成反向 Hermes memory actions。

执行前告诉用户当前用哪种模式。run 只是 `staged` 时，不需要 rollback，因为源文件没改。
