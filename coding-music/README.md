# coding-music — Claude Code Skill

Plays your 网易云音乐 (NetEase Music) liked songs while you code with Claude Code. Auto-pauses when Claude shows a permission dialog, resumes immediately after you confirm.

[中文](./README.zh.md)

## Requirements

- **ncm-cli** — `npm install -g @music163/ncm-cli` ([npm](https://www.npmjs.com/package/@music163/ncm-cli))
- [mpv](https://mpv.io) — media player (`brew install mpv`)
- [jq](https://jqlang.github.io/jq/) — JSON processor (`brew install jq`)
- Python 3.8+
- Node.js >= 18

## First-time Setup

### 1. Get NetEase Music API credentials

Register on the [NetEase Music Developer Platform](https://developer.music.163.com/st/developer/apply/account?type=INDIVIDUAL) to obtain your `appId` and `privateKey`.

### 2. Install and configure ncm-cli

```bash
npm install -g @music163/ncm-cli
ncm-cli configure   # enter your appId and privateKey
ncm-cli login       # authorize your account
```

For more details on ncm-cli setup and usage, see [NetEase/skills](https://github.com/NetEase/skills).

### 3. Install coding-music

```bash
git clone https://github.com/KKL08/Skill.git
cd Skill/coding-music
bash scripts/install.sh
```

`install.sh` does the following automatically:
- Copies hook scripts to `~/.claude/hooks/coding-music/`
- Installs `SKILL.md` to `~/.claude/skills/coding-music/`
- Registers all hooks in `~/.claude/settings.json`
- Creates default config and state files

Then restart Claude Code.

## Usage

| Say this | What happens |
|----------|-------------|
| `coding-music` | Start playing liked songs, activate hooks |
| `停止 coding-music` | Stop music, disable hooks |
| `开启 rule2` | Also pause when Claude finishes responding |
| `关闭 rule2` | Disable rule2 |
| `查看伴奏状态` | Show current config and playback state |

## How It Works

```
Permission dialog appears
    → PermissionRequest hook → pause music
User confirms
    → PostToolUse hook → resume immediately
```

Two rules:
- **Rule 1** (always on): pause on permission dialog, resume after confirm
- **Rule 2** (opt-in): pause when Claude stops responding, resume on next message

## Uninstall

```bash
bash scripts/uninstall.sh
```

Removes hook scripts, SKILL.md, and all hook registrations from `settings.json`.

## Config

`~/.claude/hooks/coding-music/config.json`:
```json
{
  "enabled": true,
  "rule2_enabled": false,
  "log_enabled": true
}
```

Logs: `~/.claude/hooks/coding-music/logs/music.log`
