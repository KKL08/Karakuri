# ShinkaSkill

ShinkaSkill 检查单个 Agent Skill —— 发布前、重构后，或 skill 表现不稳定时都可以拿它来把关。它会告诉维护者这份 skill 写清楚了没有、agent 能不能正确触发、缺少哪些材料，以及真实运行中会卡在哪里。检查默认只读，不会扫描 home 目录，也不会在未授权时修改原始 skill。结果会整理成中文报告，带有评分、证据、风险和改进建议，方便继续改，也方便交给别人审阅。

## 痛点

写 skill 本身不难，但判断它在真实 agent 里是不是好用却不容易。常见问题包括：描述看起来完整，触发条件却不够明确；引用的文件和脚本放散了，agent 运行时找不到；权限、失败处理和边界说明太少；评估只有人工感觉，缺少可复查的评分和证据。

ShinkaSkill 把这些判断拆成一份可读报告。维护者不用反复手工翻 `SKILL.md`，也不用只靠"看起来还行"做决定。

## 使用流程

推荐从只读检查开始：

1. 准备要检查的 skill 路径。
2. 运行 `inspect`，得到静态报告。
3. 根据报告修正触发描述、引用文件、权限说明或使用步骤。
4. 如果需要更接近真实使用的判断，再授权运行真实 eval。
5. 查看 eval 报告里的逐项评分、运行证据和对比结果。

真实 eval 会把被测 skill 复制到本次 run 的 sandbox，再通过 Codex 或 Claude Code 启动独立 agent 任务。这个步骤需要用户明确同意；当前环境暂时不能运行真实 eval 时，可以先使用静态报告。

## 你会得到 📄

- 一份中文 Markdown 检查报告：主要问题、0-100 总分、按维度拆开的 rubric 评分、证据和改进建议
- 可选 JSON 输出，方便接入其他工具或自动化流程
- 真实 eval 的 run 目录（需授权），包含被测 skill 副本、运行结果、`eval-report.md`、grader 逐项打分和 comparator 对比

`propose` 和 `apply` 目前还是安全入口，不会生成 patch，也不会写回原始 skill。自动优化和写回会在后续版本补上。

## 安装

需要 Node.js 20 或更高版本。

先拉取源码并构建 CLI：

```bash
git clone https://github.com/KKL08/Karakuri.git
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

创建 eval run。默认模式只记录当前环境不能运行真实 agent 的原因，不会假装已经完成真实 eval：

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
