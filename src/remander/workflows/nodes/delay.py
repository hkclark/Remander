"""Optional delay workflow node."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.workflows.nodes.nvr import NVRLoginNode
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class OptionalDelayNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Wait for delay_minutes if set (used by Set Away Delayed)."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> NVRLoginNode:
        delay = ctx.state.delay_minutes
        if delay and delay > 0:
            seconds = delay * 60
            logger.info("Delaying command %d for %d minutes", ctx.state.command_id, delay)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="optional_delay",
                status=ActivityStatus.STARTED,
                detail=f"Waiting {delay} minutes",
            )
            await asyncio.sleep(seconds)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="optional_delay",
                status=ActivityStatus.SUCCEEDED,
            )
        else:
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="optional_delay",
                status=ActivityStatus.SKIPPED,
                detail="No delay configured",
            )
        return NVRLoginNode()
