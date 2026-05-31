# AI Agent Skills

[中文版](./README.md)

A collection of AI Agent skills for Claude Code, Codex, Hermes, OpenClaw, and other general-purpose agent runtimes.

Each skill is a self-contained folder. `SKILL.md` holds the core instructions; references, templates, and scripts live alongside it. Drop a skill into your agent's skill directory and it works out of the box — no per-task setup needed. Skills are runtime-agnostic unless noted otherwise.

## Available Skills

| Skill | Best For | What It Does |
|-------|----------|--------------|
| [coding-music](./coding-music) | Claude Code | Plays music while you code; auto-pauses on permission prompts, resumes after you confirm |
| [coding-agent-fit](./coding-agent-fit) | Any coding agent | Scores how well a cloud service or dev tool supports Coding Agent integration |
| [gen-image-grounding](./gen-image-grounding) | Any generation agent | Searches for facts and visual references before image generation |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | Finds duplicates, conflicts, stale entries, and risky instructions in long-term memory |
| [shinkaskill](./shinkaskill) | Codex / Claude Code | Quality-checks a single skill's structure, trigger description, and eval results |
| [skill-triage](./skill-triage) | Codex / Claude Code | Finds duplicates and unclear boundaries across an installed skill library |

## Installation

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
```

For Hermes, OpenClaw, or other runtimes, copy the folder to the runtime's skill/plugin directory or import it as a Markdown instruction pack. Keep `agents/<runtime>.yaml`, `references/`, and `scripts/` together with `SKILL.md`.

Restart the agent runtime after copying if it doesn't pick up new skills automatically.

## Skills

### Coding Music `0.1 beta`

When an AI agent is doing the heavy lifting, your job is mostly reviewing and confirming. Permission prompts and key decisions need your attention; the rest of the time you can have music on.

Plays your NetEase Music liked songs while coding. Auto-pauses on permission prompts, resumes when you confirm. Optional: also pause when Claude finishes a response.

Requires [ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli), `mpv`, Python 3, Node.js 18+. See [coding-music/README.md](./coding-music/README.md) for setup.

```
/coding-music
```

---

### Coding Agent Fit

Give it a docs URL for any cloud service or developer tool. It returns an integration report: how smoothly a Coding Agent can get from docs to working code, where it's likely to get stuck, and what the service should fix first.

Scores 5 dimensions: service discovery, docs quality, agent tooling (CLI/MCP/Skill), integration friction, and maintenance signals. Useful for DevRel teams running self-checks and for agent developers evaluating platforms.

Requires Python 3 (probe script). See [coding-agent-fit/README.md](./coding-agent-fit/README.md) for scoring details.

```
/coding-agent-fit https://resend.com/docs
```

---

### Gen Image Grounding `0.1 beta`

For prompts involving real people, places, products, logos, or anything that needs factual accuracy — searches the web and image sources first, then hands structured results to the image model.

Outputs `gen_prompt`, `reference_images`, `facts`, `sources`, and `warnings`. Supports Serper, Volcengine, Tavily, Firecrawl, and Jina. Requires Python 3; runs in plan-only mode without API keys.

See [gen-image-grounding/README.md](./gen-image-grounding/README.md) for provider setup and output format.

```
/gen-image-grounding
```

---

### Hermes Memory Reconciler `0.2 beta`

Long-term memory gets messy: preferences conflict, facts go stale, old conclusions keep steering behavior, risky instructions slip through. This skill scans Hermes `USER.md` and `MEMORY.md`, surfaces the problems, and asks targeted questions to build a cleanup proposal. Nothing changes until you say so.

Reads from `${HERMES_HOME:-$HOME/.hermes}/memories/`. See [hermes-memory-reconciler/README.md](./hermes-memory-reconciler/README.md) for the full workflow and CLI commands.

```
/hermes-memory-reconciler
```

---

### ShinkaSkill `0.1 beta`

Pre-publish quality check for a single skill. Reads `SKILL.md`, referenced files, and scripts; checks structure, trigger clarity, and completeness; scores each rubric dimension with evidence. Optionally runs real eval via Codex or Claude Code subagents.

Differs from skill-triage: shinkaskill looks at one skill in depth, skill-triage looks across the whole library. Requires Node.js 20+.

See [shinkaskill/README.md](./shinkaskill/README.md) for installation and CLI usage.

```
/shinkaskill
```

---

### SkillTriage `0.3 beta`

As you install more skills over time, some end up with overlapping descriptions or unclear boundaries — the agent hesitates when picking which one to call.

Scans the current agent's skill library, separates true duplicates from similar-but-distinct skills, and flags descriptions that are too broad. Reports only by default; cleanup requires explicit confirmation. Supports preference memory so future reports better match your habits.

Requires Python 3 standard library. See [skill-triage/README.md](./skill-triage/README.md) for usage and output format.

```
/skill-triage
```
