#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
is_enabled || exit 0

INPUT=$(read_hook_input)
log "PermissionRequest triggered"

pause_music
set_paused_by "permission"

exit 0
