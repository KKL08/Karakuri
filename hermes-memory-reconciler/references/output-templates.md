# 输出模板

这些模板用于保持中文表达自然、清楚、低打扰。可以按实际情况压缩，不要机械照抄。

## 开场

```txt
我先检查 Hermes 记忆里有没有重复、冲突、过期或不安全的条目。这一阶段不会修改 USER.md 或 MEMORY.md，也不会写入 staged run，只会给你摘要和需要你判断的问题。
```

## CLI 不可用

```txt
当前没有可用的 memory-reconciler CLI。我会先用只读方式检查 Hermes 记忆文件，不会修改它们，也不会伪造扫描 ID 或报告。
```

## 扫描摘要

```txt
只读检查完成：

- USER.md: <found|missing|skipped>
- MEMORY.md: <found|missing|skipped>

没有修改 Hermes 源记忆文件。

我看到 <N> 个可能问题：
- <X> 个重复条目
- <Y> 个需要你判断的偏好或画像冲突
- <Z> 个低价值条目候选
- <W> 个疑似不安全记忆

我建议先处理这个问题：<brief>。
```

## 单个冲突问题

```txt
我发现一条关于 <topic> 的记忆冲突。

一条写的是：
"<memory A>"

另一条写的是：
"<memory B>"

它会影响以后怎么回答你，因为 <reason>。

你希望我以后怎么记？
1. <choice A>
2. <choice B>
3. <choice C>
4. 暂时不改
```

## Dry-run action plan

```txt
我建议整理成：
"<proposed memory>"

Hermes memory action plan:
- replace target=<user|memory> old_text="<old>" content="<new>"
- remove target=<user|memory> old_text="<old>"

这只是 dry-run，还没有修改 Hermes 源记忆文件。
```

## Staged run

```txt
我已经在独立工作目录写好候选文件，没有改你的 Hermes 源记忆。

staged run：

- run_id: <run_id>
- original/: 原始记忆快照
- proposed/: 候选整理结果
- diffs/: 差异
- manifest.json: 本次整理记录

Hermes 源文件还没有被修改。你可以先看 proposed/ 和 diffs/，再决定要不要应用。
```

## Apply 前确认

```txt
应用前我会先确认几件事：

- 有 original/ 快照
- 有 manifest.json
- 已展示 dry-run preview
- 高风险修改已经由你判断过

这些都满足后，才继续 apply。
```

## Rollback 预览

```txt
我会先预览 rollback，不会直接覆盖当前记忆。

预计会恢复或反向处理：
- USER.md: <summary>
- MEMORY.md: <summary>

确认后才执行 rollback。
```

## 定期维护询问

```txt
以后要不要定期做一次 Hermes 记忆健康检查？

它只会扫描并给摘要，不会自动修改。只有发现高风险冲突、不安全记忆，或者需要你判断的长期偏好冲突时，才提醒你。

1. 每周一次
2. 每月一次
3. 先不开启
```
