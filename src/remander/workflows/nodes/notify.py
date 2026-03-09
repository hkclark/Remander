"""Notification workflow node."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

from remander.models.command import Command
from remander.models.enums import ActivityStatus, CommandStatus
from remander.services.activity import log_activity
from remander.services.notification_templates import render_notification
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
        """Render notification email for this command outcome."""
        overall_pass = (
            cmd.status not in (CommandStatus.FAILED, CommandStatus.COMPLETED_WITH_ERRORS)
            and not state.validation_discrepancies
        )
        error_message = cmd.error_summary if cmd.status == CommandStatus.FAILED else None
        logger.debug(
            "[cmd %d] Notify: status=%s overall_pass=%s channels=%s",
            state.command_id,
            cmd.status,
            overall_pass,
            sorted(state.channel_bitmask_results.keys()),
        )
        return render_notification(
            command=cmd,
            channel_bitmask_results=state.channel_bitmask_results,
            validation_discrepancies=state.validation_discrepancies,
            overall_pass=overall_pass,
            is_rearm=state.is_rearm,
            error_message=error_message,
        )
