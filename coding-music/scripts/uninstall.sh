#!/bin/bash
# coding-music skill uninstaller

HOOK_DIR="$HOME/.claude/hooks/coding-music"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
SKILL_DEST="$HOME/.claude/skills/coding-music"

echo "Uninstalling coding-music skill..."

# Stop music if playing
if command -v ncm-cli &>/dev/null; then
  ncm-cli stop 2>/dev/null && echo "  ✓ Music stopped"
fi

# Remove hook scripts and data
if [ -d "$HOOK_DIR" ]; then
  rm -rf "$HOOK_DIR"
  echo "  ✓ Hook directory removed"
fi

# Remove skill
if [ -d "$SKILL_DEST" ]; then
  rm -rf "$SKILL_DEST"
  echo "  ✓ Skill removed"
fi

# Remove hooks from settings.json
if [ -f "$CLAUDE_SETTINGS" ]; then
  python3 << PYEOF
import json

with open("$CLAUDE_SETTINGS") as f:
    settings = json.load(f)

cm_commands = {
    "on-permission-request.sh",
    "on-post-tool-use.sh",
    "on-pre-tool-use.sh",
    "on-stop.sh",
    "on-user-input.sh",
    "on-session-end.sh",
}

hooks = settings.get("hooks", {})
for event in list(hooks.keys()):
    hooks[event] = [
        b for b in hooks[event]
        if not any(
            any(cm in h.get("command", "") for cm in cm_commands)
            for h in b.get("hooks", [])
        )
    ]
    if not hooks[event]:
        del hooks[event]

with open("$CLAUDE_SETTINGS", "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("  ✓ Hooks removed from settings.json")
PYEOF
fi

echo ""
echo "coding-music uninstalled."
