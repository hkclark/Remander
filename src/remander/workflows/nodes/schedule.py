"""Schedule re-arm workflow node."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class ScheduleReArmNode(BaseNode[WorkflowState, WorkflowDeps, str]):
    """Enqueue a SAQ job to re-arm (restore bitmasks) after pause_minutes."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> End[str]:
        from remander.services.scheduling import schedule_rearm

        logger.info(
            "[cmd %d] ScheduleReArm: pause_minutes=%s",
            ctx.state.command_id,
            ctx.state.pause_minutes,
        )
        pause_minutes = ctx.state.pause_minutes
        if pause_minutes and pause_minutes > 0:
            await schedule_rearm(ctx.state.command_id, pause_minutes)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="schedule_rearm",
                status=ActivityStatus.SUCCEEDED,
                detail=f"Re-arm scheduled in {pause_minutes} minutes",
            )
            logger.info(
                "[cmd %d] ScheduleReArm: re-arm scheduled in %d minutes",
                ctx.state.command_id,
                pause_minutes,
            )
        else:
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="schedule_rearm",
                status=ActivityStatus.SKIPPED,
                detail="No pause_minutes set",
            )

        return End("done")
