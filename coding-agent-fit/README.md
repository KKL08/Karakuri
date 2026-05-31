# Coding Agent 接入评测

评测云服务、API 平台或开发者工具对 Coding Agent 的支持程度。核心问题：开发者把接入任务交给 Claude Code、Cursor、Codex、Trae 之后，Agent 能不能找到入口、读懂资料、写出代码并跑通。

## 使用

```
/coding-agent-fit https://resend.com/docs
```

输入文档 URL，输出一份中文评测报告。

## 评分维度

| # | 维度 | 权重 | 关注点 |
|---|------|------|--------|
| 1 | 服务入口与发现 | 15% | llms.txt、sitemap、文档首页、搜索可见性 |
| 2 | 接入文档质量 | 30% | quickstart、API reference、鉴权、错误码、SDK、示例 |
| 3 | Agent 辅助工具 | 20% | CLI、MCP、Skill、OpenAPI、验证命令 |
| 4 | 接入阻碍与风险 | 20% | 登录墙、权限流程、反爬、示例失效、版本不一致 |
| 5 | 维护与反馈机制 | 15% | changelog、status page、弃用策略、文档反馈渠道 |

每个维度 1-5 分，加权后折算为 100 分制总分。

## 流程

1. **明确接入目标**：确认服务类型、典型接入任务、Agent 最可能卡住的步骤。
2. **发现证据**：运行 `scripts/probe.py` 探测 llms.txt、OpenAPI、MCP manifest 等机器可读资料；必要时做站内搜索补充。
3. **核对评分依据**：按 checklist 逐项记录证据 URL。
4. **评分**：读取 `references/rubric.md`，按维度打分并写明判断理由。
5. **改进建议**：每条建议包含问题、影响、优先级、工作量、预期提分和验收方式。

## 探测脚本

```bash
python3 scripts/probe.py <docs-url>
```

脚本会检查：
- llms.txt / llms-full.txt（根路径和文档挂载路径）
- `.md` 页面和 `Accept: text/markdown` 内容协商
- OpenAPI / Swagger / API Catalog
- MCP 和 Agent 发现文件
- sitemap、robots.txt、mint.json
- 响应头中的 `Link: rel="llms-txt"`

不需要额外依赖，Python 3 标准库就够。

## 输出

报告包含：
- 总分和等级
- Agent 接入把握（高/中/低）
- 人工介入点说明
- 接入路径（从发现入口到跑通第一个调用）
- 各维度评分、证据和建议
- 最该先改的 3 件事（含给 Coding Agent 的修复提示）

## 关键判断规则

- CLI、MCP、Skill 是辅助工具，不能替代完整 API 文档。
- 有成熟 CLI 但没有 MCP 不应自动重扣。
- 云服务缺 API reference、错误码、限流或版本说明，即使有 CLI/MCP 也要扣分。
- 判定 llms.txt 缺失前，必须检查根路径、文档挂载路径和响应头。

## 目录结构

```
coding-agent-fit/
  SKILL.md          # 核心指令
  scripts/          # probe.py 探测脚本
  references/       # rubric.md 评分标准
  evals/            # 评测样例
```
