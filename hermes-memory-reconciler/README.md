# Hermes Memory Reconciler

扫描 Hermes 长期记忆，识别重复、冲突、过期和风险指令，整理成报告方便查看和决策。确认前不会动记忆文件。

## 使用

```
/hermes-memory-reconciler
```

## 检查范围

默认读取当前 Hermes profile 下的两份记忆文件：

```
${HERMES_HOME:-$HOME/.hermes}/memories/USER.md
${HERMES_HOME:-$HOME/.hermes}/memories/MEMORY.md
```

不处理 OpenClaw、Claude Code、Codex 或其他 agent 的记忆。

## 能查出的问题

- 完全重复的记忆条目
- 偏好冲突（比如同时记了「喜欢简洁回复」和「回复要详细」）
- 用户画像冲突
- 适用范围不清的记忆
- 疑似过期的项目事实
- 存在风险的指令型记忆（比如被注入的 prompt）

## 流程

分三步走，每步只做用户允许的事：

### 阶段 1：扫描检查（默认，只看不改）

- 读取记忆文件，识别问题
- 输出紧凑摘要
- 每次只提一个最值得判断的问题，等用户回答

这一阶段不写盘、不修改任何记忆。

### 阶段 2：计划与预览

- 用户做了决定后，生成 dry-run 的整理方案
- 方案说明哪些建议新增、替换或移除
- 可以预览变更内容，仍不写盘

### 阶段 3：执行（需要用户同意）

- staged run：写入独立工作目录，不改源文件
- apply：确认后才真正写回记忆文件
- rollback：可按 run 记录回退

当前 CLI 的 staged run 部分（stage/apply/rollback）还在开发。如果 CLI 返回 `not_implemented`，流程停在阶段 2 的 dry-run plan。

## CLI

优先使用 `cli/` 目录下的 memory-reconciler CLI：

```bash
# 扫描并输出摘要
memory-reconciler scan

# 查看下一个需要判断的问题
memory-reconciler next-question

# 提交裁决
memory-reconciler decide <question-id> <choice>

# 生成 dry-run plan
memory-reconciler plan

# 预览 plan
memory-reconciler preview <plan_id>
```

CLI 不可用时，skill 会用 shell 命令读取文件完成检查，不写入。

## 依赖

- Hermes Agent 环境（需要 `${HERMES_HOME}/memories/` 下有记忆文件）
- CLI 部分依赖见 `cli/` 目录

## 目录结构

```
hermes-memory-reconciler/
  SKILL.md          # 核心指令
  cli/              # memory-reconciler CLI
  agents/           # runtime 适配文件
  references/       # 检查规则参考
  tests/            # 测试用例
```
