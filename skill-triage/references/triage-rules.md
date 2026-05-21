# Triage Rules

基础筛查 is factual. It records file and metadata facts, then routes a smaller set of skills into Agent 评估.

基础筛查 may flag missing or malformed frontmatter, missing names, description parse status, unclear description length, long skill files, script presence, broken references, duplicate names, similar descriptions, capability groups, read-only sources, and self-scan.

Script presence and read-only source are fact flags, not standalone reasons to enter Agent 评估.

Description parsing rules:

- `description_absent` means no `description` key was found.
- `description_empty` means a `description` key exists but has no usable content.
- `description_parse_incomplete` means SkillTriage found description-like content but did not parse it with full confidence.
- `missing_description` is retained for compatibility and should only mirror `description_absent`.

Capability clustering rules:

- `capability_fingerprint` is a deterministic summary of domain tags, action tags, object tags, and trigger terms from name, directory, and description.
- `capability_groups` carry a `status` field with three values:
  - `tight`: small group with high pair density. Treat as a routing signal — its members are added to `agent_evaluation_skill_ids` and should be deeply evaluated.
  - `loose`: medium group with moderate pair density. Also a routing signal, but the agent should weight its findings less heavily than `tight` groups.
  - `too_broad`: large or sparsely-connected group. **Not** a routing signal. Members are *not* added to `agent_evaluation_skill_ids` based on the group alone. Treat as a coverage/noise hint only — useful for the report to flag "这次基础筛查在某个能力维度上发现很多项，可能存在过宽的描述模式", but never as evidence to deep-read all of them.
  - `too_broad.coverage_hint`: a short explanation block for reports. It explains why the group was emitted and why it did not route members into Agent 评估. It is not evidence for a proposal and must not trigger item-by-item reading.
- Capability groups do not mean automatic merge, deletion, or archive.
- A `tight` or `loose` capability group must be reviewed by Agent 评估 as duplicate, overlap, parent-child, complementary, or no action.

Do not treat parser limitations or capability groups as final skill-quality conclusions. `tight` and `loose` groups can route a skill into Agent 评估, but the report must state the Agent judgment separately. `too_broad` groups cannot route at all.

基础筛查 does not decide whether a skill is valuable. Final cleanup suggestions come from Agent 评估.
