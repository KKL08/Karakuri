# Runtime Adapters

Adapters discover skills for one runtime and normalize them into the same inventory shape. Codex and Claude Code are the first adapters. Future runtimes add a new adapter file without changing report, proposal, or recovery output formats.

Supported Claude Code plugin layouts include:

- `~/.claude/plugins/marketplaces/<plugin>/SKILL.md`
- `~/.claude/plugins/marketplaces/<plugin>/skills/<skill>/SKILL.md`
- `~/.claude/plugins/localdev/<plugin>/skills/<skill>/SKILL.md`
- `~/.claude/plugins/cache/**/SKILL.md`

## Skill Identity

`name` is user-facing and may repeat across roots, plugin packages, or providers. `skill_id` is the machine-facing primary key and must be unique within one run.

Scanner adapters first produce a readable base id in the form `<runtime>:<source_type>:<name>@<source_id>`. If that base id appears more than once in the same run, SkillTriage appends a deterministic suffix derived from the skill directory relative to its source root:

`<runtime>:<source_type>:<name>@<source_id>#<relative-path-slug>-<path-hash>`

This keeps normal ids readable while preventing plugin-managed skills such as `discord/access`, `telegram/access`, or provider-specific duplicates from collapsing into one item. Reports should still use `name` and path evidence for human-facing explanation; JSON artifacts should use `skill_id` for joins.
