"""NVR login/logout workflow nodes."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class NVRLoginNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Authenticate with the Reolink NVR."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.models.enums import CommandType
        from remander.workflows.nodes.save_restore import RestoreBitmasksNode, SaveBitmasksNode

        logger.info("[cmd %d] NVRLogin: connecting...", ctx.state.command_id)
        start = time.monotonic()
        await log_activity(
            command_id=ctx.state.command_id,
            step_name="nvr_login",
            status=ActivityStatus.STARTED,
        )
        try:
            await ctx.deps.nvr_client.login()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("[cmd %d] NVRLogin: succeeded in %dms", ctx.state.command_id, elapsed_ms)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="nvr_login",
                status=ActivityStatus.SUCCEEDED,
                duration_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "[cmd %d] NVRLogin: failed in %dms: %s", ctx.state.command_id, elapsed_ms, e
            )
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="nvr_login",
                status=ActivityStatus.FAILED,
                duration_ms=elapsed_ms,
                detail=str(e),
            )
            raise

        # Route to the correct next node based on command type
        if ctx.state.command_type == CommandType.SET_HOME_NOW or ctx.state.is_rearm:
            return RestoreBitmasksNode()
        # Set Away and Pause commands all start with SaveBitmasks
        return SaveBitmasksNode()


@dataclass
class NVRLogoutNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Close the NVR session."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.notify import NotifyNode
        from remander.workflows.nodes.schedule import ScheduleReArmNode

        logger.info("[cmd %d] NVRLogout: disconnecting...", ctx.state.command_id)
        try:
            await ctx.deps.nvr_client.logout()
            logger.info("[cmd %d] NVRLogout: succeeded", ctx.state.command_id)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="nvr_logout",
                status=ActivityStatus.SUCCEEDED,
            )
        except Exception as e:
            logger.warning("[cmd %d] NVRLogout: failed: %s", ctx.state.command_id, e)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="nvr_logout",
                status=ActivityStatus.FAILED,
                detail=str(e),
            )

        # Pause commands schedule re-arm; other commands send notification
        if ctx.state.pause_minutes and ctx.state.pause_minutes > 0:
            return ScheduleReArmNode()
        return NotifyNode()
