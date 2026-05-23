# SkillTriage

[English](./README.en.md)

SkillTriage 用来帮助 Agent 整理当前运行环境里已经安装的 skills。它会先用脚本做一轮基础筛查，记录事实和候选项；然后让当前 Agent 继续阅读、比较和判断，输出一份适合用户审阅的整理报告。

它适合用来维护一个更小、更清晰的 skill 库：找出高置信重复、描述相似但边界不清的 skills、范围过宽的功能组，以及暂时应该保留但需要说明边界的 skills。遇到取舍取决于用户习惯的情况，它会放到“需要你决定”，不会强行给结论。SkillTriage 默认不会删除、归档、覆盖或改写任何已安装 skill。

## 它做什么

- 扫描当前 runtime 可发现的 skills，生成事实清单。
- 标记完全重复、description 过短或过宽、带脚本目录、插件托管、以及相关功能组等基础线索。
- 把可能需要进一步判断的项目交给 Agent 评估，让 Agent 阅读 description 并比较调用边界。
- 生成可审阅的 Markdown 报告、建议文件和恢复说明。
- 默认先停在报告和建议，不会自动改动已安装的 skills。
- 如果你决定继续整理，Agent 会先列出待处理项目，等你确认后再执行。
- 根据用户确认的整理选择生成偏好记忆草稿，用户确认后才保存到本地偏好记录。
- 后续扫描会把已确认偏好作为报告提示，让诊断和整理建议更贴近用户习惯。
- 写入前会先备份；执行后可以按本次运行记录里的恢复材料回退。

## 支持的运行环境

v1 支持两种“当前运行环境”流程：

- Codex：扫描当前 Codex 环境能看到的 skill 目录。
- Claude Code：扫描 Claude Code 能看到的 skill 和插件目录结构。

同一份 SkillTriage 可以分别安装在 Codex 和 Claude Code 中使用。它每次默认整理当前 Agent 自己的 skill 空间，而不是把多个 runtime 混在一起处理。

## 安装

从这个仓库复制 skill 文件夹：

```bash
git clone https://github.com/KKL08/Skill.git

# Codex
mkdir -p ~/.codex/skills
cp -r Skill/skill-triage ~/.codex/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/skill-triage ~/.claude/skills/
```

如果目标 Agent 不支持热加载，复制后需要重启或重新加载。

## 使用

在 Agent 里让它运行 SkillTriage，例如：

```text
Use skill-triage to review my installed skills.
```

当用户没有提前说明时，SkillTriage 会先确认两个设置：

- 评估范围：`quick`、`full` 或 `selected`。
- 备份策略：`off`、`targeted` 或 `full`。

第一次整理建议使用 `full` + `targeted`。日常维护建议使用 `quick` + `targeted`。

## 直接运行扫描器

Codex 快速扫描：

```bash
PYTHONPATH=~/.codex/skills/skill-triage/scripts \
python3 ~/.codex/skills/skill-triage/scripts/scan_skills.py \
  --runtime codex \
  --evaluation-scope quick \
  --backup targeted
```

Claude Code 快速扫描：

```bash
PYTHONPATH=~/.claude/skills/skill-triage/scripts \
python3 ~/.claude/skills/skill-triage/scripts/scan_skills.py \
  --runtime claude-code \
  --evaluation-scope quick \
  --backup targeted
```

直接运行扫描器得到的是基础材料，不是最终整理建议。最终要以 Agent 阅读候选项后写出的报告为准。

## 输出文件

运行产物默认写入：

```text
~/.skilltriage/runs/<runtime>/<run-id>/
```

主要文件包括：

- `inventory.json`：本次发现到的 skill 事实清单。
- `basic_screening.json`：基础筛查结果和进入 Agent 评估的路由证据。
- `agent_evaluation.md`：Agent 对候选项、相似项和调用边界的详细判断。
- `report.md`：建议优先阅读的用户报告。
- `recovery.md`：备份情况和未来恢复路径说明。
- `decisions/`：需要用户决定的取舍、用户本次选择，以及待确认的偏好记忆草稿。

## 偏好记忆

有些整理问题不能只靠相似度判断。比如两个 skill 都合理，一个更像通用入口，另一个更像固定流程；到底保留哪个，往往取决于你的使用习惯。SkillTriage 会把这类问题放到“需要你决定”，说明差异和可选处理方式。

当你选择执行整理操作后，SkillTriage 可以根据本次选择生成偏好记忆草稿。你确认后，这些偏好会保存到本地偏好记录；以后再检查 skill 库时，报告会把它们作为提示，让诊断和整理建议越来越懂你的习惯。偏好只影响提示和排序，不会自动清理 skill。

## 可选整理

大多数情况下，SkillTriage 会停在报告阶段：它告诉你哪些 skill 值得保留、哪些可能重复、哪些描述容易让 Agent 混淆。你可以只把它当成一次 skill 库体检来用。

如果你明确说要继续整理，Agent 会先列出可处理的候选项，让你逐项选择。目前支持两类操作：归档可写 skill，或用已经生成的建议版本替换可写 skill 的 `SKILL.md`。

整理开始前，Agent 会先备份并列出将要处理的项目，不会马上改动已安装 skill。只有你确认后，才会继续执行。如果有新的动作要求，需要重新确认。

执行后，本次运行目录会保留恢复材料。需要恢复时，可以让 Agent 回退本次执行；回退前仍会检查路径和文件内容，避免覆盖你后来手动改过的东西。

## 安全边界

插件托管、系统托管、只读、来源不明，以及 SkillTriage 自己，都不会被作为可执行整理对象。merge/dedupe 类建议只会出现在报告里，不会自动执行。偏好记忆不是执行授权，不能绕过备份、确认和恢复检查。
