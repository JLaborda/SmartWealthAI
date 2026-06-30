#!/usr/bin/env bash
# ponytail: idempotent; sources workspace .env in every interactive shell
set -euo pipefail
MARKER="# smartwealthai-env"
BASHRC="${HOME}/.bashrc"
HOOK='_smartwealthai_load_env() {
  local f
  for f in "${WORKSPACE_FOLDER:-}/.env" "/workspaces/SmartWealthAI/.env"; do
    if [ -n "$f" ] && [ -f "$f" ]; then set -a; . "$f"; set +a; return; fi
  done
  f="$(git -C "${PWD}" rev-parse --show-toplevel 2>/dev/null)/.env"
  if [ -f "$f" ]; then set -a; . "$f"; set +a; fi
}
_smartwealthai_load_env'

if ! grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
  {
    echo ""
    echo "$MARKER"
    echo "$HOOK"
  } >>"$BASHRC"
fi
