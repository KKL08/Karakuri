#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
is_enabled || exit 0
is_rule2_enabled || exit 0

INPUT=$(read_hook_input)
log "UserPromptSubmit (rule2)"

if [ "$(get_paused_by)" = "stop" ]; then
  resume_music
  clear_paused_by
  log "Resumed on user input (rule2)"
fi

exit 0
