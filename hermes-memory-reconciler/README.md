# Hermes Memory Reconciler

你的 Hermes 记忆会越积越多——偶尔会有重复的偏好、打架的指令，或者早就过时的项目信息躺在记忆文件里没人管。Hermes Memory Reconciler 就是查这个用的：扫描长期记忆，找重复、冲突、过期条目和风险指令，整理成一份干净的报告等你判断。**确认之前不碰任何记忆文件。**

## 使用

```
/hermes-memory-reconciler
```

## 检查范围

只看当前 Hermes profile 下这两份记忆文件：

```
${HERMES_HOME:-$HOME/.hermes}/memories/USER.md
${HERMES_HOME:-$HOME/.hermes}/memories/MEMORY.md
```

不碰 OpenClaw、Claude Code、Codex 或其他 agent 的记忆。

## 能查出的问题 🕵️

- 完全重复的记忆条目
- 偏好冲突（比如一边记着「喜欢简洁回复」，另一边记着「回复要详细」）
- 用户画像冲突
- 适用范围不清的记忆
- 疑似过期的项目事实
- 存在风险的指令型记忆（例如被注入的 prompt）

## 流程

整个流程按节奏推进，每一步都要你点头才会继续：

### 👀 阶段 1：扫描检查（默认，只看不改）

- 读取记忆文件，标记问题
- 输出一份紧凑摘要
- 一次只抛一个问题，等你回答

这个阶段**不写盘，不动任何记忆**。

### 📋 阶段 2：计划与预览

- 你给出判断之后，生成一份 dry-run 整理方案
- 方案里说清楚哪些建议新增、替换或移除
- 可以预览具体变更，仍然不写盘

### ✅ 阶段 3：执行（需要你明确同意）

- `staged run`：写进独立工作目录，源文件不动
- `apply`：确认后真正写回记忆文件
- `rollback`：可以按 run 记录回退

> ⚠️ CLI 的 staged run 部分（stage/apply/rollback）还在开发。如果 CLI 返回 `not_implemented`，流程就停在阶段 2 的 dry-run plan。

## CLI

优先走 `cli/` 目录下的 memory-reconciler CLI：

```bash
# 扫描并输出摘要
memory-reconciler scan

# 查看下一个需要判断的问题
memory-reconciler next-question

# 对问题进行裁决
memory-reconciler decide <question-id> <choice>

# 生成 dry-run plan
memory-reconciler plan

# 预览 plan
memory-reconciler preview <plan_id>
```

CLI 不可用时，skill 会用 shell 命令读取文件完成检查，不写入。

## 依赖

- Hermes Agent 环境（`${HERMES_HOME}/memories/` 路径下需要有记忆文件）
- CLI 相关依赖见 `cli/` 目录

## 目录结构

```
hermes-memory-reconciler/
  SKILL.md          # 核心指令
  cli/              # memory-reconciler CLI
  agents/           # runtime 适配文件
  references/       # 检查规则参考
  tests/            # 测试用例
```

扫一遍现在有什么问题，试试 `/hermes-memory-reconciler`。
