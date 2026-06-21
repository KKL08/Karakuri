# Karakuri

[English](./README.en.md)

Karakuri (からくり) ——指精巧机关人偶，小而灵活，一上发条就自己动起来。这个仓库里的每个 skill 也是这样：独立、轻量、放进 agent 就能跑。

面向 Claude Code、Codex、Hermes、OpenClaw 等通用 Agent。每个 skill 是一个独立文件夹：`SKILL.md` 是核心指令，参考资料、模板和脚本放在同一目录下。不绑定特定 runtime；有额外依赖的会单独注明。

## 可用 Skills

| Skill | 一句话定位 |
|-------|-----------|
| [coding-music](./coding-music) | 编码时播放音乐，权限弹窗出现自动暂停，确认后恢复——不用切窗口去翻播放器 |
| [coding-agent-fit](./coding-agent-fit) | 输入云服务或开发工具的文档 URL，自动输出 Coding Agent 接入评测报告，帮 DevRel 团队自查或选型 |
| [shinkaskill](./shinkaskill) | 发布前的质量检查：读取单个 skill 的结构和触发质量，按 rubric 打分，可选跑真实 eval |
| [skill-triage](./skill-triage) | 扫描 skill 库中的重复和边界模糊问题，支持偏好记忆，让后续报告更贴合整理习惯 |

## 安装

```bash
git clone https://github.com/KKL08/Karakuri.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Karakuri/<skill-name> ~/.claude/skills/

# Codex
mkdir -p ~/.codex/skills
cp -r Karakuri/<skill-name> ~/.codex/skills/
```

Hermes、OpenClaw 或其他 runtime：放到对应的 skill/plugin 目录，或作为 Markdown 指令包导入。skill 里的 `agents/<runtime>.yaml`、`references/`、`scripts/` 需要和 `SKILL.md` 一起保留。

复制后，如果 agent 不会自动读取新 skill，重启对应 runtime。

## 各 Skill 详情

### Coding Music `0.1 beta`

```
/coding-music
```

用 Claude Code 写代码的日常是这样的：

Claude 在终端里噼里啪啦地输出，你可以靠在椅背上，趁这个空档听听歌、放松一下。
问题是，它随时可能刹一脚——要么弹个权限确认框，要么干完了当前任务等着你的进一步指令。

这时候你还沉浸在音乐播放中，注意力根本没法立刻集中到屏幕上的文字上。
经常会出现过了好一会才意识到需要进行操作，然后手忙脚乱地找暂停键，处理完授权，再手动把音乐点回来。

于是这个 Skill 诞生了。
它做的事特别简单：让你的注意力集中在更需要的地方，并替你节省来回切换音乐播放器的时间：

- 🧘 **AI 干活时** → 音乐照常播放，你继续放松
- ⚡ **AI 需要你的注意力时** → 音乐自动淡出 / 暂停
- ✅ **你处理完后** → 音乐自动回来

现在我的 Claude Code 节奏变成了——它输出，我放松；它提问，我专注。
切换无比自然，这才是 AI coding 该有的呼吸感。

安装和配置见 [coding-music/README.md](./coding-music/README.md)。

---

### Coding Agent Fit

```
/coding-agent-fit https://resend.com/docs
```

想知道某个云服务或开发工具对 Coding Agent 接入友不友好？给一个文档 URL，Coding Agent Fit 从服务入口、接入文档、Agent 辅助工具、接入阻碍、维护与反馈五个维度打分，产出接入评测报告。DevRel 团队可以用来自查接入质量，agent 开发者可以快速判断一个平台是否值得集成。

依赖 Python 3（探测脚本）。评分维度和完整流程见 [coding-agent-fit/README.md](./coding-agent-fit/README.md)。

---

### ShinkaSkill `0.1 beta`

```
/shinkaskill
```

单个 skill 发布或迭代前的质量检查。读取 `SKILL.md`、引用文件和脚本，检查结构完整性、触发描述、授权说明等，按 rubric 逐项打分并给出改进建议。可选通过 Codex 或 Claude Code 跑 subagent 做真实 eval。

和 skill-triage 的分工：shinkaskill 只看单个 skill 的完整性，skill-triage 看整个库的重复和边界。依赖 Node.js 20+。安装和 CLI 用法见 [shinkaskill/README.md](./shinkaskill/README.md)。

---

### SkillTriage `0.3 beta`

```
/skill-triage
```

Skill 库越装越多，有些功能接近、边界模糊，遇到任务时 Agent 不知道该调哪个。SkillTriage 扫描当前 skill 库，区分高度重复、功能相近但边界明确、描述太宽容易误触发几种情况，生成诊断报告。默认只报告不改动；决定整理时先确认再执行。支持偏好记忆，后续报告会越来越贴合你的整理习惯。

依赖 Python 3 标准库。使用流程和输出格式见 [skill-triage/README.md](./skill-triage/README.md)。
