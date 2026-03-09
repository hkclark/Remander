"""Notification templates — render email content for command results."""

from remander.models.command import Command


def render_notification(
    command: Command,
    channel_bitmask_results: dict[int, dict[str, str]],
    validation_discrepancies: list[dict],
    overall_pass: bool,
    is_rearm: bool = False,
    error_message: str | None = None,
) -> tuple[str, str]:
    """Render the notification email for any command outcome."""
    base_op = command.command_type.replace("_", " ").title()
    op_name = f"Re-arm ({base_op})" if is_rearm else base_op
    status_str = "PASS" if overall_pass else "FAIL"

    channels = sorted(channel_bitmask_results.keys())
    channels_str = f"[{', '.join(str(c) for c in channels)}]" if channels else "[]"
    subject = f"{status_str}: {op_name} - Channels: {channels_str}"

    # Source host
    if command.initiated_by_user:
        source = f"{command.initiated_by_user} ({command.initiated_by_ip or 'unknown'})"
    elif command.initiated_by_ip:
        source = f"N/A ({command.initiated_by_ip})"
    else:
        source = "N/A"

    # Timestamps
    start_str = (
        command.started_at.strftime("%y-%m-%d %I:%M:%S %p") if command.started_at else "N/A"
    )
    finish_str = (
        command.completed_at.strftime("%y-%m-%d %I:%M:%S %p") if command.completed_at else "N/A"
    )

    lines = [
        f"Overall: {status_str}",
        op_name,
        f"Source Host: {source}",
        f"Start Time: {start_str}",
        f"Finish Time: {finish_str}",
    ]

    if error_message:
        lines.extend(["", f"Error: {error_message}"])

    if channel_bitmask_results:
        lines.append("")

        # Build set of (channel, detection_type) failures from validation discrepancies
        failed_pairs: set[tuple[int, str]] = {
            (d["channel"], d["detection_type"])
            for d in validation_discrepancies
            if d.get("channel") is not None
        }

        # Compute max label width for alignment across all channels
        all_labels = [
            _detection_label(dt)
            for types in channel_bitmask_results.values()
            for dt in types
        ]
        max_width = max((len(lbl) for lbl in all_labels), default=2)

        for channel in sorted(channel_bitmask_results.keys()):
            lines.append(f"channel={channel}:")
            # AI types (non-motion) alphabetically first, then MD (motion) last
            items = sorted(
                channel_bitmask_results[channel].items(),
                key=lambda kv: (1 if kv[0] == "motion" else 0, kv[0]),
            )
            for dt_str, bitmask in items:
                label = _detection_label(dt_str)
                visual = _bitmask_visual(bitmask)
                status = "FAIL" if (channel, dt_str) in failed_pairs else "OK  "
                lines.append(f"  {label.ljust(max_width)} {status} ({visual})")

    return subject, "\n".join(lines)


def _detection_label(dt: str) -> str:
    """Map detection type string to display label (motion → MD, others unchanged)."""
    return "MD" if dt == "motion" else dt


def _bitmask_visual(bitmask: str) -> str:
    """Convert bitmask to | / . visual using first 24 characters."""
    return bitmask[:24].replace("1", "|").replace("0", ".")
