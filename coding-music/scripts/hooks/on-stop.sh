#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
is_enabled || exit 0

INPUT=$(read_hook_input)

# Rule 1: 权限确认后恢复（不管 rule2 开不开）
if [ "$(get_paused_by)" = "permission" ]; then
  resume_music
  clear_paused_by
  log "Stop: resumed after permission confirm"
fi

# Rule 2: Claude 回复完毕暂停
if is_rule2_enabled; then
  log "Stop event (rule2)"
  pause_music
  set_paused_by "stop"
fi

exit 0
