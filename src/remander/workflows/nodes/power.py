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
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.power_device_id:
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.SKIPPED,
                    detail="No power device associated",
                )
                continue

            try:
                await _power_on_device(device, ctx.deps)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning("Failed to power on device %d: %s", device_id, e)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_on",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = "failed"

        return WaitForPowerOnNode()


@dataclass
class WaitForPowerOnNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Poll NVR until powered-on cameras appear online."""

    timeout_seconds: int = 120
    poll_interval_seconds: int = 10

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.ptz import PTZCalibrateNode

        # Only wait for cameras with power devices
        cameras_to_wait = []
        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if device.power_device_id and device.channel is not None:
                cameras_to_wait.append(device)

        if not cameras_to_wait:
            return PTZCalibrateNode()

        start_time = time.monotonic()
        pending = {d.id: d for d in cameras_to_wait}

        while pending and (time.monotonic() - start_time) < self.timeout_seconds:
            for device_id, device in list(pending.items()):
                try:
                    online = await ctx.deps.nvr_client.is_channel_online(device.channel)
                    if online:
                        await log_activity(
                            command_id=ctx.state.command_id,
                            device_id=device_id,
                            step_name="wait_power_on",
                            status=ActivityStatus.SUCCEEDED,
                            detail="Camera online",
                        )
                        del pending[device_id]
                except Exception as e:
                    logger.warning("Poll error for device %d: %s", device_id, e)

            if pending:
                await asyncio.sleep(self.poll_interval_seconds)

        # Mark timed-out cameras as failed
        for device_id in pending:
            await log_activity(
                command_id=ctx.state.command_id,
                device_id=device_id,
                step_name="wait_power_on",
                status=ActivityStatus.FAILED,
                detail=f"Timeout after {self.timeout_seconds}s",
            )
            ctx.state.has_errors = True
            ctx.state.device_results[device_id] = "failed"

        return PTZCalibrateNode()


@dataclass
class PowerOffNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Send power-off commands to power devices."""

    async def run(
        self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]
    ) -> BaseNode[WorkflowState, WorkflowDeps]:
        from remander.workflows.nodes.validate import ValidateNode

        for device_id in ctx.state.device_ids:
            device = await Device.get(id=device_id)
            if not device.power_device_id:
                continue

            try:
                await _power_off_device(device, ctx.deps)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_off",
                    status=ActivityStatus.SUCCEEDED,
                )
            except Exception as e:
                logger.warning("Failed to power off device %d: %s", device_id, e)
                await log_activity(
                    command_id=ctx.state.command_id,
                    device_id=device_id,
                    step_name="power_off",
                    status=ActivityStatus.FAILED,
                    detail=str(e),
                )
                ctx.state.has_errors = True
                ctx.state.device_results[device_id] = "failed"

        return ValidateNode()
