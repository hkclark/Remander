"""Power on/off/wait workflow nodes."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.device import Device
from remander.models.enums import ActivityStatus, DeviceBrand
from remander.services.activity import log_activity
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


async def _power_on_device(device: Device, deps: WorkflowDeps) -> None:
    """Send power-on to the appropriate client based on brand."""
    power_device = await Device.get(id=device.power_device_id)
    ip = power_device.ip_address
    if power_device.brand == DeviceBrand.TAPO:
        await deps.tapo_client.turn_on(ip)
    elif power_device.brand == DeviceBrand.SONOFF:
        await deps.sonoff_client.turn_on(ip)


async def _power_off_device(device: Device, deps: WorkflowDeps) -> None:
    """Send power-off to the appropriate client based on brand."""
    power_device = await Device.get(id=device.power_device_id)
    ip = power_device.ip_address
    if power_device.brand == DeviceBrand.TAPO:
        await deps.tapo_client.turn_off(ip)
    elif power_device.brand == DeviceBrand.SONOFF:
        await deps.sonoff_client.turn_off(ip)


@dataclass
class PowerOnNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Send power-on commands to power devices for cameras that need to come online."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> WaitForPowerOnNode:
        logger.info(
            "[cmd %d] PowerOn: powering on %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.power_device_id:
                logger.debug(
                    "[cmd %d] PowerOn: skipping device '%s' (no power_device_id)",
                    ctx.state.command_id,
                    device.name,
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.SKIPPED,
                    detail="No power device associated",
                )
                continue

            try:
                power_device = await Device.get(id=device.power_device_id)
                logger.info(
                    "[cmd %d] PowerOn: device '%s' via %s at %s",
                    ctx.state.command_id,
                    device.name,
                    power_device.brand,
                    power_device.ip_address,
                )
                await _power_on_device(device, ctx.deps)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning(
                    "*** ERROR: [cmd %d] PowerOn: device %d failed: %s", ctx.state.command_id, device_id, e
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = str(e)

        return WaitForPowerOnNode(
            timeout_seconds=ctx.deps.power_on_timeout_seconds,
            poll_interval_seconds=ctx.deps.power_on_poll_interval_seconds,
        )


@dataclass
class WaitForPowerOnNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Poll NVR until powered-on cameras appear online."""

    timeout_seconds: int = 120
    poll_interval_seconds: int = 10

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.models.enums import CommandType

        # Only wait for cameras with power devices
        cameras_to_wait = []
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.power_device_id and device.channel is not None:
                cameras_to_wait.append(device)

        # AWAY commands skip SaveBitmasks and go straight to PTZ calibration.
        # PAUSE commands save bitmasks (for later re-arm restore) before zeroing notifications.
        def _next_node() -> BaseNode[WorkflowState, WorkflowDeps]:
            from remander.workflows.nodes.ptz import PTZCalibrateNode
            from remander.workflows.nodes.save_restore import SaveBitmasksNode

            if ctx.state.command_type in (CommandType.SET_AWAY_NOW, CommandType.SET_AWAY_DELAYED):
                return PTZCalibrateNode()
            return SaveBitmasksNode()

        if not cameras_to_wait:
            logger.info(
                "[cmd %d] WaitForPowerOn: no cameras need power-on wait", ctx.state.command_id
            )
            return _next_node()

        logger.info(
            "[cmd %d] WaitForPowerOn: waiting for %d cameras (timeout=%ds): %s",
            ctx.state.command_id,
            len(cameras_to_wait),
            self.timeout_seconds,
            [d.name for d in cameras_to_wait],
        )
        start_time = time.monotonic()
        pending = {d.id: d for d in cameras_to_wait}

        while pending and (time.monotonic() - start_time) < self.timeout_seconds:
            await ctx.deps.nvr_client.refresh_channel_states()
            for device_id, device in list(pending.items()):
                try:
                    online = await ctx.deps.nvr_client.is_channel_online(device.channel)
                    if online:
                        elapsed = int(time.monotonic() - start_time)
                        logger.info(
                            "[cmd %d] WaitForPowerOn: device '%s' ch=%d online after %ds",
                            ctx.state.command_id,
                            device.name,
                            device.channel,
                            elapsed,
                        )
                        await log_activity(
                            command_id=ctx.state.command_id,
                            device_id=device_id,
                            step_name="wait_power_on",
                            status=ActivityStatus.SUCCEEDED,
                            detail="Camera online",
                        )
                        del pending[device_id]
                except Exception as e:
                    logger.warning(
                        "*** ERROR: [cmd %d] WaitForPowerOn: poll error device %d: %s",
                        ctx.state.command_id,
                        device_id,
                        e,
                    )

            if pending:
                await asyncio.sleep(self.poll_interval_seconds)

        # Mark timed-out cameras as failed
        for device_id in pending:
            logger.warning(
                "*** ERROR: [cmd %d] WaitForPowerOn: device %d timed out after %ds",
                ctx.state.command_id,
                device_id,
                self.timeout_seconds,
            )
            await log_activity(
                command_id=ctx.state.command_id,
                device_id=device_id,
                step_name="wait_power_on",
                status=ActivityStatus.FAILED,
                detail=f"Timeout after {self.timeout_seconds}s",
            )
            ctx.state.has_errors = True
            ctx.state.device_results[device_id] = f"Timeout after {self.timeout_seconds}s"

        settle = ctx.deps.power_on_settle_seconds
        logger.info(
            "[cmd %d] WaitForPowerOn: settling %ds before PTZ",
            ctx.state.command_id,
            settle,
        )
        await asyncio.sleep(settle)
        # Re-discover channels so cameras that came online after the initial NVR
        # login are registered in reolink-aio's _channels list before PTZ commands run.
        await ctx.deps.nvr_client.rediscover_channels()
        return _next_node()


@dataclass
class PowerOffNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Send power-off commands to power devices."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.validate import ValidateNode

        logger.info(
            "[cmd %d] PowerOff: powering off %d devices",
            ctx.state.command_id,
            len(ctx.state.device_ids),
        )
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.power_device_id:
                logger.debug(
                    "[cmd %d] PowerOff: skipping device '%s' (no power_device_id)",
                    ctx.state.command_id,
                    device.name,
                )
                continue

            try:
                power_device = await Device.get(id=device.power_device_id)
                logger.info(
                    "[cmd %d] PowerOff: device '%s' via %s at %s",
                    ctx.state.command_id,
                    device.name,
                    power_device.brand,
                    power_device.ip_address,
                )
                await _power_off_device(device, ctx.deps)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_off",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning(
                    "*** ERROR: [cmd %d] PowerOff: device %d failed: %s", ctx.state.command_id, device_id, e
                )
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_off",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = str(e)

        if ctx.state.mute_duration_seconds is not None:
            # HOME mute: wait for mute expiry before applying bitmasks.
            from remander.workflows.nodes.mute import WaitForMuteExpiryNode

            return WaitForMuteExpiryNode()
        return ValidateNode()
