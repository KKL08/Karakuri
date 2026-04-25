---
name: docai-audit
description: "Evaluate developer documentation for AI readiness across discoverability, personal/agent usability, enterprise API readiness, automation via CLI/MCP, and feedback loops. Use for doc AI audits, AI 友好度评估, llms.txt/Markdown indexing checks, Cursor/Claude Code/Codex/Cline compatibility, MCP/CLI/API documentation audits, and enterprise API onboarding readiness."
argument-hint: <docs-url>
---

# DocAI Audit — 开发文档 AI 友好度审计

Evaluate a developer documentation site in Chinese. The audit must distinguish three related but different questions:

1. **AI 能不能自动发现和读取文档**：llms.txt、Markdown、sitemap、响应头。
2. **个人/Agent 用户能不能快速用起来**：CLI、MCP、SDK、AI coding tool 配置。
3. **企业能不能稳定接入生产 API**：API spec、错误码、限流、鉴权、版本、排障。

CLI and MCP are not the same. For personal agent users, a strong CLI can be enough. For enterprise users, CLI/MCP should assist API onboarding but cannot replace complete API documentation and machine-readable specs.

## Workflow

### Phase 1: Discovery

Build a broad evidence map before scoring.

**Step 1 — Parse the input URL**

Keep both:
- `origin`: scheme + host, e.g. `https://platform.example.com`
- `input_url`: the exact docs page, e.g. `https://platform.example.com/docs/guides/intro`

Do not assume AI resources only live at the origin root. Many docs platforms mount them under `/docs`.

**Step 2 — Run the probe script**

```bash
python3 <skill-path>/scripts/probe.py <docs-url>
```

The probe checks:
- origin and likely docs mounts such as `/docs`
- `llms.txt`, `llms-full.txt`
- page Markdown through `.md` and `Accept: text/markdown`
- OpenAPI/Swagger/API Catalog
- MCP and agent discovery files
- sitemap, robots.txt, mint.json
- response headers such as `Link: rel="llms-txt"` and `x-llms-txt`
- signals inside llms indexes for MCP, CLI, AI coding tools, OpenAPI, SDK

Important interpretation rule:

If `https://host/llms.txt` is 404 but `https://host/docs/llms.txt` exists or the docs page links to it, mark llms.txt as **present under docs mount**, not missing. Note the root-path discoverability gap separately.

**Step 3 — Read first-party machine-readable sources first**

If available, inspect in this order:
1. `llms.txt`
2. `llms-full.txt`
3. current page `.md`
4. `Accept: text/markdown` output
5. sitemap/OpenAPI/API Catalog/MCP manifests

Use web search only to discover additional first-party pages or repositories that these sources do not expose.

**Step 4 — Broad search when needed**

Search the target domain for:

1. `site:<domain> MCP OR "model context protocol" OR mcp-server`
2. `site:<domain> llms.txt OR "AI onboarding" OR "AI-friendly" OR "AI integration"`
3. `site:<domain> cursorrules OR "cursor rules" OR AGENTS.md OR "AI skills" OR "AI coding"`
4. `site:<domain> OpenAPI OR swagger OR "API reference" OR "API documentation"`
5. `site:<domain> SDK OR CLI OR "code examples" OR quickstart OR "getting started"`
6. `site:<domain> changelog OR "error handling" OR troubleshooting OR FAQ`
7. `site:<domain> discord OR community OR feedback OR "rate this page"`
8. `site:<domain> oauth OR "openid" OR "well-known" OR "api catalog"`

Collect only relevant first-party URLs unless third-party repos are official.

**Step 5 — Discovery checklist**

When the user expects an interactive audit, show a short checklist before scoring. If the user asks for a direct answer, include the checklist briefly inside the final report instead of pausing.

Use these buckets:

