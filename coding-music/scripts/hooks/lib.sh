#!/bin/bash
# coding-music — shared library for hooks

HOOK_DIR="$HOME/.claude/hooks/coding-music"
CONFIG_FILE="$HOOK_DIR/config.json"
STATE_FILE="$HOOK_DIR/state.json"
LOG_FILE="$HOOK_DIR/logs/music.log"

# Ensure ncm-cli is in PATH (npm global bin may not be in hook execution environment)
for p in "$HOME/.npm-global/bin" "$HOME/.nvm/versions/node/"*/bin /usr/local/bin /opt/homebrew/bin; do
  [ -d "$p" ] && export PATH="$p:$PATH"
done

mkdir -p "$HOOK_DIR/logs"

log() {
  local log_enabled
  log_enabled=$(jq -r '.log_enabled // false' "$CONFIG_FILE" 2>/dev/null)
  if [ "$log_enabled" = "true" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
  fi
}

is_enabled() {
  local enabled
  enabled=$(jq -r 'if .enabled == false then "false" else "true" end' "$CONFIG_FILE" 2>/dev/null)
  [ "$enabled" = "true" ]
}

is_rule2_enabled() {
  local rule2
  rule2=$(jq -r 'if .rule2_enabled == true then "true" else "false" end' "$CONFIG_FILE" 2>/dev/null)
  [ "$rule2" = "true" ]
}

# paused_by: "" | "permission" | "stop"
get_paused_by() {
  jq -r '.paused_by // ""' "$STATE_FILE" 2>/dev/null
}

set_paused_by() {
  local reason="$1"
  local tmp_file="$STATE_FILE.tmp"
  cat > "$tmp_file" << EOJSON
{
  "paused_by": "$reason",
  "at": $(date +%s)
}
EOJSON
  mv "$tmp_file" "$STATE_FILE"
}

clear_paused_by() {
  set_paused_by ""
}

pause_music() {
  ncm-cli pause 2>/dev/null
  log "Paused music"
}

resume_music() {
  ncm-cli resume 2>/dev/null
  log "Resumed music"
}

stop_music() {
  ncm-cli stop 2>/dev/null
  log "Stopped music"
}

read_hook_input() {
  cat
}
