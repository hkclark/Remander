"""Ingress/egress notification mute workflow nodes."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.device import Device
from remander.models.detection import DeviceDetectionType
from remander.models.enums import ActivityStatus, CommandType
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)

MUTE_BITMASK = "0" * 24


@dataclass
class IngressEgressMuteNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Immediately silence mute-tagged cameras at workflow start (ingress/egress window).

    If no mute devices are configured, passes through to the next node without touching the NVR.
    Otherwise opens a temporary NVR session, sets 24-zeros on all enabled detection types for
    each mute device, records mute_start_time, and then routes to the next node.
    """

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        def _next_node() -> BaseNode[WorkflowState, WorkflowDeps]:
            from remander.workflows.nodes.delay import OptionalDelayNode
            from remander.workflows.nodes.nvr import NVRLoginNode

            if ctx.state.command_type in (CommandType.SET_AWAY_NOW, CommandType.SET_AWAY_DELAYED):
                return OptionalDelayNode()
            return NVRLoginNode()

        if not ctx.state.mute_tag_device_ids:
            logger.debug("[cmd %d] IngressEgressMute: no mute devices — skipping", ctx.state.command_id)
            return _next_node()

        logger.info(
            "[cmd %d] IngressEgressMute: muting %d device(s)",
            ctx.state.command_id,
            len(ctx.state.mute_tag_device_ids),
        )
        await ctx.deps.nvr_client.login()
        try:
            for device_id in ctx.state.mute_tag_device_ids:
                device = await Device.get(id=device_id)
                if device.channel is None:
                    logger.debug(
                        "[cmd %d] IngressEgressMute: skipping device %d (no channel)",
                        ctx.state.command_id,
                        device_id,
                    )
                    continue
                detection_types = await DeviceDetectionType.filter(device_id=device_id, is_enabled=True)
                for ddt in detection_types:
                    try:
                        await ctx.deps.nvr_client.set_alarm_schedule(
                            device.channel, ddt.detection_type, MUTE_BITMASK
                        )
                        logger.debug(
                            "[cmd %d] IngressEgressMute: device %d ch=%d %s → muted",
                            ctx.state.command_id,
                            device_id,
                            device.channel,
                            ddt.detection_type,
                        )
                    except Exception as e:
                        logger.warning(
                            "*** WARN: [cmd %d] IngressEgressMute: device %d ch=%d %s failed: %s",
                            ctx.state.command_id,
                            device_id,
                            device.channel,
                            ddt.detection_type,
                            e,
                        )
        finally:
            await ctx.deps.nvr_client.logout()

        ctx.state.mute_start_time = datetime.now(UTC)
        await log_activity(
            command_id=ctx.state.command_id,
            step_name="ingress_egress_mute",
            status=ActivityStatus.SUCCEEDED,
            detail=f"Muted {len(ctx.state.mute_tag_device_ids)} device(s) for {ctx.state.mute_duration_seconds}s",
        )
        return _next_node()


@dataclass
class WaitForMuteExpiryNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Wait until the mute window expires before applying final notification bitmasks.

    If no mute was applied (mute_start_time is None) or the mute has already expired,
    passes through immediately. Otherwise sleeps the remaining mute duration.
    """

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.models.enums import Mode
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        def _mode() -> Mode:
            if ctx.state.command_type == CommandType.SET_HOME_NOW:
                return Mode.HOME
            return Mode.AWAY

        if ctx.state.mute_start_time is not None and ctx.state.mute_duration_seconds:
            expiry = ctx.state.mute_start_time + timedelta(seconds=ctx.state.mute_duration_seconds)
            remaining = (expiry - datetime.now(UTC)).total_seconds()
            if remaining > 0:
                logger.info(
                    "[cmd %d] WaitForMuteExpiry: sleeping %.1fs until mute expires",
                    ctx.state.command_id,
                    remaining,
                )
                await asyncio.sleep(remaining)

        return SetNotificationBitmasksNode(mode=_mode())
