"""Post-command validation workflow node."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.device import Device
from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.workflows.nodes.nvr import NVRLogoutNode
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class ValidateNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Query the NVR to verify bitmasks match expected values."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> NVRLogoutNode:
        logger.info(
            "[cmd %d] Validate: verifying bitmasks for %d devices",
            ctx.state.command_id,
            len(ctx.state.expected_bitmasks),
        )
        for device_id in ctx.state.device_ids:
            if device_id not in ctx.state.expected_bitmasks:
                continue

            device = await Device.get(id=device_id)
            if device.channel is None:
                continue

            expectations = ctx.state.expected_bitmasks[device_id]
            for detection_type, expected in expectations.items():
                try:
                    actual_hour = await ctx.deps.nvr_client.get_alarm_schedule(
                        device.channel, detection_type
                    )
                    actual_zone = await ctx.deps.nvr_client.get_detection_zones(
                        device.channel, detection_type
                    )

                    logger.info(
                        "[cmd %d] Validate: device '%s' %s "
                        "hour_bitmask expected=%s actual=%s zone_mask expected=%s actual=%s",
                        ctx.state.command_id,
                        device.name,
                        detection_type,
                        expected.get("hour_bitmask"),
                        actual_hour,
                        expected.get("zone_mask"),
                        actual_zone,
                    )
                    if actual_hour != expected.get("hour_bitmask"):
                        logger.warning(
                            "[cmd %d] Validate: MISMATCH device '%s' %s "
                            "hour_bitmask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected.get("hour_bitmask"),
                            actual_hour,
                        )
                        discrepancy = {
                            "device": device.name,
                            "device_id": device_id,
                            "detection_type": str(detection_type),
                            "field": "hour_bitmask",
                            "expected": expected.get("hour_bitmask"),
                            "actual": actual_hour,
                        }
                        ctx.state.validation_discrepancies.append(discrepancy)
                        await log_activity(
                            command_id=ctx.state.command_id,
                            device_id=device_id,
                            step_name="validate",
                            status=ActivityStatus.FAILED,
                            detail=f"Hour bitmask mismatch for {detection_type}",
                        )

                    if actual_zone != expected.get("zone_mask"):
                        logger.warning(
                            "[cmd %d] Validate: MISMATCH device '%s' %s "
                            "zone_mask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected.get("zone_mask"),
                            actual_zone,
                        )
                        discrepancy = {
                            "device": device.name,
                            "device_id": device_id,
                            "detection_type": str(detection_type),
                            "field": "zone_mask",
                            "expected": expected.get("zone_mask"),
                            "actual": actual_zone,
                        }
                        ctx.state.validation_discrepancies.append(discrepancy)
                        await log_activity(
                            command_id=ctx.state.command_id,
                            device_id=device_id,
                            step_name="validate",
                            status=ActivityStatus.FAILED,
                            detail=f"Zone mask mismatch for {detection_type}",
                        )

                except Exception as e:
                    logger.warning(
                        "[cmd %d] Validate: device %d error: %s", ctx.state.command_id, device_id, e
                    )
                    await log_activity(
                        command_id=ctx.state.command_id,
                        device_id=device_id,
                        step_name="validate",
                        status=ActivityStatus.FAILED,
                        detail=str(e),
                    )

        if ctx.state.validation_discrepancies:
            logger.warning(
                "[cmd %d] Validate: %d discrepancies found",
                ctx.state.command_id,
                len(ctx.state.validation_discrepancies),
            )
        if not ctx.state.validation_discrepancies:
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="validate",
                status=ActivityStatus.SUCCEEDED,
                detail="All bitmasks match",
            )

        return NVRLogoutNode()
