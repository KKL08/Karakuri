# Claude Code Skills 合集

[English](./README.md)

一组 Claude Code skill，每个 skill 独立放在自己的文件夹，可单独安装。

## 可用 Skills

| Skill | 说明 |
|-------|------|
| [coding-music](./coding-music) | 编码时播放你喜欢的音乐 — 权限弹窗出现时自动暂停，确认后自动恢复 |
| [docai-audit](./docai-audit) | 开发文档 AI 友好度审计 — 评分覆盖 5 个维度，直指 AI 调用链路的关键节点 |

## 如何安装

将 skill 文件夹复制到 `~/.claude/skills/`：

```bash
git clone https://github.com/KKL08/Skill.git
cp -r Skill/<skill-name> ~/.claude/skills/
```

然后重启 Claude Code。

## 依赖

- [Claude Code](https://claude.ai/code)
- 各 skill 的具体依赖见对应文件夹内的 README

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
