# 🤖 Coding Agent 接入评测

你知道那种感觉吗——把接入任务丢给 Claude Code 或 Cursor，然后看它能不能自己找到入口、看懂文档、写出能跑的代码。这个项目评测的就是这件事：云服务、API 平台和开发者工具对 Coding Agent 的支持到底到不到位。

## 🔧 怎么用

```bash
/coding-agent-fit <docs-url>
```

扔一个文档 URL 进去，出来的是一份中文评测报告。不用看几十页文档自己判断，工具帮你跑探测、读结构、给分数。

## 📊 评分维度

| # | 维度 | 权重 | 关注点 |
|---|------|------|--------|
| 1 | 服务入口与发现 | 15% | Agent 能不能自己找到入口——llms.txt、sitemap、文档首页、搜索引擎可见性 |
| 2 | 接入文档质量 | 30% | quickstart 能不能用、API reference 全不全、鉴权写得清不清楚、有没有错误码和 SDK 示例 |
| 3 | Agent 辅助工具 | 20% | CLI、MCP Server、Skill 包、OpenAPI spec、一键验证命令 |
| 4 | 接入阻碍与风险 | 20% | 登录墙挡不挡、权限流程绕不绕、网站有没有反爬、示例代码过没过期、版本对得上吗 |
| 5 | 维护与反馈机制 | 15% | changelog 在哪儿、status page 有没有、弃用策略说明了吗、文档有没有反馈渠道 |

每个维度 1–5 分，加权后折算成 100 分制。一眼看出哪块拖后腿。

## 🔍 评测流程

**1. 明确接入目标** —— 先搞清楚这家服务是干什么的，Agent 最可能卡在哪一步。别一上来就跑脚本。

**2. 发现证据 + 探测** —— 运行 `scripts/probe.py`，它会自动检查下面这些东西。不依赖第三方库，Python 3 标准库直接跑：

```bash
python3 scripts/probe.py <docs-url>
```

脚本覆盖：
- llms.txt / llms-full.txt（根路径 + 文档挂载路径）
- `.md` 页面和 `Accept: text/markdown` 内容协商
- OpenAPI / Swagger / API Catalog
- MCP 和 Agent 发现文件
- sitemap、robots.txt、mint.json
- 响应头里的 `Link: rel="llms-txt"`

如果脚本漏了什么，手动补一轮站内搜索。

**3. 核对评分依据** —— 按 checklist 逐项记录证据 URL，别空口给分。

**4. 评分** —— 读 `references/rubric.md`，按维度打分，写清楚判断理由。

**5. 改进建议** —— 每条建议包含：具体问题、影响、优先级、预估工作量、预期能提几分、怎么验收。

## 📋 报告里有什么

- 总分 + 等级
- Agent 接入把握（高 / 中 / 低）—— 这个结论直接告诉开发者能不能放心把接入任务交给 Agent
- 需要人工介入的关键点
- 完整接入路径（从发现入口到跑通第一个调用）
- 各维度评分、证据和判断理由
- **最该先改的 3 件事**，附带给 Coding Agent 的修复提示——服务方可以直接拿去当改进清单

## ⚠️ 关键判断规则

这些是评分时容易踩进去的坑，先写清楚：

- CLI、MCP、Skill 是加分项，但不能替代完整的 API 文档。文档烂，辅助工具再多也救不回来。
- 有成熟的 CLI 但没有 MCP？不因为这个自动扣分。
- 云服务如果缺 API reference、错误码、限流说明或版本说明，就算有 CLI/MCP，该扣的分照扣。
- 判定 llms.txt 缺失之前，必须把根路径、文档挂载路径和响应头全都查一遍。

## 📁 目录结构

```
coding-agent-fit/
  SKILL.md          # 核心指令
  scripts/          # probe.py 探测脚本
  references/       # rubric.md 评分标准
  evals/            # 评测样例
```
