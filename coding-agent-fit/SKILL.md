---
name: coding-agent-fit
description: "Evaluate cloud services, API platforms, and developer tools for Coding Agent integration. Use for Coding Agent 接入评测, Claude Code/Cursor/Codex/Trae integration checks, llms.txt/Markdown docs checks, CLI/MCP/Skill support checks, OpenAPI/API/SDK documentation reviews, and integration friction analysis."
argument-hint: <docs-url>
---

# Coding Agent 接入评测

评测云服务、API 平台或开发者工具对 Coding Agent 的支持程度。核心目标：开发者把接入任务交给 Claude Code、Cursor、Codex、Trae 等 Coding Agent 之后，Agent 能否找到入口、读懂资料、写出代码、真正跑通，并且长期可靠。

评测重点：入口、文档、API/SDK/CLI/MCP/Skill、权限流程、示例质量、错误处理、版本、求助渠道。文档表达可以朴素，但接入路径必须清楚。

**重要边界**

- CLI、MCP、Skill 都是辅助工具，谁更有价值取决于能帮 Agent 少查多少资料、少试多少次。
- CLI / MCP / Skill 可以加速接入，API reference、鉴权、错误码、限流、版本仍要完整。
- 缺 MCP 不应自动重扣——成熟 CLI 对个人开发者和 Coding Agent 同样有价值。
- 云服务 / API 平台缺 API reference / 鉴权 / 错误码 / 限流 / 版本说明是明显缺口，即使有 CLI/MCP/Skill 也不能补。

## 流程

### 阶段 1：明确接入目标

确认四件事再开始：

1. 目标网站提供什么服务。
2. 目标属于哪类：云服务 / API 平台、开发者工具、Agent 工具、文档型站点，或混合型。
3. 开发者希望 Coding Agent 完成什么接入任务（用户明示了就用那个；没明示就按站点类型推一个典型任务并确认）。
4. Agent 从发现入口到跑通第一个调用，中间最可能卡在哪。

### 阶段 2：发现证据

先建立证据图，再评分。证据必须来自具体 URL、响应头、文件、页面内容、仓库或命令说明。

**步骤 0：先扫 AI Agent 专属章节**

llms.txt 顶部、docs 入口、站点导航如有 "AI Agent" / "LLM" / "agentic" / "AI coding tools" 章节，先读这段——这是站点为 Agent 接入预先写的指引，能避免后续很多不必要的试错，本身是评分加分项（维度 2 +2）。

**步骤 1：解析输入 URL**

保留两个地址：
- `origin`: 协议和域名
- `input_url`: 用户给的完整文档页

输入 URL 的每一层路径前缀都是可能的文档挂载点（`/developer`、`/developer/docs`、`/api/docs`、语言前缀）。同时考虑文档子域（`docs.host` / `developer.host` / `api.host`）。

**步骤 2：运行探测脚本**

```bash
python3 <skill-path>/scripts/probe.py <docs-url>
```

脚本输出结构：

```
{ input_url, base_url, summary, probes }
```

`summary` 是按 rubric 维度预消化的证据视图，包含 7 个 section：

- `ai_discovery`：llms.txt / llms-full / 信号命中 / link header / AI Agent 章节
- `api_spec`：OpenAPI / API Catalog / GraphQL
- `agent_tools`：MCP / Skills / 页面提及 CLI / MCP / Skill
- `docs_machine_readable`：.md / index.md / Accept: text/markdown
- `auth`：OAuth well-known
- `friction_signals`：TLS / robots / errors / rate limit / sandbox 等
- `maintenance_hints`：changelog / status page

评分时优先参考 `summary`，需要细节时回 `probes` 看具体 `attempts`。

**步骤 3：优先读取一手机器可读资料**

按这个顺序：

1. `llms.txt`（特别注意顶部 AI Agent 章节）
2. `llms-full.txt`
3. 当前页面 `.md` 版本
4. `Accept: text/markdown` 返回内容
5. sitemap, OpenAPI, API Catalog, MCP manifests, Skills index

只有一手资料暴露不全时才用搜索补充官方页面或仓库。

**步骤 4：必要时做站内搜索**

按目标域名搜：

