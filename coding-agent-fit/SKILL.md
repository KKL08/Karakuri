---
name: coding-agent-fit
description: "Evaluate cloud services, API platforms, and developer tools for Coding Agent integration. Use for Coding Agent 接入评测, Claude Code/Cursor/Codex/Trae integration checks, llms.txt/Markdown docs checks, CLI/MCP/Skill support checks, OpenAPI/API/SDK documentation reviews, and integration friction analysis."
argument-hint: <docs-url>
---

# Coding Agent 接入评测

评测云服务、API 平台或开发者工具对 Coding Agent 的支持程度。核心目标是：开发者把接入任务交给 Claude Code、Cursor、Codex、Trae 等 Coding Agent 之后，Agent 能否找到服务入口、读懂资料、写出代码，并真正调用跑起来。

评测重点包括入口、文档、API/SDK/CLI/MCP/Skill、权限流程、示例质量、错误处理、版本变化和求助渠道。文档表达可以朴素，但接入路径必须清楚。

重要边界：

- CLI、MCP、Skill 都是辅助工具。谁更有价值，取决于它能帮 Agent 少查多少资料、少试多少次。
- CLI/MCP/Skill 可以加速接入，API reference、鉴权、错误码、限流、版本和生产接入说明仍要完整。
- 对个人开发者和 Coding Agent 来说，一个成熟 CLI 可以很有价值；缺少 MCP 不应自动重扣。
- 对云服务或 API 平台来说，缺少 API reference、OpenAPI/API Catalog、错误码、限流或版本说明，仍然是明显缺口。

## 流程

### 阶段 1：明确接入目标

先确认四件事，再开始打分：

1. 目标网站提供什么服务。
2. 目标属于哪类：云服务 / API 平台、开发者工具、Agent 工具、文档型站点、交易型服务，或混合型。
3. 开发者通常希望 Coding Agent 完成什么接入任务。
4. Agent 从发现入口到跑通第一个调用，中间最可能卡在哪一步。

开发者工具可以合理使用 N/A。云服务或 API 平台有 CLI/MCP 时，仍要检查 API 文档底座。

### 阶段 2：发现证据

先建立证据图，再评分。证据必须来自具体 URL、响应头、文件、页面内容、仓库或命令说明。

**步骤 1：解析输入 URL**

保留两个地址：

- `origin`: 协议和域名，例如 `https://platform.example.com`
- `input_url`: 用户给出的完整文档页，例如 `https://platform.example.com/developer/docs/guides/intro`

不要默认 AI 相关文件只放在站点根路径，也不要把 `/docs` 写死。很多文档站会挂在 `/developer`、`/developer/docs`、`/api/docs` 或语言前缀下。输入 URL 的每一层路径前缀，都要当成可能的文档挂载点检查。

**步骤 2：运行探测脚本**

```bash
python3 <skill-path>/scripts/probe.py <docs-url>
```

脚本会检查：

- origin，以及从输入 URL 推导出的文档挂载路径
- `llms.txt`, `llms-full.txt`
- `.md` 页面和 `Accept: text/markdown`
- OpenAPI, Swagger, API Catalog
- MCP 和 Agent 发现文件
- sitemap, robots.txt, mint.json
- `Link: rel="llms-txt"`、`x-llms-txt` 等响应头
- llms 索引里关于 MCP、CLI、AI coding tools、OpenAPI、SDK 的线索

重要判断规则：

如果 `https://host/llms.txt` 是 404，但 `https://host/docs/llms.txt`、`https://host/developer/llms.txt`、`https://host/developer/docs/llms.txt` 这类文档挂载路径存在，或者文档页链接到了这些索引，就标记为 **文档挂载路径下存在 llms.txt**。根路径缺失可以单独记为发现入口的小缺口。

**步骤 3：优先读取一手机器可读资料**

如果存在，按这个顺序读取：

