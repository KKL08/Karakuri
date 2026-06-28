# Karakuri

[中文版](./README.md)

Karakuri (からくり) — the ingenious mechanical automata of Edo-period Japan: small, self-contained, wind them up and they go. Each skill here works the same way: drop it into your agent and it runs.

For Claude Code, Codex, Hermes, OpenClaw, and other general-purpose agent runtimes. Each skill is a self-contained folder — `SKILL.md` holds the core instructions; references, templates, and scripts live alongside it. Runtime-agnostic unless noted otherwise.

## Available Skills

| Skill | Best For | What It Does |
|-------|----------|--------------|
| [coding-music](./coding-music) | Claude Code | Plays music while Claude Code works; auto-pauses on permission prompts and task completion, resumes after you confirm — keeps your attention where it matters |
| [coding-agent-fit](./coding-agent-fit) | Any coding agent | When you want to integrate a new product or service via a coding agent, this evaluates how agent-friendly it is and gives you a decision reference |
| [skill-triage-sibyl](./skill-triage-sibyl) | Claude Code / Codex | Too many skills and the agent starts picking the wrong one — scans for overlapping positioning, inaccurate descriptions, and idle skills, then walks you through cleanup |

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

You're about to have a coding agent like Claude Code or Codex integrate a new product or service. But is the product agent-friendly? Can the agent find the docs, read the API ref, grab credentials, and write working code — or will it get stuck halfway through some auth flow?

Instead of letting the agent try and fail, run an assessment first:

- 🔍 **Probe** → auto-scans for llms.txt, OpenAPI, MCP, CLI, SDK, and other agent-friendly entry points
- 🏃 **Dry-run** → picks an integration path and walks through it step by step
- 📊 **Report** → scores 5 dimensions, shows what's strong, what's blocking, and what to fix first

Coding agent users can run it as a pre-integration assessment; product and service providers can use it to self-check their agent-friendliness. Weights vary by site type.

See [coding-agent-fit/README.md](./coding-agent-fit/README.md) for details.

```
/coding-agent-fit https://resend.com/docs
```

---

### Skill Triage: Sibyl Scope `0.1`

The more skills you install, the worse the agent gets at picking the right one.

You ask it to "send an email" and it grabs a skill that can only search mail. You ask it to "tidy up my notes" and two skills have near-identical descriptions, so it flips a coin. Worse, some skills claim coverage that doesn't match what the SKILL.md body actually delivers — overpromising or underselling.

The problem is in the descriptions themselves — the description is the key signal an agent uses to decide whether to invoke a skill, so its quality is critical. But checking dozens by hand isn't realistic. Sibyl Scope does it for you:

- 🔍 **Scan** → lists every skill, counts 30-day call frequency, surfaces long-idle ones
- 🩺 **Diagnose** → checks five classes per item: similar descriptions, overlapping triggers, description too broad, description too narrow, positioning unclear
- ✅ **Act** → lets you choose archive / rewrite / keep / defer per item, executes on confirmation, every action reversible

Named after the Sibyl System in *PSYCHO-PASS* — it scores citizens' threat levels for tiered handling; this one scores skill descriptions for cleanup. The difference: you decide.

See [skill-triage-sibyl/README.md](./skill-triage-sibyl/README.md).

```
use skill-triage-sibyl
```

