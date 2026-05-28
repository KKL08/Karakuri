# AI Agent Skills 合集

[English](./README.en.md)

这里提供一些 AI Agent skill，支持在 Claude Code、Codex、Hermes、OpenClaw 等通用 Agent 里使用。

每个 skill 对应一个具体工作流：`SKILL.md` 是核心指令，配套的参考资料、模板和脚本都放在同一目录下。agent 遇到同类任务时可以整套复用，省去重复搭流程的成本。

skill 默认通用、可跨 runtime 迁移；个别依赖特定 runtime 或外部工具的，会单独注明。

## 可用 Skills

| Skill | 适用对象 | 说明 |
|-------|----------|------|
| [coding-music](./coding-music) | Claude Code | 编码时播放你喜欢的音乐；Claude 请求权限时自动暂停，确认后继续播放 |
| [docai-audit](./docai-audit) | 通用 coding agent | 扫描开发文档的 AI 友好度，从 5 个维度评估它是否方便 AI 理解、调用和跑通 |
| [gen-image-grounding](./gen-image-grounding) | 通用生成类 agent | 生图前先搜索网页和参考图，整理事实、来源、参考图片和风险提示 |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | 扫描 Hermes 长期记忆里的重复、冲突、过期、范围不清和存在疑似风险的指令型记忆 |
| [shinkaskill](./shinkaskill) | Codex / Claude Code | 检查单个 Agent Skill 的结构、触发描述、引用文件和真实 eval 结果，按 rubric 生成中文报告和改进建议 |
| [skill-triage](./skill-triage) | Codex / Claude Code | 检查当前 agent 的 skill 库，识别重复、相似和边界不清的 skill；用户选择整理后，可把偏好记为后续提示 |

## 如何安装

