# SkillTriage

[English](./README.en.md)

SkillTriage 用来帮助 Agent 整理当前运行环境里已经安装的 skills。它会先用脚本做一轮基础筛查，记录事实和候选项；然后让当前 Agent 继续阅读、比较和判断，输出一份适合用户审阅的整理报告。

它适合用来维护一个更小、更清晰的 skill 库：找出高置信重复、描述相似但边界不清的 skills、范围过宽的功能组，以及暂时应该保留但需要说明边界的 skills。SkillTriage 默认不会删除、归档、覆盖或改写任何已安装 skill。

## 它做什么

- 扫描当前 runtime 可发现的 skills，生成事实清单。
- 标记完全重复、description 过短或过宽、带脚本目录、插件托管、以及相关功能组等基础线索。
- 把可能需要进一步判断的项目交给 Agent 评估，让 Agent 阅读 description 并比较调用边界。
- 生成可审阅的 Markdown 报告、建议文件和恢复说明。
- 默认只读，不会自动修改已安装的 skills。

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

## 安全边界

SkillTriage v1 只准备审阅材料和建议。它不会自行删除、归档、覆盖或重写已经安装的 skills。插件托管和系统托管的 skills 会被视为只读对象。
