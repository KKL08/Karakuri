# Agent Evaluation Rubric

Agent 评估 judges the `agent_evaluation_skill_ids` set and any `capability_groups` whose `status` is `tight` or `loose`. Groups whose `status` is `too_broad` are not evaluation targets — they are coverage hints that may be mentioned briefly in the report but must not be deep-read item-by-item. Look for unclear trigger descriptions, overly broad boundaries, overlap with another skill, content that should move into references, archive candidates, and safety review needs.

If a `too_broad` group has `coverage_hint`, the agent may cite `coverage_hint.recommended_wording` in the report's coverage section. Do not use `coverage_hint` as evidence that any member skill should be archived, merged, rewritten, or deeply evaluated.

Every suggestion needs evidence from path, description text, file shape, overlap explanation, user-selected scope, or capability group facts.

Before turning a description-related 基础筛查 flag into a suggestion, read the relevant frontmatter and decide whether the issue belongs to the skill or to SkillTriage parsing. If the runtime-facing description is acceptable but the parser was incomplete, record it as a parser coverage note rather than a cleanup suggestion.

## Agent 调用边界评估

相似不等于混淆。`similarity_candidates` and `capability_groups` are routing evidence, not conclusions. The Agent must read the relevant descriptions and decide whether the group would actually make skill selection harder during a real user task.

For every similarity group and every `tight` / `loose` 相关功能组, write a short boundary evaluation before making a recommendation:

- Agent 对 description 的理解: explain what each skill appears to handle, using its own description and path evidence.
- 可能混淆的用户请求: name one or two realistic request shapes that could match more than one skill in the group.
- 区分依据: identify the service boundary, data object, runtime, task stage, workflow scope, or source ownership that helps the Agent choose.
- 混淆风险: classify as 高, 中, or 低.
- 结论分类: choose one of the categories below.
- 建议动作: choose 保留, 调整 description, 归档候选, or 只提示不处理.

结论分类:

- 高置信重复: content, name, description, or trigger intent is effectively the same. Often a writable user copy and a plugin-managed copy. Recommend one primary entrypoint and mark the writable non-managed copy as 归档候选 when evidence is strong.
- 可能混淆: skills are not identical, but their descriptions do not give enough boundary information. A real user request could plausibly trigger more than one skill and leave the Agent unsure. Recommend 调整 description before recommending archive.
- 相似但边界明确: skills share a broad category, but service, data object, runtime, provider, or ownership boundary is clear. Recommend 保留 and explain the boundary.
- 通用入口与专项流程: one skill is a broad entrypoint and another is a narrower workflow. Keep both when the narrower workflow has distinct operating value; clarify which request shape should trigger each.
- 配套关系: skills naturally work in sequence or support different task stages, such as create vs verify, build vs test, or generate vs publish. Recommend 保留 and clarify order or trigger.
- 只提示不处理: plugin-managed, system-managed, uncertain, or `too_broad` groups. Mention selection risk or coverage context without direct modification proposals.

判断原则:

- If similarity mainly comes from common verbs such as read, search, write, manage, review, generate, or run, do not classify the group as 可能混淆 unless the object, service, or task stage is also unclear.
- If the descriptions already name clear service boundaries, data objects, runtimes, providers, or task stages, prefer 相似但边界明确 over 可能混淆.
- If a group is plugin-managed, the Agent may analyze selection confusion but must not propose direct edits or archive actions for those installed files.
- If a group is `too_broad`, do not deep-read every member. Summarize why it is broad, whether it suggests future full-mode review, and whether the descriptions are too generic at the domain level.

The final report should help the user maintain a small and clear skill library, not maximize the number of findings.
