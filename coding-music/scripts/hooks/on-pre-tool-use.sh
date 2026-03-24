#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
is_enabled || exit 0

INPUT=$(read_hook_input)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# Skip ncm-cli commands to prevent recursion
if [ "$TOOL_NAME" = "Bash" ]; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
  if echo "$COMMAND" | grep -q "ncm-cli"; then
    exit 0
  fi
fi

log "PreToolUse: $TOOL_NAME, paused_by=$(get_paused_by)"

# Fallback resume in case PostToolUse missed it
if [ "$(get_paused_by)" = "permission" ]; then
  resume_music
  clear_paused_by
  log "Resumed after permission confirm (PreToolUse fallback)"
fi

exit 0
