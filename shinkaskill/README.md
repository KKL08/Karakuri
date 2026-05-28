# ShinkaSkill

ShinkaSkill 用来检查 Agent Skill 的质量。它读取用户指定的 skill，检查 `SKILL.md`、触发描述、引用文件、运行边界和可维护性，并生成中文报告。

如果需要更接近真实使用的判断，ShinkaSkill 可以启动 Codex 或 Claude Code 的独立 agent 进程运行 eval。eval 结束后，grader 会逐项打分，comparator 会做 A/B 对比，报告会把证据、分数和风险写清楚。

默认情况下，ShinkaSkill 只读文件。它不会扫描用户的 home 目录，也不会在未授权时修改原始 skill。

## 能做什么

- 检查 `SKILL.md`、frontmatter、引用文件、脚本路径和常见风险。
- 按 profile 给出 0-100 的静态评分，支持 `general`、`agent-skills`、`text-only`、`workflow`、`scripted`。
- 生成中文 Markdown 报告；使用 `--json` 时输出稳定 JSON。
- 创建本地 eval run，保存 `original/`、`sandbox/`、`eval-results.json` 和 `eval-report.md`。
- 通过 `codex` 或 `claude-code` adapter 启动真实 agent eval。
- eval 后运行独立 grader 和 comparator，在报告中展示 rubric 打分和 A/B 判断。
- 通过 `--consent-json` 输出结构化授权请求，方便上层 agent 转成按钮式确认。
- 使用 `clean` 清理历史 run。

`propose` 和 `apply` 目前还是安全入口。命令会说明边界，但不会生成 patch，也不会写回原始 skill。自动优化和写回会在后续版本补上。

## 安装

需要 Node.js 20 或更高版本。

先拉取源码并构建 CLI：

```bash
git clone https://github.com/KKL08/Skill.git
cd Skill/shinkaskill
npm install
npm run build
```

如果使用 Codex，可以安装到 Codex 的 skills 目录。`CODEX_HOME` 需要指向当前环境的 Codex home：

```bash
node install.mjs --codex-home "$CODEX_HOME"
```

也可以直接指定一个 skills 目录：

```bash
node install.mjs --skills-dir <skills-dir>
```

如果两个参数都不传，安装器会先看 `CODEX_HOME`，再使用默认的 Codex skills 目录。安装完成后，刷新或重启 agent，让它重新读取 skill 列表。

安装器会复制 `SKILL.md`、`references/` 和 README，并生成 `scripts/shinka` 启动器。这个启动器会回到当前源码目录运行 CLI，所以源码目录需要保留；如果源码目录被移动或删除，需要重新运行安装命令。

## 基本用法

检查一个 skill：

```bash
npm run shinka -- inspect <skill-path>
```

指定评分 profile：

```bash
npm run shinka -- inspect <skill-path> --profile workflow
```

创建 eval run。默认 adapter 是 `generic`，只会写入 unavailable，不会启动真实 agent：

```bash
npm run shinka -- eval <skill-path> --yes
```

使用 Codex agent 做真实 eval：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes
```

使用 Claude Code agent 做真实 eval：

```bash
npm run shinka -- eval <skill-path> --adapter claude-code --yes
```

单个 agent 任务较慢时，可以调高超时时间：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes --agent-timeout-ms 300000
```

安装后，也可以通过 wrapper 里的启动器调用：

```bash
<skills-dir>/shinkaskill/scripts/shinka inspect <skill-path>
```

清理历史 run：

```bash
npm run shinka -- clean --dry-run --keep-last 10
npm run shinka -- clean --keep-last 10
```

## 输出位置

eval 会在当前工作目录写入：

```text
.shinka/
  runs/
    <run-id>/
      manifest.json
      original/
      sandbox/
      eval-results.json
      eval-report.md
```

`original/` 和 `sandbox/` 都是 run 内的副本。ShinkaSkill 不会直接修改传入的原始 skill 目录。

## 授权和安全

ShinkaSkill 只处理命令里显式传入的路径。真实 eval、外部 agent 进程、写回原始 skill、创建 commit 都需要单独授权。

在 agent runtime 中，可以把授权请求转成结构化问题，比如 Codex 的 `request_user_input` 或 Claude Code 的 `AskUserQuestion`。如果当前环境不能调用这些工具，可以先输出授权请求 JSON：

```bash
npm run --silent shinka -- eval <skill-path> --adapter codex --consent-json
```

真实 eval 依赖当前环境里已经安装并登录对应 CLI：

- `--adapter codex` 需要可运行的 `codex` 命令。
- `--adapter claude-code` 需要可运行的 `claude` 命令。

在受限 agent 环境中运行时，adapter preflight 可能会提示外层沙箱阻止 CLI 写入自身状态文件。这个限制来自宿主环境，被测 skill 和 ShinkaSkill 的 run sandbox 都不会写回原始目录。可以在 agent 中请求允许运行同一条命令，或在普通终端里执行。

## 开发和验证

```bash
npm run typecheck
npm run build
```

实际运行产生的 `.shinka/`、构建目录 `dist/` 和依赖目录 `node_modules/` 不会进入 Git。

## 限制

- `propose` 还不会生成真实 patch。
- `apply` 还不会写回原始 skill。
- 安装器生成的是源码绑定启动器，源码目录需要保留。
- 目前只验证了 macOS/Linux 风格的启动器，Windows 需要单独适配。
- 真实 eval 的质量取决于可用的 agent runtime、认证状态和测试 prompt。
