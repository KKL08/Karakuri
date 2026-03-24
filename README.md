# Skills for Claude Code

A collection of Claude Code skills. Each skill lives in its own folder and can be installed independently.

## Available Skills

| Skill | Description |
|-------|-------------|
| [coding-music](./coding-music) | 编码伴奏系统 — plays your 网易云音乐 liked songs while coding, auto-pauses on permission dialogs |

## How to Install a Skill

Each skill folder contains a `scripts/install.sh`. Run it to install:

```bash
git clone https://github.com/KKL08/Skill.git
cd Skill/<skill-name>
bash scripts/install.sh
```

Then restart Claude Code.

## Requirements

- [Claude Code](https://claude.ai/code)
- Skill-specific dependencies listed in each skill's README
