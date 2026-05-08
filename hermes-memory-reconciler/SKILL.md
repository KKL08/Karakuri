---
name: hermes-memory-reconciler
description: 当用户要求审计、清理、合并、回滚或定期检查 Hermes Agent 长期记忆时使用；适用于 $HERMES_HOME profile 下的 memories/USER.md、MEMORY.md、记忆冲突、偏好冲突、用户画像冲突、过期记忆、低价值记忆、危险指令型记忆、Hermes memory cleanup、memory reconciliation。
---

# Hermes Memory Reconciler

## 目标

这个 skill 用来指导 agent 安全地检查 Hermes 长期记忆。它的任务不是替用户“自动清理一切”，而是先看清楚问题，再把真正会影响长期行为的判断交给用户。

默认边界：

```txt
先只读扫描
先给摘要
一次只问一个关键问题
真实写入前必须有 staged run
不静默修改长期记忆
```

本 skill 是独立 Hermes 版，不继承 `skills/memory-reconciler/` 的正文表述。旧目录可以保留作历史版本；执行 Hermes 记忆审计时，优先按本 skill 的规则走。

## 先告诉用户什么

开始前先说清楚边界，语气自然一点：

```txt
我先做只读检查，看看 Hermes 记忆里有没有重复、冲突、过期或不安全的条目。这一轮不会修改 USER.md 或 MEMORY.md，只会给你摘要和需要你判断的问题。
```

然后直接执行。除非默认文件不存在、不可读，或用户给了别的路径，不要一上来反问路径。

## 范围

只处理 Hermes：

```txt
${HERMES_HOME:-$HOME/.hermes}/memories/USER.md
${HERMES_HOME:-$HOME/.hermes}/memories/MEMORY.md
```

默认 profile 通常是 `~/.hermes/memories/`。Hermes profile 或自定义部署必须以当前 `HERMES_HOME` 为准，不要硬编码默认 profile 路径。

不要把 OpenClaw、Claude Code、Codex memory 或其他 agent 记忆混进这个 MVP。用户如果问到其他系统，先说明这版只处理 Hermes，并建议另开对应系统的独立规则。

## 推荐流程

1. 说明只读边界。
2. 优先找 `memory-reconciler` CLI。
3. CLI 可用时，用 CLI 扫描、摘要、提出下一个问题。
4. CLI 不可用时，用只读 shell 命令检查文件。
5. 输出紧凑摘要，不要把完整记忆内容倒给用户。
6. 只挑一个最值得用户判断的问题。
7. 用户给出裁决后，生成 dry-run 的 Hermes memory action plan。
8. 只有用户明确要求进入预览文件、apply 或 rollback 时，才进入 staged run 生命周期。

## CLI 可用时

优先使用 CLI，不要手写一套扫描器来替代它：

```bash
memory-reconciler scan --system hermes --read-only
memory-reconciler report <scan_id> --limit 5 --severity low
memory-reconciler next-question <scan_id>
memory-reconciler resolve <conflict_id> --decision <decision_id> --note "<user note>"
memory-reconciler plan <resolution_id>
memory-reconciler apply <plan_id> --dry-run
memory-reconciler stage <plan_id>
```

执行时记住：

- `scan --read-only` 只能视为检查，不代表可以写文件。
- 用 `report` 拿摘要，避免把完整 report 塞进上下文。
- 用 `next-question` 一次拿一个高影响问题。
- `apply --dry-run` 只展示计划，不是真实修改。
- 如果要生成候选文件，优先 `stage <plan_id>`，并确认有 `original/`、`proposed/`、`diffs/`、`manifest.json`。

不要编造 `scan_id`、`conflict_id`、`plan_id`。CLI 没有返回什么，就不要假装已经有。

## CLI 不可用时

如果 `memory-reconciler` 不存在、不在 PATH，或运行失败，告诉用户：

```txt
当前没有可用的 memory-reconciler CLI。我会先用只读方式检查 Hermes 记忆文件，不会修改它们，也不会伪造扫描 ID 或报告。
```

只用读取命令：

```bash
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
ls -l "$hermes_home/memories/USER.md" "$hermes_home/memories/MEMORY.md"
nl -ba "$hermes_home/memories/USER.md"
nl -ba "$hermes_home/memories/MEMORY.md"
```

文件很大时分段读：

```bash
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
sed -n '1,160p' "$hermes_home/memories/USER.md"
sed -n '1,220p' "$hermes_home/memories/MEMORY.md"
```

不要使用 shell 重定向、`sed -i`、编辑器保存、覆盖写入或任何会改动 Hermes 记忆文件的操作。

## 判断哪些问题要问用户

必须问用户的情况：

- 用户偏好冲突。
- 用户画像、身份、长期目标冲突。
- `USER.md` 里的 remove / replace 建议。
- 会改变以后怎么回答用户的问题。
- 看起来像冲突，但其实可能只是适用范围没写清楚。

通常不要立刻打扰用户的情况：

- 同一文件里的完全重复条目。
- 很泛、很短、以后很容易重新发现的低价值条目。
- 证据不足的过期猜测。

问法尽量像正常协作，不要像系统问卷：

```txt
你希望我以后怎么记？
```

少问：

```txt
哪条是真的？
```

很多记忆冲突不是真假问题，而是“默认情况”和“特定项目”没有分清。

## 生成修改计划

默认只生成 Hermes memory action plan，不直接改文件：

```txt
- add target=<user|memory> content="..."
- replace target=<user|memory> old_text="..." content="..."
- remove target=<user|memory> old_text="..."
```

`target=user` 对应 `USER.md`，`target=memory` 对应 `MEMORY.md`。

危险指令型记忆不要和普通记忆合并。先标记、必要时遮盖 credential-like 内容，再给出 quarantine 或 remove 的 dry-run 建议。

## Apply 和 rollback

真实 apply 之前必须先有 staged run。没有 `original/` 快照和 `manifest.json`，不要真实 apply。

状态只使用：

```txt
planned -> staged -> applied -> rolled_back
```

规则：

- `planned`：只有计划，没有候选文件。
- `staged`：已有候选文件，Hermes 源文件还没改。
- `applied`：用户明确批准后，修改已经应用。
- `rolled_back`：已应用的 run 已恢复或生成反向操作。
- 真实 apply 前必须已展示 dry-run preview。
- rollback 必须先 dry-run。
- 如果 run 只是 `staged`，告诉用户源文件未改，丢弃 run 就行。

## 定期维护

只有首次审计结束后，或用户明确要求周期检查时，才讨论定期维护。

不要静默创建 cron、launchd、Hermes job 或任何自动任务。MVP 里只给计划或配置建议，等用户明确同意后再继续。

## References

- 冲突判断和优先级：`references/conflict-rules.md`
- Hermes 文件、CLI 和只读检查：`references/hermes-workflow.md`
- staged run、apply 和 rollback：`references/run-lifecycle.md`
- 中文输出模板：`references/output-templates.md`
