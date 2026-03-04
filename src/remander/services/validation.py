"""Post-command validation — compares NVR actual values to expected bitmasks."""

import logging

from remander.clients.reolink import ReolinkNVRClient
from remander.models.device import Device
from remander.models.enums import ActivityStatus, DetectionType
from remander.services.activity import log_activity

logger = logging.getLogger(__name__)


async def validate_device_bitmasks(
    device: Device,
    expected: dict[DetectionType, dict],
    nvr_client: ReolinkNVRClient,
) -> list[dict]:
    """Compare NVR actual bitmask values to expected values for a single device.

    Returns a list of discrepancy dicts (empty if all match).
    Does not modify command status — discrepancies are informational warnings.
    """
    if device.channel is None:
        return []

    discrepancies: list[dict] = []

    for detection_type, values in expected.items():
        try:
            actual_hour = await nvr_client.get_alarm_schedule(device.channel, detection_type)
            actual_zone = await nvr_client.get_detection_zones(device.channel, detection_type)

            if actual_hour != values.get("hour_bitmask"):
                discrepancies.append(
                    {
                        "device": device.name,
                        "device_id": device.id,
                        "detection_type": str(detection_type),
                        "field": "hour_bitmask",
                        "expected": values.get("hour_bitmask"),
                        "actual": actual_hour,
                    }
                )

            if actual_zone != values.get("zone_mask"):
                discrepancies.append(
                    {
                        "device": device.name,
                        "device_id": device.id,
                        "detection_type": str(detection_type),
                        "field": "zone_mask",
                        "expected": values.get("zone_mask"),
                        "actual": actual_zone,
                    }
                )

        except Exception as e:
            logger.warning("Validation query failed for device %d: %s", device.id, e)
            discrepancies.append(
                {
                    "device": device.name,
                    "device_id": device.id,
                    "detection_type": str(detection_type),
                    "field": "query_error",
                    "expected": None,
                    "actual": str(e),
                }
            )

    return discrepancies


async def validate_command_results(
    command_id: int,
    expected_bitmasks: dict[int, dict[DetectionType, dict]],
    nvr_client: ReolinkNVRClient,
) -> list[dict]:
    """Validate all devices for a command, logging discrepancies as activity entries.

    Returns aggregated list of all discrepancies across devices.
    Does not modify command status.
    """
    all_discrepancies: list[dict] = []

    for device_id, expectations in expected_bitmasks.items():
        device = await Device.get(id=device_id)
        device_discrepancies = await validate_device_bitmasks(device, expectations, nvr_client)
        all_discrepancies.extend(device_discrepancies)

        for discrepancy in device_discrepancies:
            await log_activity(
                command_id=command_id,
                device_id=device_id,
                step_name="validate",
                status=ActivityStatus.FAILED,
                detail=f"{discrepancy['field']} mismatch for {discrepancy['detection_type']}",
            )

    if not all_discrepancies:
        await log_activity(
            command_id=command_id,
            step_name="validate",
            status=ActivityStatus.SUCCEEDED,
            detail="All bitmasks match",
        )

    return all_discrepancies
