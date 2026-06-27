# 调用次数怎么算进判断

`usage.json` 给每条 skill 四个数字：`calls_total`（历史确认调用总数）、`calls_30d`（最近 30 天调用数）、`sessions`（出现在多少个会话里）、`last_used_iso`（最后一次时间）。这份文档说明怎么用这些数字辅助判断，**不要让数字单独决定 archive/keep**。

## 两个数字各代表什么

- **`calls_30d`** 是行为新鲜度。它告诉你「这 skill 现在还在被用」。
- **`calls_total`** 是历史承重。一个长期累计调用数高的 skill，即使近期为零，也可能只是某段工作周期结束了。

## 「0 调用」不直接等于建议清理

要看 description 是否清晰：

| description 状态 | 30 天 0 调用怎么看 |
|---|---|
| 清晰、定位明确 | 更可能是「真不需要」。如果同时和别的 skill 高度重叠，考虑 archive；否则可以 keep（待用） |
| 不清不楚 / 太短 / 全是宽泛词 | 更可能是 「agent 想不到要用它」 —— 走 rewrite 让 description 写明白，给它一次被发现的机会 |

`calls_total > 0` 但 `calls_30d == 0`：报告里标 review，不要直接推 archive 候选。

## 「确认使用」口径偏保守

我们只统计两种行为算「使用」：
- Read 工具调用且 `file_path` 命中该 skill 的 `skill_md_path`
- Skill 工具调用且 `input.skill`（去掉 `<plugin>:` 前缀后）命中该 skill 的 name

这意味着会**低估**：
- agent 只读了 description（没读完整 SKILL.md）就完成了任务
- agent 通过另一种间接路径用了这个 skill（比如调用了 skill 提供的 CLI 脚本，但没 Read 过 SKILL.md）

所以 0 调用不是铁证。如果一个 skill 描述清晰、最近 30 天 0 调用，但你直觉它本来就该用 —— 可能是统计漏了，先 keep 一轮看看。

## 频率 + 质量的组合判断

判断时把这两个维度同时摆出来：

```
              description 清晰         description 不清
calls > 0     keep（继续用）           rewrite（写清楚让它更好被发现）
calls = 0     可考虑 archive           优先 rewrite，给它机会
```

报告里给建议时记得引这张图的逻辑，让用户能跟着思路审。
