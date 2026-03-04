#!/bin/bash
# Called by Claude Code SessionEnd hook — copies the session transcript
# to the project's claude-exports/ directory.

set -euo pipefail

HOOK_INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id')

EXPORT_DIR="$(dirname "$0")/../claude-exports"
mkdir -p "$EXPORT_DIR"

if [ -f "$TRANSCRIPT_PATH" ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    cp "$TRANSCRIPT_PATH" "$EXPORT_DIR/${TIMESTAMP}-${SESSION_ID}.jsonl"
fi
