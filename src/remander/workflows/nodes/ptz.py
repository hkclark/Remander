"""PTZ workflow nodes — calibrate, set preset, set home."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.device import Device
from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class PTZCalibrateNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Run PTZ calibration on cameras that support it."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> SetPTZPresetNode:
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                continue

            try:
                # Calibrate by moving to preset 0 and back
                if device.ptz_away_preset is not None:
                    await ctx.deps.nvr_client.move_to_preset(
                        device.channel, device.ptz_away_preset, device.ptz_speed
                    )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="ptz_calibrate",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning("PTZ calibration failed for device %d: %s", device_id, e)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="ptz_calibrate",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )

        return SetPTZPresetNode()


@dataclass
class SetPTZPresetNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Move PTZ cameras to their away-mode preset position."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                continue
            if device.ptz_away_preset is None:
                continue

            try:
                await ctx.deps.nvr_client.move_to_preset(
                    device.channel, device.ptz_away_preset, device.ptz_speed
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_ptz_preset",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning("PTZ preset failed for device %d: %s", device_id, e)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_ptz_preset",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )

        return SetNotificationBitmasksNode()


@dataclass
class SetPTZHomeNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Move PTZ cameras to their home-mode preset position."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.power import PowerOffNode

        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                continue
            if device.ptz_home_preset is None:
                continue

            try:
                await ctx.deps.nvr_client.move_to_preset(
                    device.channel, device.ptz_home_preset, device.ptz_speed
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_ptz_home",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning("PTZ home failed for device %d: %s", device_id, e)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_ptz_home",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )

        return PowerOffNode()
