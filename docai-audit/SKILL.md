---
name: docai-audit
description: "Evaluate documentation sites for AI-friendliness across 5 dimensions (AI discoverability, API spec, code examples, AI tool integration, feedback). Use this skill whenever the user wants to audit a docs site for AI readiness, check how AI-friendly their documentation is, assess documentation quality for AI coding tools, or anything related to 'docai audit', 'AI 友好度评估', '文档 AI 可读性', 'docs AI audit'. Also trigger when users mention evaluating docs for Cursor, Claude Code, Copilot, or other AI coding tools compatibility."
argument-hint: <docs-url>
---

# DocAI Audit — 开发文档 AI 友好度审计

Evaluate a developer documentation site's AI-friendliness. Produce a structured Chinese report with scores across 12 dimensions, evidence, and actionable improvement suggestions.

## Two-Phase Workflow

This audit runs in two phases: **Discovery** (breadth scan) then **Evaluation** (depth assessment). Present the discovery checklist to the user between phases so they can add hints or confirm before deep evaluation.

### Phase 1: Discovery (广度扫描)

Goal: build a panoramic view of what AI-friendly features the docs site has.

**Step 1 — Parse URL**

Extract the base URL (scheme + host). If the user provides a deep path like `https://docs.example.com/api/v1/intro`, the base is `https://docs.example.com`.

**Step 2 — Run the probe script**

Execute the bundled probe script to check for well-known AI resources:

```bash
python3 <skill-path>/scripts/probe.py <base_url>
```

This returns JSON with existence data for: `llms_txt`, `openapi`, `mcp_json`, `sitemap`, `robots_txt`, `mint_json`. Each entry has `exists`, `url`, and `content_preview`.

**Step 3 — Broad WebSearch**

Search for AI-related content on the target site. Run these searches (adapt the domain from the URL):

1. `site:<domain> MCP OR "model context protocol" OR mcp-server`
2. `site:<domain> llms.txt OR "AI onboarding" OR "AI-friendly" OR "AI integration"`
3. `site:<domain> cursorrules OR "cursor rules" OR AGENTS.md OR "AI skills" OR "AI coding"`
4. `site:<domain> OpenAPI OR swagger OR "API reference" OR "API documentation"`
5. `site:<domain> SDK OR CLI OR "code examples" OR quickstart OR "getting started"`
6. `site:<domain> changelog OR "error handling" OR troubleshooting OR FAQ`
7. `site:<domain> discord OR community OR feedback OR "rate this page"`

Use WebSearch for these. Collect all discovered page URLs.

**Step 4 — Present Discovery Checklist**

Compile findings into a structured checklist organized by the 5 dimensions. For each dimension, note:
- Found resources/pages (with URLs)
- Not found / no evidence

Present this to the user in Chinese. Example format:

```
## 发现清单

- [x] llms.txt: 存在 (https://docs.example.com/llms.txt)
- [ ] AI onboarding 专属页面: 未发现
- [x] OpenAPI spec: 存在 (https://docs.example.com/openapi.json)
- [ ] MCP Server: 未发现
- [x] Cursor 集成指南: https://docs.example.com/guides/cursor
- [x] CLI 工具文档: https://docs.example.com/cli
...
```

Ask the user: "以上是初步发现清单，是否有补充线索？确认后我将进入深度评估。"

---

### Phase 2: Evaluation (深度评估)

Goal: fetch discovered pages, score each dimension, produce the final report.

**Step 5 — Targeted WebFetch**

Fetch the key pages discovered in Phase 1. Prioritize:
- AI onboarding / AI-specific pages
- MCP documentation
- API reference pages
- Quickstart / Getting Started
- Error handling / troubleshooting pages
- Changelog / feedback pages

For each page, extract observations relevant to the 5 dimensions: code examples count/quality/languages, API endpoints and naming consistency, error codes, MCP/CLI/AI tool mentions, heading structure, content density, feedback mechanisms, etc.

**Step 6 — Score Each Dimension**

