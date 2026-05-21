# AI Agent Skills

[中文版](./README.md)

A collection of `SKILL.md`-style instruction packs for AI agent runtimes.

Each skill packages task-specific instructions, references, and optional scripts so an agent can run a workflow consistently. Skills are designed to be portable where possible, and runtime-specific requirements are called out explicitly.

## Available Skills

| Skill | Best Fit | Description |
|-------|----------|-------------|
| [coding-music](./coding-music) | Claude Code | Plays your liked songs while coding — auto-pauses when Claude asks for permission, resumes after you confirm |
| [docai-audit](./docai-audit) | Portable coding agents | Evaluates any docs site across 5 dimensions targeting the key nodes in an AI invocation chain |
| [gen-image-grounding](./gen-image-grounding) | Portable generation agents | Searches and retrieves visual references before image generation, then outputs a grounded generation spec |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | Scans and checks Hermes long-term memory for duplicates, conflicts, stale or low-signal entries, and unsafe instruction memories |
| [skill-triage](./skill-triage) | Codex and Claude Code | Reviews installed skills, finds duplicates or confusing overlaps, and writes reviewable cleanup reports without modifying skills |

## How to Install a Skill

Each skill is a folder. Copy the folder into the skill directory used by your agent runtime:

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex local skills
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
```

For Hermes, OpenClaw, or another runtime, use that runtime's configured skill/plugin directory, or import the folder content as runtime instructions. If the skill includes `agents/<runtime>.yaml`, `references/`, or `scripts/`, keep those files together with `SKILL.md`.

After copying, restart or reload the target agent runtime if it does not hot-load skills.

## Requirements

- An agent runtime that can load `SKILL.md` skill folders, or that lets you reference Markdown instruction folders.
- Skill-specific dependencies listed in each skill's README or `SKILL.md`.
- `coding-music` specifically requires [Claude Code](https://claude.ai/code), Claude Code hooks, [ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli), and `mpv`.
- `hermes-memory-reconciler` assumes Hermes memory files under `${HERMES_HOME:-$HOME/.hermes}/memories/`; a future `memory-reconciler` CLI is preferred, but the skill also defines a read-only manual fallback.
- `skill-triage` uses Python 3 standard-library scripts to scan local skill folders. It writes run artifacts under `~/.skilltriage/runs/` and does not modify installed skills by itself.

---

## Skill Details

### coding-music `0.1 beta`

#### Background

As AI agents take over more of the actual coding, your role shifts — you're no longer writing every line, you're reviewing, deciding, directing. When Claude is running on its own, you can lean back and enjoy your music. When it actually needs you — a permission prompt, a key decision — that moment deserves your full focus.

Your attention is scarcer than ever. coding-music makes sure it goes where it matters.

#### What it does

Plays your liked songs while you code. When Claude is working autonomously, music plays. When it needs your input, music pauses — automatically. Resumes once you confirm. No window switching, no taking off your headphones — your focus and rhythm stay intact.

Optionally, it can also pause whenever Claude finishes a response — you decide when to pick back up.

Built on NetEase Music's official CLI ([ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli)) and Claude Code's hook system.

**Usage:**
```
/coding-music
```

---

### docai-audit

#### Background

When Cursor, Claude Code, and Codex become standard dev tools, the way developers integrate cloud services changes. It's no longer "read the docs, write the code" — you send the docs to an AI, or let it search and pick the service itself, and it writes the integration for you.

That shift raises a new question for every cloud service and developer tool: whose docs are actually easy for AI to understand, execute against, and get working?

docai-audit answers that.

#### What it does

Drop in a cloud service or developer tool's docs URL, get back a quantified report on exactly where that platform stands for AI coding and agent integration.

Good for:

- **DevRel / docs teams** — find the gaps in your own docs' AI readiness
- **Agent developers** — quickly gauge how AI-friendly a platform really is before committing

Scores across 5 dimensions that target the critical nodes in an AI invocation chain.

**Usage:**
```
/docai-audit https://resend.com/docs
```

---

### gen-image-grounding `0.1 beta`

#### Background

Image generation prompts that depend on real people, places, events, products, logos, outfits, architecture, posters, or readable text often need search and visual references before generation. gen-image-grounding turns a raw image prompt into a grounded generation spec.

#### What it does

It plans search queries, collects web and image evidence through configured providers, downloads reference images, and outputs `gen_prompt`, `reference_images`, `facts`, `sources`, and `warnings` for downstream image models.

Providers include Serper, Volcengine, Tavily, Firecrawl, and Jina when configured by environment variables.

**Usage:**
```
/gen-image-grounding
```

---

### hermes-memory-reconciler `0.2 beta`

#### Background

Long-term agent memory gets messy over time. User preferences can conflict, project notes can become stale, and unsafe prompt-like instructions can accidentally become persistent memory. Hermes memory is especially sensitive because it affects how the agent understands the user in future sessions.

hermes-memory-reconciler treats memory cleanup as a trust problem: inspect first, summarize clearly, ask the user only for high-impact decisions, and never silently rewrite long-term memory.

#### What it does

Scans and checks Hermes `USER.md` and `MEMORY.md` in a read-only-first workflow. It looks for exact duplicates, preference conflicts, profile conflicts, scope ambiguity, low-signal entries, possible stale memory, and unsafe instruction-injection memories.

When a decision is needed, it asks one focused question, then produces a dry-run Hermes memory action plan such as `add`, `replace`, or `remove`. Any real write path must go through a staged run with `original/`, `proposed/`, `diffs/`, and `manifest.json`, with rollback preview before recovery.

**Usage:**
```
/hermes-memory-reconciler
```

---

### skill-triage `0.1 beta`

#### Background

Agent skill libraries tend to grow over time. Some skills are used once and forgotten; others overlap in description or task scope, making it harder for the agent to decide which one to call. SkillTriage helps turn that messy skill space into a reviewable maintenance report.

#### What it does

Scans the current agent runtime's skills, records a factual inventory, and routes likely duplicates or confusingly similar skills into Agent evaluation. The final report separates high-confidence duplicates from related-but-clearly-bounded skills, and calls out broad groups that may need future attention.

It is read-only by default: SkillTriage prepares reports, proposals, and recovery notes, but does not delete, archive, overwrite, or rewrite installed skills on its own.

**Usage:**
```
/skill-triage
```
