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
        logger.info(
            "[cmd %d] PTZCalibrate: calibrating %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                logger.debug(
                    "[cmd %d] PTZCalibrate: skipping device '%s' (has_ptz=%s, channel=%s)",
                    ctx.state.command_id,
                    device.name,
                    device.has_ptz,
                    device.channel,
                )
                continue

            try:
                # Calibrate by moving to preset 0 and back
                if device.ptz_away_preset is not None:
                    logger.info(
                        "[cmd %d] PTZCalibrate: device '%s' ch=%d preset=%d speed=%d",
                        ctx.state.command_id,
                        device.name,
                        device.channel,
                        device.ptz_away_preset,
                        device.ptz_speed,
                    )
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
                logger.warning(
                    "[cmd %d] PTZCalibrate: device %d failed: %s",
                    ctx.state.command_id,
                    device_id,
                    e,
                )
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

        logger.info(
            "[cmd %d] SetPTZPreset: setting away presets for %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                logger.debug(
                    "[cmd %d] SetPTZPreset: skipping device '%s' (has_ptz=%s, channel=%s)",
                    ctx.state.command_id,
                    device.name,
                    device.has_ptz,
                    device.channel,
                )
                continue
            if device.ptz_away_preset is None:
                logger.debug(
                    "[cmd %d] SetPTZPreset: skipping device '%s' (no ptz_away_preset)",
                    ctx.state.command_id,
                    device.name,
                )
                continue

            try:
                logger.info(
                    "[cmd %d] SetPTZPreset: device '%s' ch=%d preset=%d speed=%d",
                    ctx.state.command_id,
                    device.name,
                    device.channel,
                    device.ptz_away_preset,
                    device.ptz_speed,
                )
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
                logger.warning(
                    "[cmd %d] SetPTZPreset: device %d failed: %s",
                    ctx.state.command_id,
                    device_id,
                    e,
                )
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

        logger.info(
            "[cmd %d] SetPTZHome: setting home presets for %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.has_ptz or device.channel is None:
                logger.debug(
                    "[cmd %d] SetPTZHome: skipping device '%s' (has_ptz=%s, channel=%s)",
                    ctx.state.command_id,
                    device.name,
                    device.has_ptz,
                    device.channel,
                )
                continue
            if device.ptz_home_preset is None:
                logger.debug(
                    "[cmd %d] SetPTZHome: skipping device '%s' (no ptz_home_preset)",
                    ctx.state.command_id,
                    device.name,
                )
                continue

            try:
                logger.info(
                    "[cmd %d] SetPTZHome: device '%s' ch=%d preset=%d speed=%d",
                    ctx.state.command_id,
                    device.name,
                    device.channel,
                    device.ptz_home_preset,
                    device.ptz_speed,
                )
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
                logger.warning(
                    "[cmd %d] SetPTZHome: device %d failed: %s", ctx.state.command_id, device_id, e
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_ptz_home",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )

        return PowerOffNode()