1. `llms.txt`
2. `llms-full.txt`
3. 当前页面的 `.md` 版本
4. `Accept: text/markdown` 返回内容
5. sitemap, OpenAPI, API Catalog, MCP manifests, Skill index

只有一手资料暴露不全时，才用搜索补充官方页面或官方仓库。

**步骤 4：必要时做站内搜索**

按目标域名搜索：

1. `site:<domain> MCP OR "model context protocol" OR mcp-server`
2. `site:<domain> CLI OR "command line" OR "npm install" OR "brew install"`
3. `site:<domain> llms.txt OR "AI onboarding" OR "AI-friendly" OR "AI integration"`
4. `site:<domain> cursor rules OR AGENTS.md OR "Claude Code" OR Codex OR Trae`
5. `site:<domain> OpenAPI OR swagger OR "API reference" OR "API documentation"`
6. `site:<domain> SDK OR "code examples" OR quickstart OR "getting started"`
7. `site:<domain> error code OR rate limit OR retry OR troubleshooting OR FAQ`
8. `site:<domain> changelog OR status OR deprecation OR migration`
9. `site:<domain> oauth OR "openid" OR "well-known" OR "api catalog"`
10. `site:<domain> skill OR "agent skill" OR prompt OR rules`

只收集相关的一手 URL。第三方仓库只有官方明确维护时才算证据。

### 阶段 3：核对评分依据

如果用户希望边查边看，评分前先给出关键依据。用户要直接结果时，把依据压缩进最终报告。

按这些类目核对：

```markdown
## 评分依据

### 服务入口与发现
- [ ] 开发者入口 / docs / API 首页:
- [ ] llms.txt / llms-full.txt:
- [ ] sitemap / robots / Link header:
- [ ] 搜索结果与页面标题:

### 接入文档质量
- [ ] quickstart:
- [ ] API reference / OpenAPI / API Catalog:
- [ ] 鉴权 / 请求响应 schema:
- [ ] 错误码 / 限流 / 重试 / 版本:
- [ ] SDK / 示例代码:
- [ ] Markdown / 页面可读性:

### Agent 辅助工具
- [ ] CLI:
- [ ] MCP:
- [ ] Skill / Agent rules / AGENTS.md / prompt pack:
- [ ] Claude Code / Cursor / Codex / Trae 配置:
- [ ] 验证命令 / 诊断命令 / 结构化输出:

### 接入阻碍与风险
- [ ] 登录墙 / 权限申请 / API key 流程:
- [ ] 地区 / 套餐 / 额度 / 计费限制:
- [ ] 动态渲染 / 反爬 / bot 访问策略:
- [ ] 示例失效 / 版本不一致:
- [ ] 安全边界 / token scope / 数据权限:

### 维护与反馈机制
- [ ] changelog / release notes:
- [ ] status page:
- [ ] 版本迁移 / 弃用策略:
- [ ] 文档反馈 / support / issues:
```

### 阶段 4：评分

读取 `references/rubric.md`，按 5 个维度评分：

| # | 维度 | 权重 |
|---|------|------|
| 1 | 服务入口与发现 | 15% |
| 2 | 接入文档质量 | 30% |
| 3 | Agent 辅助工具 | 20% |
| 4 | 接入阻碍与风险 | 20% |
| 5 | 维护与反馈机制 | 15% |

每个维度都要写清：

1. 本维度用了哪些证据。
2. 证据项或扣分项怎么计算。
3. 是否触发最高分限制。
4. 为什么给这个分数。

同时给出：

- **Agent 接入把握**: 高 / 中 / 低。
- **人工介入点**: 无需 / 需要拿 key / 需要补 API 判断 / 需要人工排障 / 需要联系销售或支持。

### 阶段 5：改进建议

建议要能落地。每条建议包含：

- 问题。
- 为什么会影响 Coding Agent 接入。
- 优先级和工作量。
- 预期提分。
- 验收方式。
- 可以直接交给 Coding Agent 的修复提示。

## 报告模板

输出简体中文。语气按技术文档来写：直接、清楚、有证据。

