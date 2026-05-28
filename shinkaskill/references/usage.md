# ShinkaSkill 用法

ShinkaSkill 用来 inspect、review、score、evaluate、improve Agent Skills。默认中文优先，先做只读静态检查；当前 eval 能创建本地 run 沙箱，也能在用户授权后通过 Codex/Claude Code adapter 运行真实 agent eval。grader 和 comparator 会作为独立 agent 继续运行，并在报告中写入逐项 rubric 打分。propose、apply 仍是安全骨架，文档和输出都要照实说明能力边界。

安装是否完成，以 `references/install-standard.md` 为准。通过 `install.mjs` 安装后，优先用当前 skill 目录里的 `scripts/shinka` 启动 CLI；不要只检查 `SKILL.md` 是否存在。

## 只读检查

先确认用户给的 skill 路径，再运行 inspect。命令只读取目标 skill，并输出中文检查报告。

```bash
npm run shinka -- inspect <skill-path>
```

如果当前 skill 是通过 `install.mjs` 安装的，也可以从安装目录使用启动器：

```bash
scripts/shinka inspect <skill-path>
```

示例：

```bash
npm run shinka -- inspect ./skills/example
```

## eval run

当前 eval 会创建本地 run 沙箱，保存 `original/`、`sandbox/`、`eval-results.json` 和 `eval-report.md`。默认 `generic` adapter 只写入 unavailable，不会运行真实 eval，也不会修改原始 skill。

用户明确授权并选择 `--adapter codex` 或 `--adapter claude-code` 时，会启动当前环境中的 subagent 做真实 eval。执行前必须说明评测会在当前 ShinkaSkill run 的 sandbox 内完成，不会触发 apply、commit 或其他写回操作，原始 skill 不会被直接修改；所选 agent runtime 仍会按当前环境配置完成推理。

授权 UX 优先走结构化提问：在 Codex 中优先使用 `request_user_input`，在 Claude Code 中优先使用 `AskUserQuestion`，其他 runtime 使用等价的 ask/clarify 工具。不要要求用户复制整句授权文本。结构化提问至少包含标题 `是否运行真实 eval？`、目标 skill、adapter、风险项和 `同意运行` / `取消` 两个选项。没有结构化提问工具时，退回普通文本确认或 CLI y/N；非交互环境必须显式传入 `--yes`。

Codex Default mode 下可能出现“工具名存在但调用被拒绝”的情况。这是宿主运行模式限制。兼容方式参考 baoyu 类 skill：CLI 不直接依赖 runtime-only 工具，而是输出可转译的授权 artifact；上层 agent 能用结构化工具时转成按钮，不能用时展示普通文字。

```bash
npm run --silent shinka -- eval <skill-path> --adapter codex --consent-json
```

真实 eval 会分三段运行：eval agent 先产出 baseline / with_skill / candidate 输出，grader 再按每个 mode 逐项 rubric 打分，comparator 最后做匿名输出对比。grader 会知道 mode，因为 `skill_grounding` 需要判断 with_skill 是否真的使用了 SKILL.md、baseline 是否避免使用 skill；comparator 则只看到 `output_a` / `output_b` / `output_c`，结果回收后再映射回真实模式。

真实 adapter 会先做 preflight。若 Codex preflight 报告无法写入 `.codex` state 数据库，拦截来自外层 Codex 工具沙箱；ShinkaSkill 的 run sandbox 只复制 `original/` 和 `sandbox/`，不会写回原始 skill。新用户在本地终端直接运行通常不会遇到这一层；在 Codex agent 里运行时，需要 agent 请求提权执行同一条 eval 命令。若 Claude Code preflight 报告认证不可用，先完成 Claude Code CLI 登录或认证。

```bash
npm run shinka -- eval <skill-path>
```

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes
```

```bash
npm run shinka -- eval <skill-path> --adapter claude-code --yes
```

控制真实 subagent 并发：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes --max-concurrent-agents 8
```

慢任务可以调高单个 subagent 超时：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes --agent-timeout-ms 300000
```

## propose guard/stub

当前 propose/apply 是 guard/stub 命令。propose 不会生成 patch；即使传入 `--verify-patch`，candidate eval 也尚未接入，不能声称已经验证候选 patch。

```bash
npm run shinka -- propose <skill-path>
```

命令存在是为了保留入口和安全提示：

```bash
npm run shinka -- propose <skill-path> --verify-patch
```

## apply guard/stub

apply 不会真实写回。即使传入 `--yes`，CLI 也只会提示准备应用 run，并说明 run 读取和最终确认流程还没接入。

未来接入真实 patch/apply 时，必须先给 diff/patchPath，并在写回 patch 前再次确认。确认内容至少包括目标 run、目标 skill、将写回的文件、diff 摘要、patchPath 和是否创建 commit。

```bash
npm run shinka -- apply <run-id>
```

## 清理历史 run

clean 只清理本仓库 `.shinka/runs` 下的历史 run。建议先 dry-run，再执行清理。可以用 `--older-than 30d` 只清理超过指定天数的 run。

```bash
npm run shinka -- clean --dry-run --keep-last 10
```

```bash
npm run shinka -- clean --dry-run --keep-last 10 --older-than 30d
```

```bash
npm run shinka -- clean --keep-last 10
```

安装后启动器同样支持：

```bash
scripts/shinka clean --dry-run --keep-last 10
```

## 边界提醒

不要默认扫描 home 目录，不要使用固定本地路径作为示例，也不要在缺少真实 eval 或 patch/apply 能力时给出模拟结果。静态检查、eval 授权状态、patch 风险和下一步建议都优先用中文说明。
