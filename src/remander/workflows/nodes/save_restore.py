"""Save/restore bitmask workflow nodes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.detection import DeviceDetectionType
from remander.models.device import Device
from remander.models.enums import ActivityStatus, Mode
from remander.models.state import SavedDeviceState
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class SaveBitmasksNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Read current bitmask values from NVR and save them to saved_device_state."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.power import PowerOnNode

        logger.info(
            "[cmd %d] SaveBitmasks: saving state for %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.channel is None:
                logger.debug(
                    "[cmd %d] SaveBitmasks: skipping device %d (no channel)",
                    ctx.state.command_id,
                    device_id,
                )
                continue

            enabled_types = await DeviceDetectionType.filter(device_id=device_id, is_enabled=True)
            logger.debug(
                "[cmd %d] SaveBitmasks: device '%s' ch=%d has %d detection types",
                ctx.state.command_id,
                device.name,
                device.channel,
                len(enabled_types),
            )
            for dt_record in enabled_types:
                try:
                    hour_bitmask = await ctx.deps.nvr_client.get_alarm_schedule(
                        device.channel, dt_record.detection_type
                    )
                    zone_mask = await ctx.deps.nvr_client.get_detection_zones(
                        device.channel, dt_record.detection_type
                    )
                    logger.info(
                        "[cmd %d] SaveBitmasks: device '%s' %s bitmask=%s",
                        ctx.state.command_id,
                        device.name,
                        dt_record.detection_type,
                        hour_bitmask,
                    )
                    logger.debug(
                        "[cmd %d] SaveBitmasks: device '%s' %s zone_mask=%s",
                        ctx.state.command_id,
                        device.name,
                        dt_record.detection_type,
                        zone_mask,
                    )
                    await SavedDeviceState.create(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        detection_type=dt_record.detection_type,
                        saved_hour_bitmask=hour_bitmask,
                        saved_zone_mask=zone_mask,
                    )
                    await log_activity(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        step_name="save_bitmasks",
                        status=ActivityStatus.SUCCEEDED,
                        detail=f"Saved {dt_record.detection_type}",
                    )
                except Exception as e:
                    logger.warning(
                        "[cmd %d] SaveBitmasks: device %d failed: %s",
                        ctx.state.command_id,
                        device_id,
                        e,
                    )
                    await log_activity(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        step_name="save_bitmasks",
                        status=ActivityStatus.FAILED,
                        detail=str(e),
                    )
                    ctx.state.has_errors = True
                    ctx.state.device_results[device_id] = "failed"

        from remander.models.enums import CommandType
        from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode

        # Pause commands go straight to zeroing bitmasks; Set Away does power-on first
        if ctx.state.command_type in (
            CommandType.PAUSE_NOTIFICATIONS,
            CommandType.PAUSE_RECORDING,
        ):
            return SetNotificationBitmasksNode(mode=Mode.AWAY)
        return PowerOnNode()


@dataclass
class RestoreBitmasksNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Read saved state from saved_device_state and write it back to the NVR."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.ptz import SetPTZHomeNode

        logger.info(
            "[cmd %d] RestoreBitmasks: restoring state for %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.channel is None:
                continue

            saved_states = await SavedDeviceState.filter(
                command_id=ctx.state.command_id,
                device_id=device_id,
                is_consumed=False,
            )
            logger.debug(
                "[cmd %d] RestoreBitmasks: device '%s' ch=%d has %d saved states",
                ctx.state.command_id,
                device.name,
                device.channel,
                len(saved_states),
            )
            for saved in saved_states:
                try:
                    if saved.saved_hour_bitmask:
                        logger.info(
                            "[cmd %d] RestoreBitmasks: device '%s' %s restoring bitmask=%s",
                            ctx.state.command_id,
                            device.name,
                            saved.detection_type,
                            saved.saved_hour_bitmask,
                        )
                        await ctx.deps.nvr_client.set_alarm_schedule(
                            device.channel, saved.detection_type, saved.saved_hour_bitmask
                        )
                    if saved.saved_zone_mask:
                        logger.debug(
                            "[cmd %d] RestoreBitmasks: device '%s' %s restoring zone_mask=%s",
                            ctx.state.command_id,
                            device.name,
                            saved.detection_type,
                            saved.saved_zone_mask,
                        )
                        await ctx.deps.nvr_client.set_detection_zones(
                            device.channel, saved.detection_type, saved.saved_zone_mask
                        )
                    saved.is_consumed = True
                    await saved.save()
                    await log_activity(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        step_name="restore_bitmasks",
                        status=ActivityStatus.SUCCEEDED,
                        detail=f"Restored {saved.detection_type}",
                    )
                except Exception as e:
                    logger.warning(
                        "[cmd %d] RestoreBitmasks: device %d failed: %s",
                        ctx.state.command_id,
                        device_id,
                        e,
                    )
                    await log_activity(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        step_name="restore_bitmasks",
                        status=ActivityStatus.FAILED,
                        detail=str(e),
                    )
                    ctx.state.has_errors = True
                    ctx.state.device_results[device_id] = "failed"

        return SetPTZHomeNode()
