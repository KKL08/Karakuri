#!/bin/bash
# coding-music companion - shared library
# 只负责 Hook 规则（暂停/恢复），不负责启动音乐

HOOK_DIR="$HOME/.claude/hooks/coding-music"
CONFIG_FILE="$HOOK_DIR/config.json"
STATE_FILE="$HOOK_DIR/state.json"
LOG_FILE="$HOOK_DIR/logs/music.log"

# 确保 ncm-cli 在 PATH 中（npm global bin 可能不在 hook 执行环境的 PATH 里）
for p in "$HOME/.npm-global/bin" "$HOME/.nvm/versions/node/"*/bin /usr/local/bin /opt/homebrew/bin; do
  [ -d "$p" ] && export PATH="$p:$PATH"
done

mkdir -p "$HOOK_DIR/logs"

# ── Logging ──────────────────────────────────
log() {
  local log_enabled
  log_enabled=$(jq -r '.log_enabled // false' "$CONFIG_FILE" 2>/dev/null)
  if [ "$log_enabled" = "true" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
  fi
}

# ── Config ───────────────────────────────────
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

# ── State: 只追踪"是否被 hook 暂停" ─────────
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

# ── Playback control (thin wrappers) ────────
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

# ── Read hook stdin ──────────────────────────
read_hook_input() {
  cat
}