```markdown
# Coding Agent 接入评测

**目标网站:** <URL>
**评测时间:** <date>
**网站类型:** <云服务 / API 平台 / 开发者工具 / Agent 工具 / 文档型站点 / 交易型服务 / 混合型>
**总分:** <score>/100 — 等级: <grade>

**Agent 接入把握:** <高 / 中 / 低>
**人工介入点:** <无明显人工介入 / 需要拿 key / 需要补 API 判断 / 需要人工排障 / 需要联系销售或支持>

## 核心判断

<直接说明这个服务交给 Claude Code / Cursor / Codex 接入时大概有多顺。说清主要优势、最大卡点，以及 CLI/MCP/Skill/API 文档各自提供了什么帮助。>

## 接入路径

1. <Agent 如何找到入口。>
2. <Agent 如何读取文档并定位接入资料。>
3. <Agent 如何拿到鉴权、SDK、API 或工具信息。>
4. <Agent 如何生成并验证接入代码。>
5. <Agent 最可能卡住的一步。>

## 评分依据

<按 Phase 3 checklist 简写，必须引用具体 URL。>

## 评分概览

| 维度 | 权重 | 得分(1-5) | 加权贡献 |
|------|------|-----------|----------|
| 服务入口与发现 | 15% | x | x.xx |
| 接入文档质量 | 30% | x | x.xx |
| Agent 辅助工具 | 20% | x | x.xx |
| 接入阻碍与风险 | 20% | x | x.xx |
| 维护与反馈机制 | 15% | x | x.xx |
| **合计** | **100%** | — | **x.xx** |

## 各维度详情

### 1. 服务入口与发现 (15%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**判断:**
<score rationale>

**建议:**
- <specific actionable recommendation>

### 2. 接入文档质量 (30%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**判断:**
<score rationale>

**建议:**
- <specific actionable recommendation>

### 3. Agent 辅助工具 (20%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**判断:**
<score rationale>

**建议:**
- <specific actionable recommendation>

### 4. 接入阻碍与风险 (20%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**最可能卡住的一步:**
<specific failure point>

**建议:**
- <specific actionable recommendation>

### 5. 维护与反馈机制 (15%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**判断:**
<score rationale>

**建议:**
- <specific actionable recommendation>

## 最该先改的 3 件事

1. **<action>** (优先级: P0/P1/P2, 工作量: S/M/L)
   <why this matters and expected score impact>

   **验收方式:**
   ```text
   <how to verify the fix>
   ```

   **给 Coding Agent 的修复提示:**
   ```text
   <copy-paste ready implementation prompt>
   ```

2. **<action>** (优先级: P0/P1/P2, 工作量: S/M/L)
   <why this matters and expected score impact>

   **验收方式:**
   ```text
   <how to verify the fix>
   ```

   **给 Coding Agent 的修复提示:**
   ```text
   <copy-paste ready implementation prompt>
   ```

3. **<action>** (优先级: P0/P1/P2, 工作量: S/M/L)
   <why this matters and expected score impact>

   **验收方式:**
   ```text
   <how to verify the fix>
   ```

   **给 Coding Agent 的修复提示:**
   ```text
   <copy-paste ready implementation prompt>
   ```
```

## 注意事项

- 证据要具体：URL、响应头、文件路径、内容片段、官方仓库、命令示例、关键词命中都可以。
- 判定 llms.txt 缺失前，必须检查根路径、文档挂载路径、响应头、`.md` 和 `Accept: text/markdown`。
- CLI、MCP、Skill 不能和完整 API 文档混为一谈。
- 如果 CLI、SDK 或 Skill 已经提供了可靠接入路径，缺少 MCP 不应主导评分。
- 云服务和 API 平台缺 API spec、错误处理、限流、鉴权或版本说明时，即使有 CLI/MCP/Skill，也要扣分。
- 页面需要点击才能复制内容，但同样内容可通过 Markdown 或内容协商读取时，按机器可读处理。