Read the detailed rubric from `references/rubric.md` and score each of the **5 dimensions** on a **1–5 integer scale**:

- **5** = 卓越（行业标杆）
- **4** = 良好（有明确 AI 友好设计意图）
- **3** = 及格（满足基本要求，无主动 AI 适配）
- **2** = 不足（有少量相关内容，远不够用）
- **1** = 缺失（完全没有相关内容）

For dimensions with discovered content: strictly match rubric criteria, cite specific evidence.
For dimensions with no discovered content: score 1, noting "未检测到相关内容".
For dimensions not applicable (e.g., API spec for non-API docs): mark "N/A" and exclude from weight.

The 5 dimensions and their weights:

| # | 维度 | 权重 |
|---|------|------|
| 1 | AI 可发现性 | 15% |
| 2 | 文档与 API 规范 | 25% |
| 3 | 代码示例质量 | 20% |
| 4 | AI 工具接入 | 30% |
| 5 | 反馈与迭代 | 10% |

**维度 4 特殊规则：** 若站点有完善 CLI（评估为 4–5 分级别），MCP 缺失的扣分幅度减半。无 CLI 且无 MCP，该维度上限为 2 分。

**Step 7 — Compute Total Score**

```
原始加权分 = Σ(维度分数 × 权重)           // 范围 1.0 ~ 5.0
百分制总分 = (原始加权分 - 1) / 4 × 100   // 映射到 0 ~ 100
```

If a dimension is N/A, exclude it and re-normalize remaining weights to sum to 100%.

Apply the grading scale: S(90-100), A(75-89), B(60-74), C(40-59), D(20-39), F(0-19).

**Step 8 — Generate Report**

Output the full report in Chinese using this exact template:

```markdown
# DocAI Audit 评估报告

**目标站点:** <URL>
**评估时间:** <date>
**总分:** <score>/100 — 等级: <grade> (<label>)

---

## 评分概览

| 维度 | 权重 | 得分(1-5) | 加权分贡献 |
|------|------|-----------|-----------|
| AI 可发现性 | 15% | x | x.xx |
| 文档与 API 规范 | 25% | x | x.xx |
| 代码示例质量 | 20% | x | x.xx |
| AI 工具接入 | 30% | x | x.xx |
| 反馈与迭代 | 10% | x | x.xx |
| **合计** | **100%** | — | **x.xx** |

## 各维度详情

### 1. AI 可发现性 (15%) — 得分: x/5

**证据:**
- <evidence item>
- <evidence item>

**建议:**
- <specific actionable recommendation>

### 2. 文档与 API 规范 (25%) — 得分: x/5

**证据:**
- <evidence item>

**建议:**
- <specific actionable recommendation>

### 3. 代码示例质量 (20%) — 得分: x/5

**证据:**
- <evidence item>

**建议:**
- <specific actionable recommendation>

### 4. AI 工具接入 (30%) — 得分: x/5

**证据:**
- <evidence item>

**建议:**
- <specific actionable recommendation>

### 5. 反馈与迭代 (10%) — 得分: x/5

**证据:**
- <evidence item>

**建议:**
- <specific actionable recommendation>

## Top 3 改进建议

1. **<action>** (优先级: P0, 工作量: S/M/L)
   <reason and expected score impact>

2. **<action>** (优先级: P1, 工作量: S/M/L)
   <reason and expected score impact>

3. **<action>** (优先级: P1, 工作量: S/M/L)
   <reason and expected score impact>
```

## Important Notes

- All report output should be in **Simplified Chinese**
- Evidence must be **specific** — cite actual URLs, file contents, keyword matches. Do not use vague language like "seems good"
- The Top 3 suggestions should focus on **highest ROI improvements** — high weight dimensions with low scores where small effort yields big gains
- If WebFetch fails for a page, note it and adjust scoring accordingly rather than guessing
- For non-API documentation sites (tutorials, guides without REST endpoints), mark 维度 2「文档与 API 规范」as "不适用" and exclude from weighted total
