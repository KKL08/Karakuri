# ShinkaSkill 安装验收标准

这份文档用来判断 ShinkaSkill 是否真的安装完成。不要只看文件是否复制成功；能安装、运行、授权、生成报告、清理历史 run，才算可用。

当前推荐的安装方式是「源码安装 + install.mjs」。安装器会复制 skill wrapper，并在安装目录生成 `scripts/shinka` 启动器。agent 可以通过这个启动器从任意工作目录调用 ShinkaSkill CLI。

## 安装完成的定义

安装完成需要同时满足这些条件：

- CLI 能运行：`shinka --help` 或 `npm run shinka -- --help` 能输出命令帮助。
- Skill wrapper 能被 agent 发现：安装目录中存在 `shinkaskill/SKILL.md`，重启 agent 后能触发这个 skill。
- 安装后启动器能运行：安装目录中存在 `shinkaskill/scripts/shinka`，并能从任意工作目录执行 `inspect`。
- 只读检查能跑通：对一个最小 skill 运行 `inspect`，能得到中文报告。
- Eval run 能创建：默认 `generic` adapter 会创建 `.shinka/runs/<run-id>`，并写入 `unavailable`，不假装真实 eval 已经运行。
- 真实 eval 有授权门：使用 `--adapter codex` 或 `--adapter claude-code` 前，必须让用户确认；同一时间最多启动 8 个 subagent。
- 报告能回读：能打开 `eval-results.json` 和 `eval-report.md`，并看到 grader、comparator、rubric 逐项打分字段。
- 清理能预演：`clean --dry-run` 能列出将清理的 run，不直接删除。

## 源码安装

当前版本优先推荐这种安装方式，开发和试用都适用。

```bash
git clone https://github.com/KKL08/Karakuri.git
cd Skill/shinkaskill
npm install
npm run build
npm run install:skill -- --codex-home <codex-home>
```

`install.mjs` 会检查 `dist/cli/index.js`。如果 CLI 还没构建，它会自动运行 `npm run build`。也可以先手动运行 `npm run build`，这样构建错误会更早暴露。

验收：

```bash
npm run shinka -- --help
npm run install:skill -- --codex-home <codex-home>
<codex-home>/skills/shinkaskill/scripts/shinka --help
npm run shinka -- inspect <skill-path>
npm run shinka -- eval <skill-path> --yes
npm run shinka -- clean --dry-run --keep-last 10
```

通过标准：

- `inspect` 输出中文报告，并包含 Gate、Static Score 和评分维度。
- 安装后 `scripts/shinka` 可以在 repo 外的工作目录运行。
- 默认 `eval` 输出 `unavailable`，同时生成 `eval-results.json` 和 `eval-report.md`。
- `clean --dry-run` 明确输出 `dry-run`，只展示计划，不删除文件。

## Skill wrapper 安装

适合把 ShinkaSkill 作为 agent skill 使用。

安装器会把以下内容复制到目标 skill 目录：

```text
skills/shinkaskill/
  SKILL.md
  references/
    usage.md
    install-standard.md
  scripts/
    shinka
  .shinka-install.json
```

安装到目标 agent 的 skill 目录时，不要只复制 `SKILL.md`。`references/` 是使用说明的一部分，`scripts/shinka` 是安装后的 CLI 启动器。

安装后需要重启或刷新 agent，让它重新读取 skill 列表。

验收：

- agent 的技能列表里能看到 `shinkaskill`。
- agent 能使用安装目录里的 `scripts/shinka` 执行检查命令。
- 触发请求类似「检查这个 skill」时，agent 会先要求用户给出 skill 路径。
- agent 不应该默认扫描 home 目录，也不应该使用安装者的固定本地路径做默认值。
- 当用户要求真实 eval 时，agent 会优先用结构化提问工具请求授权；没有结构化工具时，退回普通确认。

## CLI 和 wrapper 的关系

当前 wrapper 不复制完整 CLI。`install.mjs` 会生成 `scripts/shinka`，这个启动器会回到源码仓库调用已构建的 `dist/cli/index.js`。如果 `dist/` 被清掉，启动器会尝试在源码仓库运行一次 `npm run build`。

如果源码目录被移动或删除，启动器无法继续工作，需要回到新的源码目录重新运行 `node install.mjs`。使用 `--force` 时，安装器会替换整个目标 `shinkaskill` 目录，不会增量合并；不要把自定义 prompt、私有配置或实验文件只放在安装目录里。

安装时要明确使用方式：

- 开发者在 repo 根目录运行：使用 `npm run shinka -- ...`。
- 已经全局安装 CLI：使用 `shinka ...`。
- 使用 `install.mjs` 安装 wrapper：使用安装目录里的 `scripts/shinka ...`。
- 只手工复制 wrapper：只能读说明，不能直接运行检查；需要用户提供 ShinkaSkill repo 路径或可执行的 CLI 命令。

文档和回答里不要把这些方式混在一起。

## 真实 eval 验收

真实 eval 需要对应 runtime 已经安装并认证：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes
npm run shinka -- eval <skill-path> --adapter claude-code --yes
```

可选并发参数：

```bash
npm run shinka -- eval <skill-path> --adapter codex --yes --max-concurrent-agents 8
```

通过标准：

- 命令输出显示使用的 adapter 和 subagent 并发上限。
- `eval-results.json` 包含 `results`、`grader_results`、`comparisons`。
- `grader_results` 至少包含 `expectationResults`、`rubricScores`、`gradingSummary`。
- `rubricScores` 按逐项 rubric 给出 `key`、`label`、`score`、`maxScore`、`passed`、`evidence`。
- `eval-report.md` 有 `Grader / Comparator` 和 `Rubric 逐项打分`。
- grader 输出按真实 mode 打分；comparator 输出应先使用匿名标签，再由 ShinkaSkill 映射成 `baseline` / `with_skill` / `candidate`。
- 原始 skill 目录没有被修改。

如果 adapter 不可用，报告必须写明原因，不能把 fallback 写成真实 eval。

## 发布前检查

对外发布前至少跑这几项：

```bash
npm run typecheck
npm run build
git diff --check
```

准备对外发布时，还要做一次临时目录验收：

1. 新建一个临时 `codex-home`。
2. 运行 `node install.mjs --codex-home <codex-home>`。
3. 确认 `SKILL.md`、`references/`、`scripts/shinka` 和 `.shinka-install.json` 都在。
4. 从 repo 外的临时工作目录调用 `<codex-home>/skills/shinkaskill/scripts/shinka inspect <skill-path>`。
5. 再调用同一个启动器跑 `eval <skill-path> --yes` 和 `clean --dry-run --keep-last 10`。

## 常见失败

- 只复制 `SKILL.md`：agent 能看到 skill，但缺少使用说明和 CLI 启动器。
- 没有运行 `npm run build`：`package.json` 的 `bin` 指向 `dist/cli/index.js`，源码安装后需要构建。
- 移动或删除源码仓库：安装后 `scripts/shinka` 会找不到原源码目录，需要重新安装。
- `--force` 覆盖已有安装：目标目录里的手工文件会被替换，安装前先确认没有只存在于安装目录的自定义内容。
- Windows 直接运行启动器：当前只验收 macOS/Linux，Windows 需要后续生成 `.cmd` 包装。
- 把固定本地路径写进示例：别人不能复用，也容易误扫错误目录。
- 真实 eval 没有授权：不允许启动 subagent。
- adapter 未认证：应返回 unavailable 或 failed，并解释命令不可用或认证失败。
- `clean` 没有先 dry-run：容易删掉仍需要回看的 run。