1. `site:<domain> MCP OR "model context protocol"`
2. `site:<domain> CLI OR "command line" OR "npm install" OR "brew install"`
3. `site:<domain> llms.txt OR "AI onboarding" OR "AI-friendly" OR "agentic"`
4. `site:<domain> "Claude Code" OR Codex OR Cursor OR AGENTS.md`
5. `site:<domain> OpenAPI OR swagger OR GraphQL OR "API reference"`
6. `site:<domain> SDK OR quickstart OR "getting started"`
7. `site:<domain> "error code" OR "rate limit" OR retry`
8. `site:<domain> changelog OR status OR deprecation`
9. `site:<domain> oauth OR "well-known" OR "api catalog"`
10. `site:<domain> skill OR "agent skill" OR rules`

只收集相关的一手 URL。第三方仓库只有官方明确维护时才算证据。

**硬规则：服务能力断言必须有 URL 证据**

报告里出现"X 服务有 / 没有 Y 能力"时，必须有具体 URL 证据。无证据视为该能力缺失，不能凭印象写。

### 阶段 3：核对评分依据

```markdown
## 评分依据

### 服务入口与发现
- [ ] 开发者入口 / docs / API 首页:
- [ ] llms.txt / llms-full.txt:
- [ ] sitemap / robots / Link header:
- [ ] 搜索结果与页面标题:

### 接入文档质量
- [ ] quickstart:
- [ ] API reference / OpenAPI / API Catalog / GraphQL:
- [ ] 鉴权 / 请求响应 schema:
- [ ] 错误码 / 限流 / 重试 / 版本:
- [ ] SDK / 示例代码:
- [ ] Markdown / 页面可读性:
- [ ] AI Agent / LLM 专属章节:

### Agent 辅助工具
- [ ] CLI（含 doctor / verify / JSON 输出）:
- [ ] MCP（remote / local / well-known）:
- [ ] Skill / Agent rules / AGENTS.md / prompt pack:
- [ ] Claude Code / Cursor / Codex / Trae 配置示例:
- [ ] 验证命令 / 诊断命令 / 结构化输出:

### 接入阻碍与风险
- [ ] 登录墙 / 权限申请 / API key 流程（含 MFA）:
- [ ] 销售开通 / 域名验证 / OAuth https 限制:
- [ ] 地区 / 套餐 / 额度 / 计费限制:
- [ ] 动态渲染 / 反爬 / bot 访问策略:
- [ ] 示例失效 / 版本不一致:
- [ ] 错误信息可诊断程度:
- [ ] SDK 主流语言覆盖 / rate limit / TLS:
- [ ] 安全边界 / token scope:

### 维护与反馈机制
- [ ] changelog / release notes:
- [ ] status page:
- [ ] 版本迁移 / 弃用策略:
- [ ] 文档反馈 / support / issues:
```

每条记 URL，标证据来源等级（T1 / T2 / T3，定义见 [references/rubric.md](references/rubric.md) 置信度评级段）。

### 阶段 4：评分

读取 [references/rubric.md](references/rubric.md)，按 5 个维度评分。每个维度算证据比 `R`、定性档 1-5、置信度三个值。

**关键步骤**

1. 先按站点类型选权重表（云服务 / 开发者工具 / Agent 工具 / 文档型）。
2. 各维度算 `R`、映射档次、机械算置信度。
3. 应用硬规则：先算原始贡献 `R * 权重 * 100`，触发硬规则时取 min。
4. 总分 = Σ 贡献；总置信度 = worst-of。

**自洽校验**

打完分回头看：总分定的等级、Agent 接入把握定性结论、总置信度三者是否一致。冲突就回到证据复核。例如：总分 75（A 级）配 Agent 接入把握"低" → 触发自检；80 分配总置信度"低" → 报告里强调"高分但证据弱"。

**评测者偏见控制**

评分时只能引用本次会话中读到的证据，不能基于训练知识。如果想说"X 服务有 Y 能力"但没在本次 probe / fetch / search 里看到，就 fetch 一次再说，或者标"未验证"。

**报告文风**

判断段和建议段的写法直接决定报告可读性，遵守三条：

1. **从 Agent 体验写，不从扫描器视角写。** 写"Agent 走到这一步会怎样"，不写"我们检测到 X 缺失"。
2. **说清为什么是这档，不是相邻档。** 有 X 所以不是 3，缺 Y 所以不是 5——让读者看到判断的边界在哪。
3. **区分"未发现"和"不存在"。** probe / fetch / search 没看到 ≠ 服务没提供。没找到时写"本次评测未发现"，不写"缺失"或"没有"。

