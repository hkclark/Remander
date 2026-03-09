"""Notification workflow node."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

from remander.models.command import Command
from remander.models.enums import ActivityStatus, CommandStatus
from remander.services.activity import log_activity
from remander.services.notification_templates import (
    render_command_failed_notification,
    render_command_succeeded_notification,
    render_completed_with_errors_notification,
    render_validation_warnings_notification,
)
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class NotifyNode(BaseNode[WorkflowState, WorkflowDeps, str]):
    """Send a notification with the command result."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> End[str]:
        logger.info("[cmd %d] Notify: sending notification", ctx.state.command_id)
        try:
            cmd = await Command.get(id=ctx.state.command_id)
            subject, body = self._render_notification(cmd, ctx.state)
            logger.info("[cmd %d] Notify: subject='%s'", ctx.state.command_id, subject)

            await ctx.deps.notification_sender.send(subject, body)

            await log_activity(
                command_id=ctx.state.command_id,
                step_name="notify",
                status=ActivityStatus.SUCCEEDED,
            )
        except Exception as e:
            logger.warning("[cmd %d] Notify: failed: %s", ctx.state.command_id, e)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="notify",
                status=ActivityStatus.FAILED,
                detail=str(e),
            )

        return End("done")

    def _render_notification(self, cmd: Command, state: WorkflowState) -> tuple[str, str]:
        """Choose the right template based on command status."""
        device_count = len(state.device_ids)

        if state.validation_discrepancies:
            logger.debug(
                "[cmd %d] Notify: %d validation discrepancy(s) → validation_warnings template",
                state.command_id,
                len(state.validation_discrepancies),
            )
            return render_validation_warnings_notification(cmd, state.validation_discrepancies)

        if cmd.status == CommandStatus.FAILED:
            logger.debug(
                "[cmd %d] Notify: status=FAILED, error=%r → command_failed template",
                state.command_id,
                cmd.error_summary,
            )
            return render_command_failed_notification(
                cmd, error=cmd.error_summary or "Unknown error", failed_step="unknown"
            )

        if cmd.status == CommandStatus.COMPLETED_WITH_ERRORS:
            successes = [
                {"device": str(did), "detail": "OK"}
                for did, result in state.device_results.items()
                if result == "succeeded"
            ]
            failures = [
                {"device": str(did), "detail": result}
                for did, result in state.device_results.items()
                if result != "succeeded"
            ]
            logger.debug(
                "[cmd %d] Notify: status=COMPLETED_WITH_ERRORS (%d ok, %d failed)"
                " → completed_with_errors template",
                state.command_id,
                len(successes),
                len(failures),
            )
            return render_completed_with_errors_notification(cmd, successes, failures)

        logger.debug(
            "[cmd %d] Notify: status=%s, %d device(s) → command_succeeded template",
            state.command_id,
            cmd.status,
            device_count,
        )
        return render_command_succeeded_notification(cmd, device_count, duration_s=0.0)
