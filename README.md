# AI Agent Skills 合集

[English](./README.en.md)

这个仓库里几个 AI Agent skill，面向在 Claude Code、Codex、Hermes、OpenClaw 等通用 Agent 上做开发的工程师。每个 skill 解决一类高频场景，安装后即开即用。

每个 skill 是一个独立文件夹：`SKILL.md` 是核心指令，参考资料、模板和脚本放在同一目录下。agent 遇到同类任务时整套复用，不用每次重新搭。不绑定特定 runtime；有额外依赖的会单独注明。

## 可用 Skills

| Skill | 一句话定位 |
|-------|-----------|
| [coding-music](./coding-music) | 编码时播放音乐，权限弹窗出现自动暂停，确认后恢复——不用切窗口去翻播放器 |
| [coding-agent-fit](./coding-agent-fit) | 输入云服务或开发工具的文档 URL，自动输出 Coding Agent 接入评测报告，帮 DevRel 团队自查或选型 |
| [gen-image-grounding](./gen-image-grounding) | 生图前自动搜索事实和视觉参考，输出结构化参数，减少 AI 凭空捏造 |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | 扫描 Hermes 长期记忆中的重复、冲突、过期和风险指令，整理前先问，确认前不改 |
| [shinkaskill](./shinkaskill) | 发布前的质量检查：读取单个 skill 的结构和触发质量，按 rubric 打分，可选跑真实 eval |
| [skill-triage](./skill-triage) | 扫描 skill 库中的重复和边界模糊问题，支持偏好记忆，让后续报告更贴合整理习惯 |

## 安装

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
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

### Gen Image Grounding `0.1 beta`

```
/gen-image-grounding
```

生图模型碰到真实人物、地点、产品名时容易瞎编。Gen Image Grounding 先按 prompt 规划搜索，调用你配置的文本和图片搜索 provider，整理出 `gen_prompt`、`reference_images`、`facts`、`sources`、`warnings`，给后续生图模型用。没配 API key 时只输出搜索计划，不实际执行。

支持 Serper、火山引擎、Tavily、Firecrawl、Jina。依赖 Python 3。输出格式和 provider 配置见 [gen-image-grounding/README.md](./gen-image-grounding/README.md)。

---

### Hermes Memory Reconciler `0.2 beta`

```
/hermes-memory-reconciler
```

Hermes 长期记忆跑久了会出现偏好冲突、事实过期、旧结论影响新判断的情况，甚至可能残留有风险的指令。Memory Reconciler 扫描 `USER.md` 和 `MEMORY.md`，识别重复、冲突、范围模糊、疑似过期和风险指令，先问几个问题确认优先级，再给建议方案。确认前不动记忆文件。

默认读取 `${HERMES_HOME:-$HOME/.hermes}/memories/`。详细流程和 CLI 用法见 [hermes-memory-reconciler/README.md](./hermes-memory-reconciler/README.md)。

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
