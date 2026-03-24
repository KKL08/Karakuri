#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
is_enabled || exit 0

INPUT=$(read_hook_input)

# Rule 1 fallback: resume if still paused from a permission dialog
if [ "$(get_paused_by)" = "permission" ]; then
  resume_music
  clear_paused_by
  log "Stop: resumed after permission confirm (Stop fallback)"
fi

# Rule 2: pause when Claude finishes responding
if is_rule2_enabled; then
  log "Stop event (rule2)"
  pause_music
  set_paused_by "stop"
fi

exit 0