每个 skill 都是一个独立文件夹。把需要的文件夹复制到你的 agent runtime 使用的 skill 目录即可：

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex 本地 skills
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
```

如果你使用的是 Hermes、OpenClaw 或其他 runtime，可以放到该 runtime 配置的 skill/plugin 目录里，也可以把整个文件夹作为 Markdown 指令包导入。skill 里如果有 `agents/<runtime>.yaml`、`references/` 或 `scripts/`，需要和 `SKILL.md` 一起保留。

复制后，如果目标 agent 不支持热加载，就重启或重新加载对应 runtime。

## 依赖

- 一个能加载 `SKILL.md` skill 文件夹的 agent runtime，或者至少能引用 Markdown 指令文件夹的 agent 环境。
- 各 skill 的具体依赖见对应文件夹内的 README 或 `SKILL.md`。
- `coding-music` 仍然依赖 [Claude Code](https://claude.ai/code)、Claude Code hooks、[ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli) 和 `mpv`。
- `hermes-memory-reconciler` 默认读取 `${HERMES_HOME:-$HOME/.hermes}/memories/` 下的 Hermes 记忆文件，并结合可用的 CLI 或内置指引生成检查报告和整理建议。
- `shinkaskill` 需要 Node.js 20+。只做静态检查时不依赖外部 agent；真实 eval 需要当前环境里已登录的 Codex CLI 或 Claude Code CLI。当前环境暂时不能运行真实 eval 时，可以先使用静态检查。
- `skill-triage` 使用 Python 3 标准库脚本扫描本地 skill 文件夹，运行结果写入 `~/.skilltriage/runs/`；默认只生成报告。如果用户决定继续整理，它会先备份并请用户确认，确认后再执行，并保留回退材料。用户明确选择后，还可以把本次取舍记为偏好，用于后续报告提示。

---

## Skill 详情

### coding-music `0.1 beta`

#### 背景

当 AI Agent 承担越来越多实际编码工作，你的注意力会更多放在审查、决策和指挥上。Claude 真正需要你判断的时刻，比如权限确认或关键决策，值得被你及时看到并处理；Claude 自己执行任务时，你也可以稍微放松一下，继续听喜欢的音乐。

#### 它做什么

编码时播放你喜欢的音乐。权限弹窗出现时自动暂停，你确认后自动恢复。不需要切窗口，也不需要摘耳机，专注和节奏都能保持住。

可选开启：Claude 每次回复完毕也暂停，把节奏完全交还给你来决定何时继续。

基于网易云音乐官方 CLI（[ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli)）和 Claude Code hook 系统构建。

**使用方式：**
```
/coding-music
```

---

### docai-audit

#### 背景

当 Cursor、Claude Code、Codex 成为常用开发工具，开发者接入云服务的方式也在变化：很多时候，人会把文档交给 AI，或者让 AI 自行搜索服务提供方，再生成集成代码。

这个变化让开发文档多了一层新标准：它是否方便 AI 理解、执行和跑通。

docai-audit 就是来回答这个问题的。

#### 它做什么

输入一个云服务或开发工具的文档 URL，输出一份量化评估报告，说明这个平台对 AI coding 和 agent 调用的支持程度。

适用于：

- **DevRel / 文档团队**：找到自家文档对 AI 不够友好的地方
- **Agent 开发者**：快速判断一个平台是否适合交给 AI 集成

评分覆盖 5 个维度，重点看 AI 调用链路中的关键节点。

**使用方式：**
```
/docai-audit https://resend.com/docs
```

---

### gen-image-grounding `0.1 beta`

#### 背景

涉及真实人物、地点、事件、产品、徽标、服装、建筑、海报文字等内容的生图需求，最好先补足事实和视觉参考。gen-image-grounding 会在生图前完成搜索、搜图和参考材料整理。

#### 它做什么

根据原始 prompt 规划搜索 query，调用已配置的文本搜索、图片搜索和网页读取 provider，下载参考图，并输出 `gen_prompt`、`reference_images`、`facts`、`sources` 和 `warnings`，供下游生图模型使用。

已支持 Serper、火山引擎 Volcengine、Tavily、Firecrawl、Jina 等 provider 的环境变量接入。

**使用方式：**
```
/gen-image-grounding
```

---

### hermes-memory-reconciler `0.2 beta`

#### 背景

长期记忆用久了以后很容易变乱：用户偏好可能互相冲突，项目事实可能过期，旧结论可能继续影响判断，甚至还可能把存在风险的 prompt 指令保留下来。Hermes 的记忆尤其敏感，因为它会影响 agent 以后怎么理解用户。

hermes-memory-reconciler 会全面扫描检查，把问题识别出来，并整理成易于理解的报告，帮助用户判断哪些记忆需要合并、更新或移除。它不会在用户不知情的情况下改动长期记忆；当某些冲突会影响后续行为时，会把关键判断留给用户确认。

#### 它做什么

扫描检查 Hermes 的 `USER.md` 和 `MEMORY.md`。它会识别完全重复、偏好冲突、用户画像冲突、适用范围不清、疑似过期记忆，以及存在疑似风险的指令型记忆。

它会通过询问关键问题来确定一些冲突记忆的处理优先级。用户做出决定后，它会整理出一份记忆整理方案，说明哪些内容建议新增、替换或移除，方便后续审阅和执行。

**使用方式：**
```
/hermes-memory-reconciler
```

---

### shinkaskill `0.1 beta`

#### 背景

ShinkaSkill 面向的是单个 Agent Skill 的质量检查。它关注一份 skill 在发布或迭代前是否清楚、完整、可运行：`SKILL.md` 是否把触发条件和工作流说清楚，引用文件和脚本是否齐全，权限、失败处理和真实 eval 是否有明确边界。

整个 skill 库的扫描、重复度和误触发风险，交给 [skill-triage](./skill-triage)。ShinkaSkill 只围绕当前被检查的 skill 生成报告，把结构、说明、引用和运行结果拆开看，再给出分数、证据和改进建议。

#### 它做什么

ShinkaSkill 接收一个或多个 skill 路径，先做只读检查。即使一次传入多个路径，每份报告也会围绕单个 skill 独立生成。它会读取 `SKILL.md`、frontmatter、引用文件和脚本，检查结构完整性、触发描述、渐进加载、授权说明、runtime 绑定和可维护性。报告默认用中文生成，并按 rubric 给每个维度打分。

需要更接近真实使用时，可以让用户明确授权真实 eval。ShinkaSkill 会把被测 skill 复制到 run sandbox，通过 Codex 或 Claude Code adapter 启动 subagent 跑 prompts，再让 grader 逐项打分、comparator 做 A/B 判断。报告会区分静态检查和真实 eval；当前环境暂时不能运行真实 eval 时，会直接提示原因。

适合这些情况：

- 发布新 skill 前做质量检查。
- 排查某个 skill 为什么不容易被触发，或为什么触发后表现不稳定。
- 比较一次修改前后的效果。
- 为后续自动优化准备评分、证据和改动建议。

默认模式只读，不扫描 home 目录，不修改原始 skill。`propose` 和 `apply` 目前保留为安全入口，不会生成或应用 patch。完整安装和 CLI 用法见 [shinkaskill/README.md](./shinkaskill/README.md)。

**使用方式：**
```
/shinkaskill
```

---

### skill-triage `0.3 beta`

#### 背景

Agent 的 skill 库用久了以后会自然变多：有些 skill 只用过一两次就被遗忘，有些描述和能力范围很接近，导致 agent 在遇到任务时难以判断该调用哪一个。skill-triage 用来把这类混乱整理成一份可审阅的维护报告。

#### 它做什么

扫描当前 agent 里的 skill，生成事实清单，并把可能重复、相似或调用边界容易混淆的 skill 交给 agent 进一步评估。报告会把结果分清楚：哪些高度重复，哪些只是功能相近但边界明确，哪些描述太宽、容易让 agent 犹豫。

默认情况下，SkillTriage 只生成报告、建议和恢复说明，不会改动已安装的 skill。你决定继续整理时，它会先列出准备处理的项目；你确认后，才会进入整理执行。插件托管、系统托管和 merge/dedupe 类建议不会自动执行。

SkillTriage 还支持偏好记忆：每次你选择执行整理操作后，它可以根据本次选择生成偏好记忆草稿，等你确认后保存到本地偏好记录。之后再检查 skill 库时，这些偏好会作为提示和排序依据，让报告更贴近你的整理习惯。

**使用方式：**
```
/skill-triage
```
