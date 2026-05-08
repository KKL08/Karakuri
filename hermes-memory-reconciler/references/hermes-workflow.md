# Hermes 工作流

这个文件记录 Hermes 记忆扫描检查时的文件范围、CLI 约定和只读检查方式。

## 默认文件

```txt
${HERMES_HOME:-$HOME/.hermes}/memories/USER.md
${HERMES_HOME:-$HOME/.hermes}/memories/MEMORY.md
```

默认 profile 通常解析到 `~/.hermes/memories/`。如果用户正在使用 Hermes profile、Docker/custom deployment，或显式设置了 `HERMES_HOME`，必须以当前 `HERMES_HOME` 为准。

`USER.md` 更敏感，因为它通常描述用户是谁、喜欢什么、长期怎么被服务。

`MEMORY.md` 更偏项目和任务记忆，但如果里面出现用户偏好、身份、长期指令，也要按高风险处理。

## 先确认文件存在

```bash
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
ls -ld "$hermes_home" "$hermes_home/memories"
ls -l "$hermes_home/memories/USER.md" "$hermes_home/memories/MEMORY.md"
```

如果 `$hermes_home` 整个不存在，早退并提示用户确认 `HERMES_HOME` 或 Hermes 是否安装。不要把这种情况降级成“两份文件都缺失”继续扫描检查。

如果根目录存在但单个文件不存在，不要声称已完成完整扫描检查。告诉用户缺了哪个文件，并说明只能检查实际存在的部分。

## CLI 路径

CLI 可用时优先走：

```bash
memory-reconciler scan --system hermes --read-only
memory-reconciler report <scan_id> --limit 5 --severity low
memory-reconciler next-question <scan_id>
memory-reconciler resolve <conflict_id> --decision <decision_id> --note "<user note>"
memory-reconciler plan <resolution_id>
memory-reconciler preview <plan_id>
memory-reconciler stage <plan_id>
memory-reconciler preview <run_id>
memory-reconciler apply <run_id>
memory-reconciler rollback <run_id> --dry-run
```

scan 输出可以包含这些字段：

```json
{
  "scan_id": "scan_20260509_001",
  "system": "hermes",
  "files_scanned": 2,
  "entries": 42,
  "issues": 8,
  "needs_user": 3,
  "summary_path": "~/.memory-reconciler/scans/scan_20260509_001.json"
}
```

不要自己发明这些字段。只有 CLI 返回了，才可以引用。

## ID 契约

CLI 可以返回更多字段，但每一步必须能让 agent 找到下一步需要的 ID：

```txt
scan                         -> scan_id
report <scan_id>             -> conflict_id 列表
next-question <scan_id>      -> conflict_id + decision_id 选项
resolve <conflict_id>        -> resolution_id
plan <resolution_id>         -> plan_id
preview <plan_id>            -> 不产生新 ID
stage <plan_id>              -> run_id
preview <run_id>             -> 不产生新 ID
apply <run_id>               -> run_id 状态变 applied
rollback <run_id>            -> run_id 状态变 rolled_back
```

字段名以 CLI 实际输出为准。若只是字段名不同，但语义仍能唯一对应契约，agent 可以内部适配；若字段语义偏离契约，例如 `scan_id` 不能唯一定位扫描结果，或 `run_id` 实际指向 plan，必须先停下并告诉用户，不要硬走后续流程。

## CLI 不可用时

告诉用户 CLI 不可用，并继续做不依赖 CLI 的只读检查。

推荐命令：

```bash
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
ls -ld "$hermes_home" "$hermes_home/memories"
nl -ba "$hermes_home/memories/USER.md"
nl -ba "$hermes_home/memories/MEMORY.md"
```

文件较大时分段读取：

```bash
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
sed -n '1,160p' "$hermes_home/memories/USER.md"
sed -n '1,220p' "$hermes_home/memories/MEMORY.md"
```

只读检查期间不要使用：

```txt
>
>>
sed -i
perl -pi
truncate
mv 覆盖源文件
直接编辑 USER.md / MEMORY.md
```

## Action plan

默认输出 Hermes memory actions：

```json
[
  {
    "action": "replace",
    "target": "user",
    "old_text": "用户喜欢简短回答。",
    "content": "用户默认喜欢简洁回答；涉及复杂工程、产品判断或方案取舍时，希望看到推理过程。"
  },
  {
    "action": "remove",
    "target": "user",
    "old_text": "用户总是要非常详细的回答。"
  }
]
```

`target=user` 对应 `USER.md`。`target=memory` 对应 `MEMORY.md`。

## Staged files

需要生成候选文件时，优先让 CLI 处理：

```bash
memory-reconciler stage <plan_id>
```

`stage` 必须返回 `run_id`。从这个点开始，apply、rollback 和 staged run preview 都围绕 `run_id`，不要继续用 `plan_id` 表示已落盘的 run。

预期目录：

```txt
~/.memory-reconciler/runs/run_YYYYMMDD_NNN/
├── original/
├── proposed/
├── diffs/
├── plan.json
├── manifest.json
└── apply-log.jsonl
```

staged 后必须告诉用户：Hermes 源文件还没有被修改。

## Rollback

已 apply 的 run 回滚前必须预览：

```bash
memory-reconciler rollback <run_id> --dry-run
```

`preview <run_id>` 用来看这个 run 的正向变更；`rollback <run_id> --dry-run` 用来看回滚这个 run 的反向变更。用户问“回滚会怎样”时，必须先用 rollback dry-run；只有需要回看当初应用了什么时，才额外使用 `preview <run_id>`。

用户明确批准后才执行：

```bash
memory-reconciler rollback <run_id>
```

如果 run 只是 `staged`，不需要 rollback。说明源文件没变，丢弃 run 即可。