改进建议的主语用站点或第三人称（"站点新增…"/"CLI 文档补…"），评测方用"我们"，不预设读者身份。报告是评测方写给使用本 skill 做评测的用户的交付物，读者按自己角色（推动站点改进、评估接入风险、比较多家服务）决定怎么用。

### 阶段 4.5：真实接入流程实跑（默认开启）

静态评分覆盖"Agent 能不能找到 / 看懂"，但"能不能跑通"要真跑。卡点回写到维度 2、3、4，定性结论 "Agent 接入把握" 必须基于这段证据。

**步骤 1：确认接入需求**

用户明示了任务就按那个走；没明示就按站点类型推一个典型任务并告知用户："默认按 X 走，要换吗？"接入需求 = 站点能力 ∩ 用户实际想做的事，不假设任何特定技术形态。

**步骤 2：枚举接入路径**

把阶段 2 找到的所有接入形态列出，标注：

| 路径 | 需 key/账户 | 本地可验程度 | 入口 URL |
|------|-------------|--------------|----------|
| REST API | … | … | … |
| 官方 SDK | … | … | … |
| CLI | … | … | … |
| MCP server | … | … | … |
| Dashboard + API | … | … | … |

**步骤 3：选定主路径**

优先级：用户明示偏好 > Agent 友好度 > 文档完整度。说出理由。两条路径都强时允许同时跑短的那条做对照。

**步骤 4：执行**

按选定路径跑：

1. 找入口
2. 读对应 quickstart（顺便扫 AI Agent 专属章节）
3. 安装 / 配置 / 鉴权（会产生费用或副作用前先告知用户、等同意）
4. 写最小可运行片段
5. 实跑（发请求 / 跑命令 / 调 MCP 工具）
6. 拿到响应或卡住

每一步记录：通过 / 卡住 / 跳过；卡点原因；回查次数。

**步骤 5：安全边界**

会发邮件 / 发短信 / 下单 / 推送 / 部署 / 写数据的步骤，跑之前必须用户明确同意，尽量用 sandbox / test 收件人 / 临时 project。用户拒绝就降级 dry-run（写出代码不执行），仍计入证据。不创建付费资源，不持久写入用户数据，不把 key 落到 history / logs。

**步骤 6：卡点映射回维度 4**

每个实跑卡点必须先映射到 [rubric.md](references/rubric.md) 维度 4 的具体扣分项；映射不上 = 报告里提议新扣分项作为评测产出。

实跑覆盖到的维度，置信度的 `dry_run_verified` 设为 true。

### 阶段 5：改进建议

每条建议用两段式：

- **我们看到的：** 客观事实——站点现状和对 Agent 接入的实际影响。
- **改进方向：** 站点可以做什么、做完后的衡量标准。

附带元信息：优先级（P0/P1/P2）、工作量（S/M/L）、预期提分（要具体——"维度 2 +0.15 R，约 +4.5 总分"）。

主语用站点或第三人称，评测方用"我们"，不预设读者身份（不用"你"），不用"给 Coding Agent 的修复提示"——读者是使用本 skill 做评测的用户，他们拿改进建议去推动站点改进或评估接入风险。

**低置信度维度的改进建议优先级前置**：如果某维度证据偏弱（covered_ratio < 0.4），即使分数中等也要把"补可机读文档 / Agent 友好资源"作为 P0 建议，理由是"既能提分又能让评测更稳"。

## 报告模板

完整模板见 [references/report_template.md](references/report_template.md)。输出简体中文。语气按技术文档：直接、清楚、有证据。

## 注意事项

- 证据要具体：URL、响应头、文件路径、内容片段、官方仓库、命令示例、关键词命中都可以。
- 判定 llms.txt 缺失前，必须检查根路径、文档挂载路径、子域、响应头、`.md` 和 `Accept: text/markdown`。
- CLI、MCP、Skill 不能和完整 API 文档混为一谈。
- CLI / SDK / Skill 提供了可靠接入路径时，缺少 MCP 不应主导评分。
- 云服务和 API 平台缺 API spec、错误处理、限流、鉴权或版本说明时，即使有 CLI/MCP/Skill 也要扣分。
- 服务能力断言必须有 URL 证据，不能凭印象写。
- 站点类型选错权重表会让分数偏离，混合型时报告里明示用了哪套。
