# Report Writing

Write natural Chinese. The report is a 用户决策报告, not a scanner transcript. It should help the user decide what can be simplified, what should be kept, what only needs wording clarification, and what is just a coverage reminder.

Separate 基础筛查 and Agent 评估:

- 基础筛查 records facts and routes candidates.
- Agent 评估 reads descriptions and decides whether a group is truly confusing, clearly bounded, duplicated, or only worth mentioning.
- Final suggestions in `report.md` must come from Agent 评估. Do not turn raw flags, raw similarity scores, or raw related groups directly into cleanup advice.

Preferred report shape:

1. `## 整理结论`: start with user-actionable findings. Say which items can be considered for 归档候选, which should be kept, and which are maintenance notes.
2. `## 本次如何判断`: briefly explain the evaluation chain: basic screening -> description-based Agent 调用边界评估 -> final recommendations.
3. `## Agent 调用边界评估`: show whether similar skills would actually make Agent selection harder. Before the table, include a short 快速读法 explaining the judgment basis so the user does not have to infer why the table says 高 / 中 / 低.
4. `## 重点分组详情`: expand only the groups that need evidence, grouped by user decision type such as 高置信归档候选, 需要先明确边界, 建议保留, or 只提示不处理. This heading should sit at the same level as `## Agent 调用边界评估`, not as a nested afterthought.
5. `## 相似项概览`: summarize `similarity_candidates`, grouping them as 高置信重复, 可能混淆, 相似但边界明确, or 只提示不处理. If the report already uses `## 重点分组详情`, this can be a subsection there instead of a separate top-level heading.
6. `## 相关功能组概览`: summarize `capability_groups`, including `too_broad` coverage hints without item-by-item deep reading.
7. `## 建议下一步`: give concrete next actions in priority order.
8. `## 没有修改的内容`: state that SkillTriage only prepared reviewable files.

For Agent 调用边界评估, prefer this compact table:

| 分组 | 混淆风险 | Agent 判断 | 建议 |
|---|---|---|---|
| group name | 高 / 中 / 低 | 高置信重复 / 可能混淆 / 相似但边界明确 / 通用入口与专项流程 / 配套关系 / 只提示不处理 | 归档候选 / 调整 description / 保留 / 只提示不处理 |

Use prose after the table only for the groups where the user needs evidence to make a decision. Do not just provide a table and conclusion. 不要只给表格和结论. Give the user enough explanation to understand the judgment without reading raw JSON.

不要把相似直接写成混淆。功能类似但边界明确的 groups should be marked 保留, with the boundary stated plainly. Similarity from common verbs is not enough evidence for cleanup.

When `capability_groups` exist, call them "相关功能组" in user-facing Markdown. Include a Skill 库瘦身 section only when Agent 评估 can name a clear primary entrypoint, 归档候选, boundary clarification, 同类但边界清楚, 通用入口与专项流程, or 配套关系.

For `too_broad` groups, call them "宽泛功能组" or "覆盖提示"; do not list members one by one. If the group has `coverage_hint`, mention at most the domain, count, and recommended wording. Phrase it as coverage context, for example: "基础筛查发现一组网页/浏览器相关 skill 描述较宽泛，已作为覆盖提示保留；本次未因这个宽泛功能组逐项深读。"

For provider-separated tools, avoid saying "互补". Say "同类但边界清楚". Example pattern: two skills may share a broad domain, but if they operate on different services or data stores, keep both and state the boundary.

For broad skill plus workflow skill, say "通用入口与专项流程". Example pattern: a broad service entrypoint and a narrower cleanup, review, or publishing workflow can both be valuable when the narrower workflow has distinct operating steps.

Do not include internal report-review commentary in `report.md`. Avoid self-review hedges, implementation-note phrases, and future-iteration musings (the report is for the user, not for the team writing it). Put that material outside the user-facing report.

For `## 没有修改的内容`, use factual user-facing wording. Prefer: "本次只生成审阅材料，没有删除、归档、覆盖或改写任何已安装 skill。" If `backup` is `off`, add: "由于本次没有保存原始快照，如果你之后手动采用某个建议，恢复需要依赖你自己的 git、备份或原始来源。"

At the top of the report, state the evaluation scope:

- `quick`: "本次采用快速整理：基础筛查先缩小范围，Agent 评估再审阅候选项、相似项和你点名的 skill。它更快，但可能漏掉格式正常但语义上有问题的 skill。"
- `full`: "本次采用完整整理：Agent 评估会审阅当前运行环境中可发现的非 SkillTriage 自身 skill。它更慢，但更适合第一次整理或怀疑漏检时使用。"
- `selected`: "本次采用指定整理：Agent 评估只审阅你点名的 skill。"

If all `active_state` values are `unknown`, say once: "本次运行环境没有提供明确的启用状态信号，所以发现到文件不等于当前一定会触发。"

For description parser findings, avoid saying "缺少 description" unless `description_absent` is true. For parse-incomplete cases, say: "基础筛查没有稳定解析出 description，需要 Agent 复核；这不等于当前运行环境一定无法触发这个 skill。"

## 可读性复核

Before finalizing `report.md`, run a short 可读性复核. This is a writing pass, not a new analysis phase. Keep the report natural and decision-oriented; do not force every run into the exact same wording.

Check these points:

- Can the user see the main decision in the first screen: what can be considered for 归档候选, what should be kept, and what only needs attention?
- Does `## Agent 调用边界评估` explain the judgment basis before the table, with a 快速读法 for high / medium / low risk?
- Are detailed sections grouped under a clear top-level `## 重点分组详情` instead of a flat list of disconnected findings?
- Does every cleanup suggestion include evidence in plain language, such as same name + same description + same hash, explicit replacement text, or unclear trigger boundary?
- Are similar-but-clear groups described as 保留 with their boundary, instead of being framed as cleanup opportunities?
- Are plugin-managed or too-broad groups clearly marked as reminders or only worth mentioning, not direct local cleanup tasks?
- Does `## 建议下一步` give 2-4 concrete actions, in priority order, without making the user inspect raw artifacts first?
- Does the report avoid internal review language, future-iteration notes, and implementation commentary?

If the report feels like a scanner transcript, rewrite it once before delivery: lead with the user decision, then explain evidence, then give next steps.

## Proposal Wording

Use "建议先看" for priority. Use "归档候选" for archive review items. Do not say that SkillTriage deleted, archived, fixed, or recovered anything in version 1. It only prepares reviewable files.
