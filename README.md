# AI Agent Skills 合集

[English](./README.en.md)

几个 AI Agent skill，可以在 Claude Code、Codex、Hermes、OpenClaw 等通用 Agent 里用。

每个 skill 是一个独立文件夹：`SKILL.md` 是核心指令，参考资料、模板和脚本放在同一目录下。agent 遇到同类任务时整套复用，不用每次重新搭。不绑定特定 runtime；有额外依赖的会单独注明。

## 可用 Skills

| Skill | 适用对象 | 说明 |
|-------|----------|------|
| [coding-music](./coding-music) | Claude Code | 编码时播放音乐；权限弹窗自动暂停，确认后继续 |
| [coding-agent-fit](./coding-agent-fit) | 通用 coding agent | 评测云服务或开发工具对 Coding Agent 接入的支持程度 |
| [gen-image-grounding](./gen-image-grounding) | 通用生成类 agent | 生图前搜索事实和视觉参考，整理成结构化的生图参数 |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | 扫描长期记忆里的重复、冲突、过期和风险指令 |
| [shinkaskill](./shinkaskill) | Codex / Claude Code | 检查单个 skill 的结构和触发质量，生成评分报告 |
| [skill-triage](./skill-triage) | Codex / Claude Code | 识别 skill 库中的重复和边界不清问题，支持偏好记忆 |

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

## 各 Skill 简介

### coding-music `0.1 beta`

AI Agent 干活时，注意力主要在审查和确认上。权限弹窗、关键决策这些需要判断的时刻得及时看到；其余时间可以听着歌等。

编码时播放网易云音乐喜欢的歌，权限弹窗出现自动暂停，确认后恢复。可选开启「Claude 回复完毕也暂停」。依赖 [ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli)、`mpv`、Python 3、Node.js 18+。

详细安装和配置见 [coding-music/README.md](./coding-music/README.md)。

```
/coding-music
```

---

### coding-agent-fit

输入一个云服务或开发工具的文档 URL，输出 Coding Agent 接入评测报告：接入有多顺、最可能卡在哪、服务方最该先补什么。

从服务入口、接入文档、Agent 辅助工具、接入阻碍、维护与反馈 5 个维度打分。DevRel 团队可以用来自查，agent 开发者可以快速判断一个平台是否方便 AI 集成。依赖 Python 3（探测脚本）。

详细评分维度和流程见 [coding-agent-fit/README.md](./coding-agent-fit/README.md)。

```
/coding-agent-fit https://resend.com/docs
```

---

### gen-image-grounding `0.1 beta`

涉及真实人物、地点、产品、徽标等内容的生图需求，最好先补足事实和视觉参考。

根据 prompt 规划搜索，调用已配置的文本和图片搜索 provider，输出 `gen_prompt`、`reference_images`、`facts`、`sources`、`warnings`，给后续生图模型用。支持 Serper、火山引擎、Tavily、Firecrawl、Jina。依赖 Python 3；没有 API key 时只输出搜索计划，不实际执行。

详细配置和输出格式见 [gen-image-grounding/README.md](./gen-image-grounding/README.md)。

```
/gen-image-grounding
```

---

### hermes-memory-reconciler `0.2 beta`

长期记忆用久了容易乱：偏好冲突、事实过期、旧结论影响判断，甚至可能保留有风险的指令。

扫描 Hermes 的 `USER.md` 和 `MEMORY.md`，识别重复、冲突、范围不清、疑似过期和风险指令。会先问几个问题确认优先级，再整理出建议方案。确认前不会动记忆文件。默认读取 `${HERMES_HOME:-$HOME/.hermes}/memories/`。

详细流程和 CLI 用法见 [hermes-memory-reconciler/README.md](./hermes-memory-reconciler/README.md)。

```
/hermes-memory-reconciler
```

---

### shinkaskill `0.1 beta`

单个 skill 发布或迭代前的质量检查。读取 `SKILL.md`、引用文件和脚本，检查结构完整性、触发描述、授权说明等，按 rubric 打分并给改进建议。可选真实 eval（通过 Codex 或 Claude Code 跑 subagent）。

和 skill-triage 的区别：shinkaskill 只看一个 skill 的完整性，skill-triage 看整个库的重复和边界。依赖 Node.js 20+。

详细安装和 CLI 用法见 [shinkaskill/README.md](./shinkaskill/README.md)。

```
/shinkaskill
```

---

### skill-triage `0.3 beta`

Agent 用久了装的 skill 越来越多，有些描述接近、边界模糊，遇到任务时不确定该调哪个。

扫描当前 agent 的 skill 库，区分高度重复、功能相近但边界明确、描述太宽容易误触发的情况，生成报告。默认只报告不改动；决定整理时先确认再执行。支持偏好记忆，让后续报告更贴近整理习惯。依赖 Python 3 标准库。

详细使用流程和输出格式见 [skill-triage/README.md](./skill-triage/README.md)。

```
/skill-triage
```
