# AI Agent Skills 合集

[English](./README.md)

一组 `SKILL.md` 风格的 AI Agent skill 包。

每个 skill 都把特定工作流需要的指令、参考资料和可选脚本封装在一个文件夹里，让 agent 可以稳定复用这套流程。仓库里的 skill 会尽量保持可迁移；如果某个 skill 依赖特定 runtime，会在说明里单独标出来。

## 可用 Skills

| Skill | 适用对象 | 说明 |
|-------|----------|------|
| [coding-music](./coding-music) | Claude Code | 编码时播放你喜欢的音乐 — 权限弹窗出现时自动暂停，确认后自动恢复 |
| [docai-audit](./docai-audit) | 通用 coding agent | 开发文档 AI 友好度扫描检查 — 评分覆盖 5 个维度，直指 AI 调用链路的关键节点 |
| [gen-image-grounding](./gen-image-grounding) | 通用生成类 agent | 生图前先联网搜索和搜图，输出带参考图、来源和风险提示的生成规格 |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | 扫描检查 Hermes 长期记忆里的重复、冲突、过期、低价值和危险指令型条目 |

## 如何安装

每个 skill 都是一个独立文件夹。把对应文件夹复制到你的 agent runtime 使用的 skill 目录即可：

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex 本地 skills
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
```

如果是 Hermes、OpenClaw 或其他 runtime，就放到对应 runtime 配置的 skill/plugin 目录里，或者把这个文件夹作为 Markdown 指令包导入。skill 里如果有 `agents/<runtime>.yaml`、`references/` 或 `scripts/`，需要和 `SKILL.md` 一起保留。

复制后，如果目标 agent 不支持热加载，就重启或重新加载对应 runtime。

## 依赖

- 一个能加载 `SKILL.md` skill 文件夹的 agent runtime，或者至少能引用 Markdown 指令文件夹的 agent 环境。
- 各 skill 的具体依赖见对应文件夹内的 README 或 `SKILL.md`。
- `coding-music` 仍然依赖 [Claude Code](https://claude.ai/code)、Claude Code hooks、[ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli) 和 `mpv`。
- `hermes-memory-reconciler` 默认读取 `${HERMES_HOME:-$HOME/.hermes}/memories/` 下的 Hermes 记忆文件；未来如果有 `memory-reconciler` CLI 会优先使用，没有 CLI 时按只读 fallback 流程执行。

---

## Skill 详情

### coding-music `0.1 beta`

#### 背景

当 AI Agent 承担了越来越多的实际编码工作，你的角色在转变——不再是写每一行代码，而是在审查、决策、指挥。这意味着你的注意力比以前更稀缺，而不是更宽裕。每一次 Claude 真正需要你判断的时刻——一个权限确认，一个关键决策——都值得你完整的专注。而当 Claude 自我执行任务时候，你可以稍微放松一下，耳机里享受喜爱的音乐。

#### 它做什么

编码时播放你喜欢的音乐。权限弹窗出现时自动暂停，你确认后自动恢复。不需要切窗口，不需要摘耳机，专注和节奏都没断。

可选开启：Claude 每次回复完毕也暂停，把节奏完全交还给你来决定何时继续。

基于网易云音乐官方 CLI（[ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli)）和 Claude Code hook 系统构建。

**使用方式：**
```
/coding-music
```

---

### docai-audit

#### 背景

当 Cursor、Claude Code、Codex 成为标配开发工具，开发者接入一个云服务的方式正在改变——不再是人读文档再写代码，而是把文档发给 AI，或者让 AI 自行搜索选择服务提供方，直接生成集成代码。

这个转变对云服务和工具提出了新的要求：同样的服务，谁家的文档对 AI 理解、执行和跑通更友好？

docai-audit 就是来回答这个问题的。

#### 它做什么

输入一个云服务或开发工具的文档 URL，输出一份量化评估报告——这个平台对 AI coding 和 Agent 调用的支持程度到底在哪个层级。

适用于：

- **DevRel / 文档团队**，找到自家文档的 AI 适配缺口
- **Agent 开发者**，快速判断哪个平台对 AI coding 更友好

评分覆盖 5 个维度，直指 AI 调用链路的关键节点。

**使用方式：**
```
/docai-audit https://resend.com/docs
```

---

### gen-image-grounding `0.1 beta`

#### 背景

真实人物、地点、事件、产品、徽标、服装、建筑、海报文字等生图需求，直接丢给生图模型容易靠幻觉补细节。gen-image-grounding 在生图前先做搜索和参考图 grounding。

#### 它做什么

根据原始 prompt 规划搜索 query，调用已配置的文本搜索、图片搜索和网页读取 provider，下载参考图，然后输出 `gen_prompt`、`reference_images`、`facts`、`sources` 和 `warnings`，供下游生图模型使用。

已支持 Serper、火山引擎 Volcengine、Tavily、Firecrawl、Jina 等 provider 的环境变量接入。

**使用方式：**
```
/gen-image-grounding
```

---

### hermes-memory-reconciler `0.2 beta`

#### 背景

长期记忆用久了以后很容易变乱：用户偏好可能互相冲突，项目事实可能过期，低价值条目越积越多，甚至还可能把危险的 prompt 指令持久化进去。Hermes 的记忆尤其敏感，因为它会影响 agent 以后怎么理解用户。

hermes-memory-reconciler 的核心判断是：清理长期记忆不是简单删文件，而是信任问题。它应该先只读检查，把问题说清楚，只在真正影响长期行为的时候问用户，并且不能静默改记忆。

#### 它做什么

以只读优先的方式扫描检查 Hermes 的 `USER.md` 和 `MEMORY.md`。它会识别完全重复、偏好冲突、用户画像冲突、适用范围不清、低价值记忆、疑似过期记忆，以及危险指令型记忆。

需要用户判断时，它只问一个最关键的问题。用户裁决后，它生成 dry-run 的 Hermes memory action plan，比如 `add`、`replace`、`remove`。如果未来进入真实写入，必须先有 staged run，包含 `original/`、`proposed/`、`diffs/` 和 `manifest.json`，回滚也必须先预览。

**使用方式：**
```
/hermes-memory-reconciler
```
