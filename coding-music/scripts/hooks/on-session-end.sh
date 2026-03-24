#!/bin/bash
source "$HOME/.claude/hooks/coding-music/lib.sh"
log "SessionEnd — clearing hook state"
clear_paused_by
exit 0
