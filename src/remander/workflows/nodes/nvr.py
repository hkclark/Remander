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
            logger.debug(
                "[cmd %d] NVRLogin: command_type=%s is_rearm=%s → RestoreBitmasks",
                ctx.state.command_id,
                ctx.state.command_type,
                ctx.state.is_rearm,
            )
            return RestoreBitmasksNode()
        if ctx.state.command_type in (CommandType.SET_AWAY_NOW, CommandType.SET_AWAY_DELAYED):
            # Power on cameras before querying the NVR — the NVR returns no data for offline cameras
            logger.debug(
                "[cmd %d] NVRLogin: command_type=%s → PowerOn",
                ctx.state.command_id,
                ctx.state.command_type,
            )
            from remander.workflows.nodes.power import PowerOnNode

            return PowerOnNode()
        # Pause commands start with SaveBitmasks (cameras already on while in Away mode)
        logger.debug(
            "[cmd %d] NVRLogin: command_type=%s → SaveBitmasks",
            ctx.state.command_id,
            ctx.state.command_type,
        )
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
            logger.debug(
                "[cmd %d] NVRLogout: pause_minutes=%d → ScheduleReArm",
                ctx.state.command_id,
                ctx.state.pause_minutes,
            )
            return ScheduleReArmNode()
        logger.debug(
            "[cmd %d] NVRLogout: no pause_minutes → Notify (has_errors=%s, discrepancies=%d)",
            ctx.state.command_id,
            ctx.state.has_errors,
            len(ctx.state.validation_discrepancies),
        )
        return NotifyNode()
