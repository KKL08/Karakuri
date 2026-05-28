---
name: shinkaskill
description: "Use when the user wants to inspect, review, score, evaluate, or improve Agent Skills. 中文优先：用于检查 skill 质量、生成中文报告、运行受控 eval、说明 propose/apply guard 边界。"
---

# ShinkaSkill

ShinkaSkill 是 repo-local 的 Agent Skill 检查与优化 wrapper。默认中文优先，默认只读检查；当前 CLI 还处在安全 MVP 阶段，eval、propose、apply 都必须按现有能力描述，不能把未来能力写成已经可用。

## 使用原则

1. 先确认用户给的 skill 路径。不默认扫描 home，也不要假设任何固定本地路径存在。
2. 静态检查优先。先用 inspect 看结构、frontmatter、引用、评分和风险，再决定是否需要进入 eval 授权流程。
3. 核心输出使用中文，包括结论、分数、风险、证据、建议和下一步。
4. 当前 eval 会创建本地 run 沙箱，保存 `original/`、`sandbox/`、`eval-results.json` 和 `eval-report.md`；默认 `generic` adapter 只写入 unavailable，不会运行真实 eval，也不会修改原始 skill。
5. 用户明确授权并选择 `--adapter codex` 或 `--adapter claude-code` 时，可以启动当前环境中的 subagent 做真实 eval。执行前必须告知用户评测会在当前 ShinkaSkill run 的 sandbox 内完成，不会触发 apply、commit 或其他写回操作，原始 skill 不会被直接修改；所选 agent runtime 仍会按当前环境配置完成推理。
6. 当前 propose/apply 是 guard/stub 命令；propose 不会生成 patch，apply 不会真实写回。未来接入真实 patch/apply 时，必须先给 diff/patchPath，并在写回 patch 前必须再次确认。
7. 如果路径缺失、权限不足、依赖未安装或 eval adapter 不可用，要直接说明阻塞点，不要用 mock 结果冒充真实运行。
8. 判断别人是否安装完成时，使用 `references/install-standard.md`。不要只看 `SKILL.md` 是否复制成功。
9. 如果是通过 `install.mjs` 安装，优先使用当前 skill 目录下的 `scripts/shinka` 启动 CLI；如果没有这个启动器，再退回 repo 根目录的 `npm run shinka -- ...`。

## 用户输入工具

请求真实 eval 授权时，优先使用当前 runtime 暴露的结构化提问工具，例如 Codex 的 `request_user_input`、Claude Code 的 `AskUserQuestion`，或其他等价的 ask/clarify 工具。不要要求用户复制整句授权文本。

结构化提问应包含：

- 标题：`是否运行真实 eval？`
- 目标 skill 名称和用户传入路径
- 将使用的 adapter：`codex` 或 `claude-code`
- 风险项：会复制到本地 sandbox、会启动当前环境中的 subagent、评测只在 sandbox 内完成、不会触发 apply、commit 或其他写回操作、原始 skill 不会被直接修改
- 选项：`同意运行` / `取消`

如果当前 runtime 没有结构化提问工具，退回普通文本确认或 CLI 的 y/N；非交互环境必须要求显式 `--yes`，否则拒绝运行真实 eval。

如果当前环境像 Codex Default mode 一样暴露了工具名但拒绝调用结构化提问，不要继续重试。原因是宿主运行模式限制，不是 ShinkaSkill CLI 能力缺失。可用 `shinka eval <skill-path> --adapter codex --consent-json` 生成结构化授权请求 artifact；上层 agent 能调用 `request_user_input` / `AskUserQuestion` 时，把 artifact 映射成按钮问题，不能调用时就展示其中的 `plain_text_fallback`。如果通过 npm script 调用，需要用 `npm run --silent shinka -- ... --consent-json`，避免 npm header 混进 JSON。

## 常用命令

只读检查：

```bash
npm run shinka -- inspect <skill-path>
```

安装后也可以用 wrapper 自带启动器：

```bash
scripts/shinka inspect <skill-path>
```

准备 eval run。默认只创建本地 run 并写入 unavailable：

```bash
npm run shinka -- eval <skill-path>
```

运行真实 Codex/Claude Code agent eval：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes
npm run shinka -- eval <skill-path> --adapter claude-code --yes
```

如果运行真实 Codex eval 时 preflight 报告“外层 Codex 工具沙箱阻止 Codex CLI 写入自身状态目录”，说明拦截发生在宿主 Codex 工具沙箱；ShinkaSkill run sandbox 和被测 skill 的 read-only sandbox 都不会写回原始目录。解决方式是让当前 agent 请求提权运行同一条命令，或让用户在本地终端直接执行。

慢任务可以调高单个 subagent 超时时间：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes --agent-timeout-ms 300000
```

进入 propose guard/stub。当前不会生成 patch：

```bash
npm run shinka -- propose <skill-path>
```

进入 apply guard/stub。当前不会真实写回：

```bash
npm run shinka -- apply <run-id>
```

清理本仓库历史 run：

```bash
npm run shinka -- clean --keep-last 10
```

更多用法见 `references/usage.md`。
安装验收标准见 `references/install-standard.md`。
