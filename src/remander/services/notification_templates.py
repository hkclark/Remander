"""Notification templates — render email content for command results."""

from remander.models.command import Command


def render_command_succeeded_notification(
    command: Command, device_count: int, duration_s: float
) -> tuple[str, str]:
    """Render notification for a successfully completed command."""
    subject = f"Remander: {command.command_type} succeeded"
    body = (
        f"Command: {command.command_type}\n"
        f"Status: succeeded\n"
        f"Devices configured: {device_count}\n"
        f"Duration: {duration_s:.1f}s\n"
    )
    return subject, body


def render_command_failed_notification(
    command: Command, error: str, failed_step: str
) -> tuple[str, str]:
    """Render notification for a failed command."""
    subject = f"Remander: {command.command_type} FAILED"
    body = (
        f"Command: {command.command_type}\n"
        f"Status: failed\n"
        f"Failed step: {failed_step}\n"
        f"Error: {error}\n"
    )
    return subject, body


def render_completed_with_errors_notification(
    command: Command,
    successes: list[dict],
    failures: list[dict],
) -> tuple[str, str]:
    """Render notification for a command that completed with some errors."""
    subject = f"Remander: {command.command_type} completed with errors"
    lines = [
        f"Command: {command.command_type}",
        "Status: completed with errors",
        f"Successful devices: {len(successes)}",
        f"Failed devices: {len(failures)}",
        "",
        "Failures:",
    ]
    for f in failures:
        lines.append(f"  - {f['device']}: {f['detail']}")
    body = "\n".join(lines)
    return subject, body


def render_validation_warnings_notification(
    command: Command,
    discrepancies: list[dict],
) -> tuple[str, str]:
    """Render notification for post-command validation warnings."""
    subject = f"Remander: {command.command_type} validation warnings"
    lines = [
        f"Command: {command.command_type}",
        f"Validation found {len(discrepancies)} discrepancy(ies):",
        "",
    ]
    for d in discrepancies:
        lines.append(f"  - {d['device']}: expected={d['expected']}, actual={d['actual']}")
    body = "\n".join(lines)
    return subject, body
