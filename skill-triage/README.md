# SkillTriage

[English](./README.en.md)

SkillTriage 帮你的 Agent 做一次 skill 库体检：先跑脚本收集事实，再把需要判断的候选项交给 Agent 深入对比，最后出一份你可以直接审阅的整理报告。整个过程不会自动删除、覆盖或改写任何已安装的 skill。

## 它能做什么

### 🕵️ 扫描事实，初筛可疑项

- 扫描当前 runtime 可发现的 skills，生成一份事实清单
- 标记出完全重复、description 过短或过宽、带脚本目录、插件托管、以及相关功能组等基础线索

### 📋 把判断交给 Agent，生成可审阅的报告

- 将需要进一步判断的项目提交给当前 Agent，让 Agent 阅读 description、比较调用边界
- 输出 Markdown 报告、建议文件和恢复说明
- 报告停在建议阶段，不会自动对已安装 skill 做任何改动

### 🩺 你决定后，再执行整理

- 如果你说要继续，Agent 会先列出所有能处理的候选项，等你逐项确认
- 根据你的选择生成偏好记忆草稿，你确认后才保存到本地偏好记录
- 以后再用 SkillTriage 时，这些偏好会作为提示，让诊断建议更贴合你的习惯（偏好只影响提示和排序，不会自动清理 skill）
- 整理前先备份，执行后可按本次运行记录中的恢复材料回退

## 支持的运行环境

v1 支持两种"当前运行环境"流程：

- Codex：扫描当前 Codex 环境能看到的 skill 目录。
- Claude Code：扫描 Claude Code 能看到的 skill 和插件目录结构。

同一份 SkillTriage 可以分别安装在 Codex 和 Claude Code 中使用。它每次默认整理当前 Agent 自己的 skill 空间，不会把多个 runtime 混在一起处理。

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

## 输出文件 📎

运行产物默认写入：

```text
~/.skilltriage/runs/<runtime>/<run-id>/
```

| 文件 | 内容 |
|------|------|
| `inventory.json` | 本次发现的 skill 事实清单 |
| `basic_screening.json` | 基础筛查结果和需要 Agent 进一步评估的候选依据 |
| `agent_evaluation.md` | Agent 对候选项、相似项和调用边界的详细判断 |
| `report.md` | 建议优先阅读的用户报告 |
| `recovery.md` | 备份情况和恢复路径说明 |
| `decisions/` | 需要你决定的取舍、你的选择、待确认的偏好记忆草稿 |

## 偏好记忆

有些整理问题不能只靠相似度判断。比如两个 skill 都合理，一个更像通用入口，另一个更像固定流程；到底保留哪个往往取决于你的使用习惯。SkillTriage 会把这类问题放到"需要你决定"，说明差异和可选处理方式。

当你选择执行整理操作后，SkillTriage 可以根据本次选择生成偏好记忆草稿。你确认后，这些偏好会保存到本地偏好记录；以后再检查 skill 库时，报告会把它们作为提示，让诊断和整理建议更符合你的习惯。偏好只影响提示和排序，不会自动清理 skill。

## 可选整理

大多数情况下，SkillTriage 会停在报告阶段：它告诉你哪些 skill 值得保留、哪些可能重复、哪些描述容易让 Agent 混淆。你可以只把它当成一次 skill 库体检来用。

如果你明确说要继续整理，Agent 会先列出可处理的候选项，让你逐项选择。目前支持两类操作：归档可写 skill，或用已经生成的建议版本替换可写 skill 的 `SKILL.md`。

整理开始前，Agent 会先备份并列出将要处理的项目，不会马上改动已安装 skill。只有你确认后，才会继续执行。如果有新的动作要求，需要重新确认。

执行后，本次运行目录会保留恢复材料。需要恢复时，可以让 Agent 回退本次执行；回退前仍会检查路径和文件内容，避免覆盖你后来手动改过的东西。

## 安全边界

插件托管、系统托管、只读、来源不明，以及 SkillTriage 自己，都不会被作为可执行整理对象。merge/dedupe 类建议只会出现在报告里，不会自动执行。偏好记忆不是执行授权，不能绕过备份、确认和恢复检查。
