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


def _bitmasks_match(expected: str, actual: str) -> bool:
    """Compare bitmasks, handling 24-char internal vs 168-char NVR format.

    Our internal representation is a 24-char single-day pattern applied uniformly
    to every day of the week. The NVR stores 168 chars (7 days × 24 hours). We set
    all 7 days identically, so a valid match means actual == expected repeated 7 times.
    """
    if expected == actual:
        return True
    if len(expected) == 24 and len(actual) == 168:
        return actual == expected * 7
    return False


def _fmt_bitmask(value: str) -> str:
    """Return a compact bitmask representation for log lines.

    168-char NVR values are condensed to 'first_24 (×7 days)' for readability.
    """
    if len(value) == 168:
        return f"{value[:24]} (×7 days)"
    return value


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
                    expected_hour = expected.get("hour_bitmask")
                    expected_zone = expected.get("zone_mask")  # None when zone masks disabled

                    actual_hour = await ctx.deps.nvr_client.get_alarm_schedule(
                        device.channel, detection_type
                    )

                    if expected_zone is not None:
                        actual_zone = await ctx.deps.nvr_client.get_detection_zones(
                            device.channel, detection_type
                        )
                        logger.info(
                            "[cmd %d] Validate: device '%s' %s "
                            "hour_bitmask expected=%s actual=%s zone_mask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected_hour,
                            _fmt_bitmask(actual_hour),
                            expected_zone,
                            actual_zone,
                        )
                    else:
                        actual_zone = None
                        logger.info(
                            "[cmd %d] Validate: device '%s' %s hour_bitmask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected_hour,
                            _fmt_bitmask(actual_hour),
                        )

                    if not _bitmasks_match(expected_hour, actual_hour):
                        logger.warning(
                            "[cmd %d] Validate: MISMATCH device '%s' %s "
                            "hour_bitmask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected_hour,
                            _fmt_bitmask(actual_hour),
                        )
                        discrepancy = {
                            "device": device.name,
                            "device_id": device_id,
                            "channel": device.channel,
                            "detection_type": str(detection_type),
                            "field": "hour_bitmask",
                            "expected": expected_hour,
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

                    if expected_zone is not None and actual_zone != expected_zone:
                        logger.warning(
                            "[cmd %d] Validate: MISMATCH device '%s' %s "
                            "zone_mask expected=%s actual=%s",
                            ctx.state.command_id,
                            device.name,
                            detection_type,
                            expected_zone,
                            actual_zone,
                        )
                        discrepancy = {
                            "device": device.name,
                            "device_id": device_id,
                            "channel": device.channel,
                            "detection_type": str(detection_type),
                            "field": "zone_mask",
                            "expected": expected_zone,
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
