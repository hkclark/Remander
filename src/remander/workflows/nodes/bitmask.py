"""Bitmask application workflow nodes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.device import Device
from remander.models.enums import ActivityStatus, Mode
from remander.services.activity import log_activity
from remander.services.bitmask import resolve_bitmasks_for_device
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class SetNotificationBitmasksNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Apply resolved hour bitmasks to each camera's notification schedule."""

    mode: Mode = Mode.AWAY

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:

        logger.info(
            "[cmd %d] SetNotificationBitmasks: mode=%s, %d devices",
            ctx.state.command_id,
            self.mode,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.channel is None:
                logger.debug(
                    "[cmd %d] SetNotificationBitmasks: skipping device %d (no channel)",
                    ctx.state.command_id,
                    device_id,
                )
                continue

            try:
                resolved = await resolve_bitmasks_for_device(
                    device_id,
                    self.mode,
                    latitude=ctx.deps.latitude,
                    longitude=ctx.deps.longitude,
                )
                for entry in resolved:
                    logger.info(
                        "[cmd %d] SetNotificationBitmasks: device '%s' ch=%d %s bitmask=%s",
                        ctx.state.command_id,
                        device.name,
                        device.channel,
                        entry["detection_type"],
                        entry["hour_bitmask"],
                    )
                    await ctx.deps.nvr_client.set_alarm_schedule(
                        device.channel, entry["detection_type"], entry["hour_bitmask"]
                    )
                    # Track expected values for validation
                    if device_id not in ctx.state.expected_bitmasks:
                        ctx.state.expected_bitmasks[device_id] = {}
                    ctx.state.expected_bitmasks[device_id][entry["detection_type"]] = {
                        "hour_bitmask": entry["hour_bitmask"],
                        "zone_mask": entry.get("zone_mask", ""),
                    }
                    # Track final bitmask state for notification display
                    dt_str = str(entry["detection_type"])
                    bitmask_24 = entry["hour_bitmask"][:24]
                    ctx.state.channel_bitmask_results.setdefault(device.channel, {})[dt_str] = bitmask_24

                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_notification_bitmasks",
                    status=ActivityStatus.SUCCEEDED,
                )
                ctx.state.device_results[device_id] = "succeeded"
            except Exception as e:
                logger.warning(
                    "[cmd %d] SetNotificationBitmasks: device %d failed: %s",
                    ctx.state.command_id,
                    device_id,
                    e,
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_notification_bitmasks",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = str(e)

        return SetZoneMasksNode(mode=self.mode)


@dataclass
class SetZoneMasksNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Apply zone masks to each camera's detection zones."""

    mode: Mode = Mode.AWAY

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.validate import ValidateNode

        logger.info(
            "[cmd %d] SetZoneMasks: mode=%s, %d devices",
            ctx.state.command_id,
            self.mode,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.channel is None:
                continue

            try:
                resolved = await resolve_bitmasks_for_device(
                    device_id,
                    self.mode,
                    latitude=ctx.deps.latitude,
                    longitude=ctx.deps.longitude,
                )
                for entry in resolved:
                    if entry["zone_mask"]:
                        logger.info(
                            "[cmd %d] SetZoneMasks: device '%s' ch=%d %s zone_mask=%s",
                            ctx.state.command_id,
                            device.name,
                            device.channel,
                            entry["detection_type"],
                            entry["zone_mask"],
                        )
                        await ctx.deps.nvr_client.set_detection_zones(
                            device.channel, entry["detection_type"], entry["zone_mask"]
                        )
                        # Update expected values for validation
                        if device_id in ctx.state.expected_bitmasks:
                            dt = entry["detection_type"]
                            if dt in ctx.state.expected_bitmasks[device_id]:
                                ctx.state.expected_bitmasks[device_id][dt]["zone_mask"] = entry[
                                    "zone_mask"
                                ]

                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_zone_masks",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning(
                    "[cmd %d] SetZoneMasks: device %d failed: %s",
                    ctx.state.command_id,
                    device_id,
                    e,
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="set_zone_masks",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = str(e)

        return ValidateNode()