```markdown
## 发现清单

### AI 可发现性与可读取性
- [ ] llms.txt / llms-full.txt:
- [ ] 页面 Markdown:
- [ ] sitemap / robots:
- [ ] 响应头 Link / x-llms-txt:

### 个人/Agent 用户可用性
- [ ] CLI:
- [ ] MCP:
- [ ] AI coding tools:
- [ ] SDK / quickstart:

### 企业 API 接入完整性
- [ ] OpenAPI / Swagger / API Catalog:
- [ ] API reference:
- [ ] 错误码 / 限流 / 排障:
- [ ] 版本变更 / 弃用策略:

### 自动化接入能力
- [ ] well-known MCP / Agent Skills:
- [ ] CLI/MCP 自动读取文档或生成配置:
- [ ] 可复制配置模板 / agent prompt:

### 反馈与迭代
- [ ] 页面反馈:
- [ ] 社区 / 工单 / 邮箱:
- [ ] Changelog:
```

### Phase 2: Evaluation

Read `references/rubric.md` and score 5 dimensions:

| # | 维度 | 权重 |
|---|------|------|
| 1 | AI 可发现性与可读取性 | 20% |
| 2 | 个人/Agent 用户可用性 | 20% |
| 3 | 企业 API 接入完整性 | 25% |
| 4 | 自动化接入能力 | 25% |
| 5 | 反馈与迭代 | 10% |

Also produce two audience-specific grades:

- **个人/Agent 用户友好度**: give more weight to CLI/MCP/AI coding tool setup.
- **企业 API 接入友好度**: give more weight to API specs, reliability, governance, and automated onboarding.

## Report Template

Output in Simplified Chinese.

```markdown
# DocAI Audit 评估报告

**目标站点:** <URL>
**评估时间:** <date>
**总分:** <score>/100 — 等级: <grade> (<label>)

**个人/Agent 用户友好度:** <grade> — <one-sentence reason>
**企业 API 接入友好度:** <grade> — <one-sentence reason>

## 核心判断

<直接说明它到底友好在哪里、不友好在哪里。区分 CLI/MCP/API 文档的边界。>

## 发现清单

<按 Phase 1 checklist 简写，必须引用具体 URL。>

## 评分概览

| 维度 | 权重 | 得分(1-5) | 加权分贡献 |
|------|------|-----------|-----------|
| AI 可发现性与可读取性 | 20% | x | x.xx |
| 个人/Agent 用户可用性 | 20% | x | x.xx |
| 企业 API 接入完整性 | 25% | x | x.xx |
| 自动化接入能力 | 25% | x | x.xx |
| 反馈与迭代 | 10% | x | x.xx |
| **合计** | **100%** | — | **x.xx** |

## 各维度详情

### 1. AI 可发现性与可读取性 (20%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**建议:**
- <specific actionable recommendation>

### 2. 个人/Agent 用户可用性 (20%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**建议:**
- <specific actionable recommendation>

### 3. 企业 API 接入完整性 (25%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**建议:**
- <specific actionable recommendation>

### 4. 自动化接入能力 (25%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**建议:**
- <specific actionable recommendation>

### 5. 反馈与迭代 (10%) — 得分: x/5

**证据:**
- <specific URL/evidence>

**建议:**
- <specific actionable recommendation>

## Top 3 改进建议

1. **<action>** (优先级: P0, 工作量: S/M/L)
   <reason and expected score impact>

   **修复参考：**
   ```text
   <copy-paste ready implementation instructions or file template>
   ```

2. **<action>** (优先级: P1, 工作量: S/M/L)
   <reason and expected score impact>

   **修复参考：**
   ```text
   <copy-paste ready implementation instructions or file template>
   ```

3. **<action>** (优先级: P1, 工作量: S/M/L)
   <reason and expected score impact>

   **修复参考：**
   ```text
   <copy-paste ready implementation instructions or file template>
   ```
```

## Important Notes

- Evidence must be specific: URLs, response headers, file paths, content snippets, or keyword matches.
- Do not mark llms.txt missing until you have checked origin root, docs mount candidates, response headers, `.md`, and `Accept: text/markdown`.
- Do not over-penalize lack of MCP when a strong CLI fully serves personal agent users.
- Do penalize enterprise readiness when API specs, error handling, rate limits, auth, or versioning are incomplete, even if CLI/MCP exists.
- If a page requires clicking UI to copy content but the same content is available as Markdown or via content negotiation, treat it as machine-readable.
