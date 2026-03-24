---
name: coding-music
description: Coding music companion for Claude Code. Plays your NetEase Music (网易云音乐) liked songs while you code. Auto-pauses when Claude Code shows a permission dialog, resumes immediately after you confirm. Trigger when user says "coding-music", "start coding music", "开始 coding-music", "编码伴奏", or wants background music while coding.
---

# Coding Music Companion

Plays your 网易云音乐 liked songs while coding. The hook system auto-pauses on permission dialogs and resumes immediately after confirmation — no interruption to your flow.

## Prerequisites

- `ncm-cli` installed: `npm install -g @music163/ncm-cli` ([npm](https://www.npmjs.com/package/@music163/ncm-cli))
- [mpv](https://mpv.io) installed (`brew install mpv` on macOS)
- Hooks installed via `scripts/install.sh`

## When user says "coding-music" / "开始 coding-music" — Startup

**Execute exactly in order. Do not search for songs. Do not recommend music.**

### Step 1-3: Check env, login, config (one Bash call)

```bash
ncm-cli --version && \
ncm-cli login --check && \
(cat ~/.claude/hooks/coding-music/config.json 2>/dev/null || \
  (mkdir -p ~/.claude/hooks/coding-music/logs && \
   echo '{"enabled":true,"rule2_enabled":false,"log_enabled":true}' > ~/.claude/hooks/coding-music/config.json && \
   echo '{"paused_by":"","at":0}' > ~/.claude/hooks/coding-music/state.json && \
   cat ~/.claude/hooks/coding-music/config.json))
```

- If `ncm-cli --version` fails → tell user to install ncm-cli first
- If `login --check` shows not logged in → run `ncm-cli login --background`
- If config shows `"enabled": false` → re-enable with `jq '.enabled = true' ~/.claude/hooks/coding-music/config.json > /tmp/cm_tmp.json && mv /tmp/cm_tmp.json ~/.claude/hooks/coding-music/config.json`

### Step 4: Start playback + update state (one Bash call — only one permission prompt)

```bash
LIKED=$(ncm-cli playlist created --output json | python3 -c "
import json,sys
data=json.load(sys.stdin)
for r in data['data']['records']:
    if r.get('specialType')==5:
        print(r['id'], r['originalId'])
        break
") && \
ENC_ID=$(echo $LIKED | awk '{print $1}') && \
ORIG_ID=$(echo $LIKED | awk '{print $2}') && \
ncm-cli play --playlist --encrypted-id $ENC_ID --original-id $ORIG_ID && \
sleep 0.3 && \
ncm-cli next && \
sleep 0.3 && \
ncm-cli resume && \
jq '.at = now | .paused_by = ""' ~/.claude/hooks/coding-music/state.json > /tmp/cm_state.json && \
mv /tmp/cm_state.json ~/.claude/hooks/coding-music/state.json
```

The liked songs playlist has `specialType=5` in the created playlists list. Merging all commands into one Bash call avoids multiple permission prompts that would cause repeated pause/resume cycles.

The sequence `play → sleep 0.3 → next → sleep 0.3 → resume` is required because `play --playlist` loads the queue asynchronously; calling `next` immediately fails with "queue empty", and `resume` alone won't start a stopped player.

### Step 5: Tell the user

- Coding music started, playing liked songs
- Music auto-pauses on permission dialogs and resumes right after
- To also pause when Claude finishes a response, say "开启 rule2"

---

## When user says "停止 coding-music" / "stop coding music"

```bash
ncm-cli stop 2>/dev/null && \
jq '.enabled = false' ~/.claude/hooks/coding-music/config.json > /tmp/cm_tmp.json && \
mv /tmp/cm_tmp.json ~/.claude/hooks/coding-music/config.json
```

## When user says "开启 rule2" / "enable rule2"

```bash
jq '.rule2_enabled = true' ~/.claude/hooks/coding-music/config.json > /tmp/cm_tmp.json && mv /tmp/cm_tmp.json ~/.claude/hooks/coding-music/config.json
```

Tell user: Rule 2 enabled — music pauses when Claude finishes responding, resumes when you send the next message.

## When user says "关闭 rule2" / "disable rule2"

```bash
jq '.rule2_enabled = false' ~/.claude/hooks/coding-music/config.json > /tmp/cm_tmp.json && mv /tmp/cm_tmp.json ~/.claude/hooks/coding-music/config.json
```

## When user says "查看伴奏状态" / "check music status"

```bash
cat ~/.claude/hooks/coding-music/config.json && \
cat ~/.claude/hooks/coding-music/state.json && \
ncm-cli state 2>/dev/null
```

---

## Hook Rules

| Rule | Default | Behavior |
|------|---------|----------|
| Rule 1 | On | Permission dialog → pause; confirmed → resume immediately (PostToolUse) |
| Rule 2 | Off | Claude stops responding → pause; user sends next message → resume |

Resume priority: `PostToolUse` (fastest) → `PreToolUse` (next tool) → `Stop` (fallback).

Config: `~/.claude/hooks/coding-music/config.json`
Logs: `~/.claude/hooks/coding-music/logs/music.log`
