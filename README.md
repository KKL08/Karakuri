# Skills for Claude Code

[中文版](./README.zh.md)

A collection of Claude Code skills. Each skill lives in its own folder and can be installed independently.

## Available Skills

| Skill | Description |
|-------|-------------|
| [coding-music](./coding-music) | Plays your liked songs while coding — auto-pauses when Claude asks for permission, resumes after you confirm |
| [docai-audit](./docai-audit) | Evaluates any docs site across 5 dimensions targeting the key nodes in an AI invocation chain |

## How to Install a Skill

Copy the skill folder into `~/.claude/skills/`:

```bash
git clone https://github.com/KKL08/Skill.git
cp -r Skill/<skill-name> ~/.claude/skills/
```

Then restart Claude Code.

## Requirements

- [Claude Code](https://claude.ai/code)
- Skill-specific dependencies listed in each skill's README

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
