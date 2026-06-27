# Karakuri

[English](./README.en.md)

Karakuri (からくり) ——指精巧机关人偶，小而灵活，一上发条就自己动起来。这个仓库里的每个 skill 也是这样：独立、轻量、放进 agent 就能跑。

面向 Claude Code、Codex、Hermes、OpenClaw 等通用 Agent。每个 skill 是一个独立文件夹：`SKILL.md` 是核心指令，参考资料、模板和脚本放在同一目录下。不绑定特定 runtime；有额外依赖的会单独注明。

## 可用 Skills

| Skill | 一句话定位 |
|-------|-----------|
| [coding-music](./coding-music) | 编码时播放音乐，权限弹窗出现自动暂停，确认后恢复——不用切窗口去翻播放器 |
| [coding-agent-fit](./coding-agent-fit) | 扔个文档 URL，帮你看看这个服务对 Coding Agent 友不友好 |
| [skill-triage-sibyl](./skill-triage-sibyl) | 给当前 agent 的 skill 库做体检，扫出描述重叠/边界吹大或写漏/调用频率，给可回退的处置建议 |

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

你打算让 Claude Code 帮你接入一个新的 API 或云服务。但这个服务对 Agent 友好吗？Agent 能自己找到入口吗？quickstart 能跑通吗？会不会卡在拿 key 或者某个权限流程上？

以前只能让 Agent 先试试，卡了再排查。现在可以先跑个评测：

- 🔍 **探测** → 自动扫 llms.txt、OpenAPI、MCP、CLI、SDK 等入口和辅助工具
- 🏃 **实跑** → 选一条接入路径真走一遍，记录每步通过还是卡住
- 📊 **出报告** → 五个维度打分，告诉你哪块强、哪块拖后腿、最该先改什么

DevRel 团队拿来自查接入质量，开发者拿来选型——先看评测再决定值不值得让 Agent 去接。

依赖 Python 3（探测脚本）。评分按站点类型分权重表，详见 [coding-agent-fit/README.md](./coding-agent-fit/README.md)。

---

### Skill Triage: Sibyl Scope `0.1`

```
/skill-triage-sibyl
```

装到几十个 skill 之后，agent 调用准确度往往掉得很厉害 —— 两个 skill 描述太像、某 skill description 吹得过宽、某 skill 实际能力比描述写得多 agent 看不到。Sibyl Scope 扫当前 runtime 的 skill 列表 + 本地 30 天使用频率，按五类问题（定位重叠 / 触发边界重叠 / 边界吹大 / 边界写小 / 定位缺失）诊断，逐项让用户选 archive / rewrite / keep / defer，执行后可一键回退。命名来自 PSYCHO-PASS 的 Sibyl System —— 它是给"潜在威胁度"打分的扫描器，我们这个给 skill 描述打质量分。

依赖 Python 3 标准库 + 系统 git，无第三方包。详见 [skill-triage-sibyl/README.md](./skill-triage-sibyl/README.md)。

