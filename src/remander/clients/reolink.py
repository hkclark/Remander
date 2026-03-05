"""Reolink NVR client — wraps reolink-aio for camera configuration."""

import logging
import time

import attrs
from reolink_aio.api import Host

from remander.models.enums import DetectionType

logger = logging.getLogger(__name__)


@attrs.define
class ReolinkNVRClient:
    """High-level async client for a Reolink NVR.

    Uses reolink-aio for login/logout/PTZ/channel info.
    Uses direct HTTP API calls for alarm schedule and detection zone operations
    that reolink-aio doesn't expose as public methods.
    """

    host: str
    port: int
    username: str
    password: str
    use_https: bool = False
    timeout: int = 15
    _nvr: Host = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        self._nvr = Host(
            host=self.host,
            port=self.port,
            use_https=self.use_https,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
        )

    async def login(self) -> None:
        """Authenticate with the NVR and fetch host data."""
        logger.info("NVR login to %s:%s", self.host, self.port)
        t0 = time.monotonic()
        await self._nvr.login()
        await self._nvr.get_host_data()
        elapsed = time.monotonic() - t0
        logger.info("NVR login completed in %.1fs", elapsed)

    async def logout(self) -> None:
        """Close the NVR session."""
        logger.info("NVR logout from %s:%s", self.host, self.port)
        await self._nvr.logout()

    async def list_channels(self) -> list[dict]:
        """Return metadata for all connected camera channels."""
        t0 = time.monotonic()
        channels = [await self.get_channel_info(ch) for ch in self._nvr.channels]
        elapsed = time.monotonic() - t0
        logger.info("NVR listed %d channels in %.1fs", len(channels), elapsed)
        logger.debug("NVR channel data: %s", channels)
        return channels

    async def get_channel_info(self, channel: int) -> dict:
        """Get detailed info for a single camera channel."""
        info = {
            "channel": channel,
            "name": self._nvr.camera_name(channel),
            "model": self._nvr.camera_model(channel),
            "hw_version": self._nvr.camera_hardware_version(channel),
            "firmware": self._nvr.camera_sw_version(channel),
            "online": self._nvr.camera_online(channel),
        }
        logger.debug("NVR channel %d info: %s", channel, info)
        return info

    async def get_alarm_schedule(self, channel: int, detection_type: DetectionType) -> str:
        """Get the current notification bitmask for a channel/detection type.

        Uses direct NVR HTTP API since reolink-aio doesn't expose schedule bitmasks.
        """
        logger.info("NVR get alarm schedule ch=%d type=%s", channel, detection_type.value)
        t0 = time.monotonic()
        result = await self._api_get_alarm(channel, detection_type)
        elapsed = time.monotonic() - t0
        logger.info("NVR got alarm schedule in %.1fs", elapsed)
        logger.debug("NVR alarm schedule ch=%d: %s", channel, result)
        return result

    async def set_alarm_schedule(
        self, channel: int, detection_type: DetectionType, hour_bitmask: str
    ) -> None:
        """Set the notification bitmask for a channel/detection type."""
        logger.info(
            "NVR set alarm schedule ch=%d type=%s bitmask=%s",
            channel,
            detection_type.value,
            hour_bitmask,
        )
        t0 = time.monotonic()
        await self._api_set_alarm(channel, detection_type, hour_bitmask)
        elapsed = time.monotonic() - t0
        logger.info("NVR set alarm schedule in %.1fs", elapsed)

    async def get_detection_zones(self, channel: int, detection_type: DetectionType) -> str:
        """Get the current zone mask for a channel/detection type."""
        logger.info("NVR get detection zones ch=%d type=%s", channel, detection_type.value)
        t0 = time.monotonic()
        result = await self._api_get_zones(channel, detection_type)
        elapsed = time.monotonic() - t0
        logger.info("NVR got detection zones in %.1fs", elapsed)
        logger.debug("NVR detection zones ch=%d: %s", channel, result)
        return result

    async def set_detection_zones(
        self, channel: int, detection_type: DetectionType, zone_mask: str
    ) -> None:
        """Set the zone mask for a channel/detection type."""
        logger.info(
            "NVR set detection zones ch=%d type=%s mask=%s",
            channel,
            detection_type.value,
            zone_mask,
        )
        t0 = time.monotonic()
        await self._api_set_zones(channel, detection_type, zone_mask)
        elapsed = time.monotonic() - t0
        logger.info("NVR set detection zones in %.1fs", elapsed)

    async def move_to_preset(
        self, channel: int, preset_index: int, speed: int | None = None
    ) -> None:
        """Move a PTZ camera to a preset position."""
        logger.info("NVR move ch=%d to preset %d (speed=%s)", channel, preset_index, speed)
        t0 = time.monotonic()
        await self._nvr.set_ptz_command(channel, preset=preset_index, speed=speed)
        elapsed = time.monotonic() - t0
        logger.info("NVR PTZ move completed in %.1fs", elapsed)

    async def get_push_schedules(self) -> list[dict]:
        """Fetch push notification schedule tables for all channels.

        Returns a list of dicts, one per channel:
            {"channel": int, "name": str, "table": {"MD": "...", "AI_PEOPLE": "...", ...}}

        Uses the GetPushV20 API (falls back to GetPush for legacy firmware).
        Leverages reolink-aio's send() to handle auth and HTTP transport.
        """
        t0 = time.monotonic()
        results = []
        for ch in self._nvr.channels:
            if self._nvr.api_version("GetPush") >= 1:
                body = [{"cmd": "GetPushV20", "action": 1, "param": {"channel": ch}}]
            else:
                body = [{"cmd": "GetPush", "action": 1, "param": {"channel": ch}}]

            response = await self._nvr.send(body, expected_response_type="json")
            logger.debug("Push schedule response ch=%d: %s", ch, response)

            table = {}
            if response and len(response) > 0:
                value = response[0].get("value", {})
                push = value.get("Push", {})
                schedule = push.get("schedule", {})
                raw_table = schedule.get("table", {})
                if isinstance(raw_table, dict):
                    table = raw_table
                elif isinstance(raw_table, str):
                    # Legacy GetPush returns a single flat string for MD only
                    table = {"MD": raw_table}

            results.append({
                "channel": ch,
                "name": self._nvr.camera_name(ch),
                "table": table,
            })

        elapsed = time.monotonic() - t0
        logger.info("NVR fetched push schedules for %d channels in %.1fs", len(results), elapsed)
        return results

    async def is_channel_online(self, channel: int) -> bool:
        """Check if a camera channel is currently online."""
        online = self._nvr.camera_online(channel)
        logger.debug("NVR channel %d online=%s", channel, online)
        return online

    # --- Direct HTTP API stubs ---
    # These will be implemented with httpx calls using the NVR session token
    # when we have access to a real NVR for integration testing.

    async def _api_get_alarm(self, channel: int, detection_type: DetectionType) -> str:
        """Fetch alarm schedule bitmask via direct NVR HTTP API."""
        raise NotImplementedError("Direct NVR API call — requires integration testing")

    async def _api_set_alarm(
        self, channel: int, detection_type: DetectionType, hour_bitmask: str
    ) -> None:
        """Set alarm schedule bitmask via direct NVR HTTP API."""
        raise NotImplementedError("Direct NVR API call — requires integration testing")

    async def _api_get_zones(self, channel: int, detection_type: DetectionType) -> str:
        """Fetch detection zone mask via direct NVR HTTP API."""
        raise NotImplementedError("Direct NVR API call — requires integration testing")

    async def _api_set_zones(
        self, channel: int, detection_type: DetectionType, zone_mask: str
    ) -> None:
        """Set detection zone mask via direct NVR HTTP API."""
        raise NotImplementedError("Direct NVR API call — requires integration testing")
