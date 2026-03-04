#!/bin/bash
# List available Claude Code session transcripts with metadata.
# Usage: ./scripts/list-transcripts.sh [--all]
#   --all: also show transcripts from ~/.claude/projects/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXPORT_DIR="$PROJECT_DIR/claude-exports"
CLAUDE_DIR="$HOME/.claude/projects/-home-kclark-git-Remander"

print_entry() {
    local file="$1"
    local slug session_id first_user_msg line_count

    line_count=$(wc -l < "$file")
    slug=$(head -20 "$file" | jq -r 'select(.slug != null) | .slug' 2>/dev/null | head -1)
    session_id=$(head -5 "$file" | jq -r 'select(.sessionId != null) | .sessionId' 2>/dev/null | head -1)
    first_user_msg=$(jq -r 'select(.type == "user") | .message.content[] | select(.type == "text") | .text' "$file" 2>/dev/null | head -c 80 | head -1)

    local name="${slug:-unknown}"
    printf "  %-35s %6d lines  %s\n" "$name" "$line_count" "$(basename "$file")"
    if [ -n "$first_user_msg" ]; then
        printf "    > %.75s\n" "$first_user_msg"
    fi
    printf "    %s\n\n" "$file"
}

echo ""
echo "=== Auto-exported transcripts (claude-exports/) ==="
echo ""
if [ -d "$EXPORT_DIR" ] && ls "$EXPORT_DIR"/*.jsonl &>/dev/null; then
    for f in "$EXPORT_DIR"/*.jsonl; do
        print_entry "$f"
    done
else
    echo "  (none yet — transcripts appear here after ending a session)"
    echo ""
fi

if [ "${1:-}" = "--all" ]; then
    echo "=== Raw transcripts (~/.claude/projects/) ==="
    echo ""
    if [ -d "$CLAUDE_DIR" ] && ls "$CLAUDE_DIR"/*.jsonl &>/dev/null; then
        for f in "$CLAUDE_DIR"/*.jsonl; do
            print_entry "$f"
        done
    else
        echo "  (none found)"
        echo ""
    fi
fi

echo "To convert a transcript to Markdown:"
echo "  ./scripts/transcript-to-markdown.py <path-to-jsonl> [output.md]"
echo ""
