# AI Agent Skills

[中文版](./README.md)

This repository collects `SKILL.md`-style instruction packs for AI agent runtimes such as Claude Code, Codex, Hermes, and other systems that can load Markdown-based workflows.

Each skill is organized around one concrete workflow. The main instructions live in `SKILL.md`, with any references, templates, or helper scripts kept in the same folder. That makes the workflow easier for an agent to reuse consistently. The skills are designed to stay portable where possible, and runtime-specific requirements are called out in the relevant skill notes.

## Available Skills

| Skill | Best Fit | Description |
|-------|----------|-------------|
| [coding-music](./coding-music) | Claude Code | Plays your favorite music while coding; pauses when Claude asks for permission and resumes after you confirm |
| [docai-audit](./docai-audit) | Portable coding agents | Reviews developer docs for AI readiness across 5 dimensions: understanding, integration, execution, recovery, and agent usability |
| [gen-image-grounding](./gen-image-grounding) | Portable generation agents | Searches the web and image sources before generation, then organizes facts, sources, reference images, and warnings |
| [hermes-memory-reconciler](./hermes-memory-reconciler) | Hermes Agent | Scans Hermes long-term memory for duplicates, conflicts, stale notes, unclear scope, and potentially risky instruction-style memories |
| [skill-triage](./skill-triage) | Codex and Claude Code | Reviews installed skills, finds duplicates or confusing overlaps, and writes reviewable cleanup reports |

## How to Install a Skill

Each skill is a folder. Copy the folder you need into the skill directory used by your agent runtime:

```bash
git clone https://github.com/KKL08/Skill.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Skill/<skill-name> ~/.claude/skills/

# Codex local skills
mkdir -p ~/.codex/skills
cp -r Skill/<skill-name> ~/.codex/skills/
```

For Hermes, OpenClaw, or another runtime, use that runtime's configured skill/plugin directory, or import the entire folder as a Markdown instruction pack. If the skill includes `agents/<runtime>.yaml`, `references/`, or `scripts/`, keep those files together with `SKILL.md`.

After copying, restart or reload the target agent runtime if it does not hot-load skills.

## Requirements

- An agent runtime that can load `SKILL.md` skill folders, or that lets you reference Markdown instruction folders.
- Skill-specific dependencies listed in each skill's README or `SKILL.md`.
- `coding-music` specifically requires [Claude Code](https://claude.ai/code), Claude Code hooks, [ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli), and `mpv`.
- `hermes-memory-reconciler` assumes Hermes memory files under `${HERMES_HOME:-$HOME/.hermes}/memories/` and uses the available CLI or built-in guidance to produce an inspection report and cleanup recommendations.
- `skill-triage` uses Python 3 standard-library scripts to scan local skill folders. It writes run artifacts under `~/.skilltriage/runs/` and stops at reports by default. If the user chooses to clean up, it prepares backups, asks for explicit confirmation, and keeps rollback materials.

---

## Skill Details

### coding-music `0.1 beta`

#### Background

As AI agents take on more day-to-day coding work, your attention moves toward review, decisions, and direction. When Claude needs you for a permission prompt or a key choice, that moment should be easy to notice. When Claude is working on its own, you can keep your music going.

#### What it does

Plays your favorite music while you code. When Claude needs your input, the music pauses automatically and resumes once you confirm. No window switching, no taking off your headphones; your focus and rhythm stay intact.

Optionally, it can also pause whenever Claude finishes a response — you decide when to pick back up.

Built on NetEase Music's official CLI ([ncm-cli](https://www.npmjs.com/package/@music163/ncm-cli)) and Claude Code's hook system.

**Usage:**
```
/coding-music
```

---

### docai-audit

#### Background

As Cursor, Claude Code, and Codex become common development tools, developers increasingly hand documentation to an AI agent and ask it to produce working integration code. That changes what good developer documentation needs to support.

The practical question becomes simple: can an AI agent understand these docs, call the right APIs, recover from common errors, and get to a working result?

docai-audit answers that.

#### What it does

Give it a cloud service or developer tool documentation URL, and it returns a quantified report on how well that documentation supports AI coding and agent integration.

Good for:

- **DevRel / docs teams** — find the gaps that make your docs harder for AI agents to use
- **Agent developers** — quickly judge whether a platform is suitable for AI-assisted integration

The score covers 5 dimensions focused on the main points where AI-driven integration usually succeeds or breaks down.

**Usage:**
```
/docai-audit https://resend.com/docs
```

---

### gen-image-grounding `0.1 beta`

#### Background

Image generation prompts that depend on real people, places, events, products, logos, outfits, architecture, posters, or readable text work better when facts and visual references are gathered first. gen-image-grounding prepares that grounding before the image model is called.

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

Long-term agent memory gets messy over time. User preferences can conflict, project facts can become stale, old conclusions can keep steering behavior, and risky prompt-like instructions can accidentally stay in memory. Hermes memory is especially sensitive because it affects how the agent understands the user in future sessions.

hermes-memory-reconciler reviews the memory set, identifies issues, and turns them into a clear report that helps the user decide which memories should be merged, updated, or removed. It does not change long-term memory without the user's awareness; when a conflict can affect future behavior, it leaves the key decision to the user.

#### What it does

Scans Hermes `USER.md` and `MEMORY.md`. It looks for exact duplicates, preference conflicts, profile conflicts, unclear scope, possible stale memories, and potentially risky instruction-style memories.

It asks targeted questions to help prioritize how conflicting memories should be handled. After the user makes a decision, it produces a memory cleanup proposal that explains which items should be added, replaced, or removed.

**Usage:**
```
/hermes-memory-reconciler
```

---

### skill-triage `0.1 beta`

#### Background

Agent skill libraries tend to grow over time. Some skills are used once and forgotten; others overlap in description or task scope, making it harder for the agent to decide which one to call. SkillTriage turns that messy skill space into a reviewable maintenance report.

#### What it does

Scans the current agent runtime's skills, records a factual inventory, and routes likely duplicates or confusingly similar skills into Agent evaluation. The final report separates high-confidence duplicates from related-but-clearly-bounded skills, and calls out broad groups that may need future attention.

SkillTriage prepares reports, proposals, and recovery notes by default. If the user explicitly chooses to clean up, it asks for item-by-item approval and prepares backups before writing; plugin-managed, system-managed, merge, and dedupe suggestions are not automatically executed.

**Usage:**
```
/skill-triage
```
