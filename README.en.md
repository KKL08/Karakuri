# Karakuri

[中文版](./README.md)

Karakuri (からくり) — the ingenious mechanical automata of Edo-period Japan: small, self-contained, wind them up and they go. Each skill here works the same way: drop it into your agent and it runs.

For Claude Code, Codex, Hermes, OpenClaw, and other general-purpose agent runtimes. Each skill is a self-contained folder — `SKILL.md` holds the core instructions; references, templates, and scripts live alongside it. Runtime-agnostic unless noted otherwise.

## Available Skills

| Skill | Best For | What It Does |
|-------|----------|--------------|
| [coding-music](./coding-music) | Claude Code | Plays music while you code; auto-pauses on permission prompts, resumes after you confirm |
| [coding-agent-fit](./coding-agent-fit) | Any coding agent | Check if a service is agent-friendly before you try to integrate it |
| [skill-triage-sibyl](./skill-triage-sibyl) | Claude Code / Codex | Audits the current agent's skill library — finds overlapping descriptions, inflated/deflated boundaries, and usage stats, with reversible cleanup |

## Installation

```bash
git clone https://github.com/KKL08/Karakuri.git

# Claude Code
mkdir -p ~/.claude/skills
cp -r Karakuri/<skill-name> ~/.claude/skills/

# Codex
mkdir -p ~/.codex/skills
cp -r Karakuri/<skill-name> ~/.codex/skills/
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

You're about to hand a service integration to your coding agent. But will it actually work? Can the agent find the docs, read the API ref, grab credentials, and write working code — or will it get stuck halfway through some auth flow?

Instead of letting the agent try and fail, run an assessment first:

- 🔍 **Probe** → auto-scans for llms.txt, OpenAPI, MCP, CLI, SDK, and other agent-friendly entry points
- 🏃 **Dry-run** → picks an integration path and walks through it step by step
- 📊 **Report** → scores 5 dimensions, shows what's strong, what's blocking, and what to fix first

DevRel teams use it for self-checks; developers use it to evaluate platforms before committing. Weights vary by site type.

See [coding-agent-fit/README.md](./coding-agent-fit/README.md) for details.

```
/coding-agent-fit https://resend.com/docs
```

---

### Skill Triage: Sibyl Scope `0.1`

The more skills you install, the worse the agent gets at picking the right one.

You ask it to "send an email" and it grabs a skill that can only search mail. You ask it to "tidy up my notes" and two skills have near-identical descriptions, so it flips a coin. Worse, some skills can do five things but their description only mentions one — the agent never sees the rest.

The problem is in the descriptions themselves, but checking dozens by hand isn't realistic. Sibyl Scope does it for you:

- 🔍 **Scan** → lists every skill, counts 30-day call frequency, surfaces long-idle ones
- 🩺 **Diagnose** → checks five classes per item: similar descriptions, overlapping triggers, description too broad, description too narrow, positioning unclear
- ✅ **Act** → lets you choose archive / rewrite / keep / defer per item, executes on confirmation, every action reversible

Named after the Sibyl System in *PSYCHO-PASS* — it scores citizens' threat levels for tiered handling; this one scores skill descriptions for cleanup. The difference: you decide.

See [skill-triage-sibyl/README.md](./skill-triage-sibyl/README.md).

```
use skill-triage-sibyl
```

