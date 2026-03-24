#!/bin/bash
# coding-music skill installer

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_DIR="$HOME/.claude/hooks/coding-music"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
SKILL_DEST="$HOME/.claude/skills/coding-music"

echo "Installing coding-music skill..."

# ── 1. Copy hook scripts ──────────────────────
mkdir -p "$HOOK_DIR/logs"
cp "$SKILL_DIR/scripts/hooks/"*.sh "$HOOK_DIR/"
chmod +x "$HOOK_DIR/"*.sh
echo "  ✓ Hook scripts installed to $HOOK_DIR"

# ── 2. Create default config if not exists ────
if [ ! -f "$HOOK_DIR/config.json" ]; then
  echo '{"enabled":true,"rule2_enabled":false,"log_enabled":true}' > "$HOOK_DIR/config.json"
  echo "  ✓ Default config created"
fi

if [ ! -f "$HOOK_DIR/state.json" ]; then
  echo '{"paused_by":"","at":0}' > "$HOOK_DIR/state.json"
fi

# ── 3. Install SKILL.md ───────────────────────
mkdir -p "$SKILL_DEST"
cp "$SKILL_DIR/SKILL.md" "$SKILL_DEST/SKILL.md"
echo "  ✓ SKILL.md installed to $SKILL_DEST"

# ── 4. Register hooks in settings.json ───────
if [ ! -f "$CLAUDE_SETTINGS" ]; then
  echo '{}' > "$CLAUDE_SETTINGS"
fi

# Use Python to safely merge hooks into existing settings
python3 << PYEOF
import json, sys

with open("$CLAUDE_SETTINGS") as f:
    settings = json.load(f)

hooks_to_add = {
    "PermissionRequest": "bash ~/.claude/hooks/coding-music/on-permission-request.sh",
    "PostToolUse":       "bash ~/.claude/hooks/coding-music/on-post-tool-use.sh",
    "PreToolUse":        "bash ~/.claude/hooks/coding-music/on-pre-tool-use.sh",
    "Stop":              "bash ~/.claude/hooks/coding-music/on-stop.sh",
    "UserPromptSubmit":  "bash ~/.claude/hooks/coding-music/on-user-input.sh",
    "SessionEnd":        "bash ~/.claude/hooks/coding-music/on-session-end.sh",
}

settings.setdefault("hooks", {})

for event, cmd in hooks_to_add.items():
    entry = {"type": "command", "command": cmd, "timeout": 5}
    block = {"hooks": [entry]}
    existing = settings["hooks"].setdefault(event, [])
    # Skip if already registered
    if not any(
        h.get("command") == cmd
        for b in existing
        for h in b.get("hooks", [])
    ):
        existing.append(block)

with open("$CLAUDE_SETTINGS", "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("  ✓ Hooks registered in settings.json")
PYEOF

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  Start:        say 'coding-music' or '/coding-music' in Claude Code"
echo "  Stop:         say '停止 coding-music'"
echo "  Enable Rule2: say '开启 rule2' (pause when Claude finishes responding)"
echo ""
echo "Requirements: ncm-cli (npm install -g @music163/ncm-cli) + mpv"
