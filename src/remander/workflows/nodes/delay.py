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
        # delay_seconds (button-driven) takes priority over delay_minutes (legacy)
        if ctx.state.delay_seconds and ctx.state.delay_seconds > 0:
            seconds = ctx.state.delay_seconds
            label = f"{seconds}s"
        elif ctx.state.delay_minutes and ctx.state.delay_minutes > 0:
            seconds = ctx.state.delay_minutes * 60
            label = f"{ctx.state.delay_minutes} minutes"
        else:
            seconds = 0
            label = None

        logger.info(
            "[cmd %d] OptionalDelay: delay_seconds=%s delay_minutes=%s",
            ctx.state.command_id,
            ctx.state.delay_seconds,
            ctx.state.delay_minutes,
        )
        if seconds > 0:
            logger.info(
                "[cmd %d] OptionalDelay: waiting %s (%ds)", ctx.state.command_id, label, seconds
            )
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="optional_delay",
                status=ActivityStatus.STARTED,
                detail=f"Waiting {label}",
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
