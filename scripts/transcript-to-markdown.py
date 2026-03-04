#!/usr/bin/env python3
"""Convert a Claude Code JSONL session transcript to readable Markdown.

Usage:
    ./scripts/transcript-to-markdown.py <input.jsonl> [output.md]

If output is omitted, writes to stdout.
If output is a directory, writes to <directory>/<input-stem>.md.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def parse_timestamp(ts: str) -> str:
    """Convert ISO timestamp to a readable local format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError, TypeError:
        return ts or ""


def format_tool_use(block: dict) -> str:
    """Format a tool_use content block."""
    name = block.get("name", "Unknown")
    inp = block.get("input", {})

    lines = [f"**Tool: {name}**"]

    if name == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        if desc:
            lines.append(f"*{desc}*")
        lines.append(f"```bash\n{cmd}\n```")
    elif name in ("Read", "Glob", "Grep"):
        for k, v in inp.items():
            lines.append(f"- {k}: `{v}`")
    elif name == "Write":
        path = inp.get("file_path", "")
        content = inp.get("content", "")
        lines.append(f"Write to `{path}`")
        if len(content) > 500:
            lines.append(f"```\n{content[:500]}\n... ({len(content)} chars total)\n```")
        else:
            lines.append(f"```\n{content}\n```")
    elif name == "Edit":
        path = inp.get("file_path", "")
        old = inp.get("old_string", "")
        new = inp.get("new_string", "")
        lines.append(f"Edit `{path}`")
        lines.append(f"```diff\n- {old[:200]}\n+ {new[:200]}\n```")
    elif name == "Agent":
        desc = inp.get("description", "")
        prompt = inp.get("prompt", "")
        lines.append(f"*{desc}*")
        if prompt:
            lines.append(f"> {prompt[:300]}")
    else:
        # Generic tool display
        for k, v in inp.items():
            val_str = str(v)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            lines.append(f"- {k}: {val_str}")

    return "\n".join(lines)


def format_tool_result(block: dict) -> str:
    """Format a tool_result content block."""
    content = block.get("content", "")
    is_error = block.get("is_error", False)

    if not content:
        return ""

    # Content can be a string or a list of content blocks
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", str(item)))
            else:
                parts.append(str(item))
        content = "\n".join(parts)

    # Strip system reminders from output
    lines = []
    in_reminder = False
    for line in content.split("\n"):
        if "<system-reminder>" in line:
            in_reminder = True
            continue
        if "</system-reminder>" in line:
            in_reminder = False
            continue
        if not in_reminder:
            lines.append(line)
    content = "\n".join(lines).strip()

    if not content:
        return ""

    prefix = "**Error:**\n" if is_error else ""
    if len(content) > 1000:
        content = content[:1000] + f"\n... ({len(content)} chars total)"

    return f"{prefix}```\n{content}\n```"


def format_message(record: dict) -> str | None:
    """Format a single JSONL record into Markdown."""
    record_type = record.get("type")
    message = record.get("message", {})
    timestamp = parse_timestamp(record.get("timestamp", ""))

    if record_type == "user":
        content = message.get("content", [])
        parts = []

        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        text = block.get("text", "")
                        # Skip system reminders and local command caveats
                        if "<system-reminder>" in text or "<local-command-caveat>" in text:
                            # Extract just the user's actual text
                            import re

                            # Remove XML tags and their content
                            cleaned = re.sub(
                                r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL
                            )
                            cleaned = re.sub(
                                r"<local-command-caveat>.*?</local-command-caveat>",
                                "",
                                cleaned,
                                flags=re.DOTALL,
                            )
                            cleaned = re.sub(
                                r"<local-command-stdout>.*?</local-command-stdout>",
                                "",
                                cleaned,
                                flags=re.DOTALL,
                            )
                            cleaned = re.sub(
                                r"<command-name>.*?</command-name>", "", cleaned, flags=re.DOTALL
                            )
                            cleaned = re.sub(
                                r"<command-message>.*?</command-message>",
                                "",
                                cleaned,
                                flags=re.DOTALL,
                            )
                            cleaned = re.sub(
                                r"<command-args>.*?</command-args>", "", cleaned, flags=re.DOTALL
                            )
                            cleaned = cleaned.strip()
                            if cleaned:
                                parts.append(cleaned)
                        else:
                            parts.append(text)
                    elif block_type == "tool_result":
                        result = format_tool_result(block)
                        if result:
                            parts.append(result)

        text = "\n".join(parts).strip()
        if not text:
            return None
        return f"---\n\n### User ({timestamp})\n\n{text}\n"

    elif record_type == "assistant":
        content = message.get("content", [])
        parts = []

        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")

            if block_type == "text":
                parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                parts.append(format_tool_use(block))
            elif block_type == "thinking":
                thinking = block.get("thinking", "")
                if thinking:
                    # Show a brief summary of thinking
                    preview = thinking[:200]
                    if len(thinking) > 200:
                        preview += "..."
                    parts.append(
                        f"<details>\n<summary>Thinking...</summary>\n\n{preview}\n\n</details>"
                    )

        text = "\n\n".join(parts).strip()
        if not text:
            return None

        model = message.get("model", "")
        model_str = f" [{model}]" if model else ""
        return f"### Assistant{model_str} ({timestamp})\n\n{text}\n"

    return None


def convert(input_path: Path, output_file) -> None:
    """Convert a JSONL transcript to Markdown."""
    # Extract session metadata from first few records
    session_id = ""
    slug = ""
    start_time = ""

    records = []
    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records.append(record)
            if not session_id:
                session_id = record.get("sessionId", "")
            if not slug:
                slug = record.get("slug", "")
            if not start_time and record.get("timestamp"):
                start_time = parse_timestamp(record["timestamp"])

    # Write header
    title = slug.replace("-", " ").title() if slug else "Claude Code Session"
    output_file.write(f"# {title}\n\n")
    output_file.write(f"- **Session ID**: {session_id}\n")
    output_file.write(f"- **Started**: {start_time}\n")
    output_file.write(f"- **Transcript**: {input_path.name}\n\n")

    # Process records
    for record in records:
        formatted = format_message(record)
        if formatted:
            output_file.write(formatted + "\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
        if output_path.is_dir():
            output_path = output_path / f"{input_path.stem}.md"
        with open(output_path, "w") as f:
            convert(input_path, f)
        print(f"Written to {output_path}", file=sys.stderr)
    else:
        convert(input_path, sys.stdout)


if __name__ == "__main__":
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
