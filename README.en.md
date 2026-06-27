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

Requires Python 3 (probe script). See [coding-agent-fit/README.md](./coding-agent-fit/README.md) for details.

```
/coding-agent-fit https://resend.com/docs
```

---

### Skill Triage: Sibyl Scope `0.1`

Once you have dozens of skills installed, the agent's pick-the-right-skill accuracy drops noticeably — two skills with similar descriptions, a description over-promising what the body can do, a body able to do more than the description advertises. Sibyl Scope scans the current runtime's skill library and 30-day local usage frequency, diagnoses five classes (positioning overlap / trigger boundary overlap / boundary inflation / boundary deflation / positioning unclear), and lets the user choose archive / rewrite / keep / defer per item. Every executed action is reversible. Named after the Sibyl System in *PSYCHO-PASS* — a scanner that scores potential threat levels; we score skill description quality.

Requires Python 3 stdlib + system git. No third-party packages. See [skill-triage-sibyl/README.md](./skill-triage-sibyl/README.md).

```
use skill-triage-sibyl
```

