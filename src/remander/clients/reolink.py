"""Reolink NVR client — wraps reolink-aio for camera configuration."""

import attrs
from reolink_aio.api import Host

from remander.models.enums import DetectionType


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
    _nvr: Host = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        self._nvr = Host(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    async def login(self) -> None:
        """Authenticate with the NVR and fetch host data."""
        await self._nvr.login()
        await self._nvr.get_host_data()

    async def logout(self) -> None:
        """Close the NVR session."""
        await self._nvr.logout()

    async def list_channels(self) -> list[dict]:
        """Return metadata for all connected camera channels."""
        return [await self.get_channel_info(ch) for ch in self._nvr.channels]

    async def get_channel_info(self, channel: int) -> dict:
        """Get detailed info for a single camera channel."""
        return {
            "channel": channel,
            "name": self._nvr.camera_name(channel),
            "model": self._nvr.camera_model(channel),
            "hw_version": self._nvr.camera_hardware_version(channel),
            "firmware": self._nvr.camera_sw_version(channel),
            "online": self._nvr.camera_online(channel),
        }

    async def get_alarm_schedule(self, channel: int, detection_type: DetectionType) -> str:
        """Get the current notification bitmask for a channel/detection type.

        Uses direct NVR HTTP API since reolink-aio doesn't expose schedule bitmasks.
        """
        return await self._api_get_alarm(channel, detection_type)

    async def set_alarm_schedule(
        self, channel: int, detection_type: DetectionType, hour_bitmask: str
    ) -> None:
        """Set the notification bitmask for a channel/detection type."""
        await self._api_set_alarm(channel, detection_type, hour_bitmask)

    async def get_detection_zones(self, channel: int, detection_type: DetectionType) -> str:
        """Get the current zone mask for a channel/detection type."""
        return await self._api_get_zones(channel, detection_type)

    async def set_detection_zones(
        self, channel: int, detection_type: DetectionType, zone_mask: str
    ) -> None:
        """Set the zone mask for a channel/detection type."""
        await self._api_set_zones(channel, detection_type, zone_mask)

    async def move_to_preset(
        self, channel: int, preset_index: int, speed: int | None = None
    ) -> None:
        """Move a PTZ camera to a preset position."""
        await self._nvr.set_ptz_command(channel, preset=preset_index, speed=speed)

    async def is_channel_online(self, channel: int) -> bool:
        """Check if a camera channel is currently online."""
        return self._nvr.camera_online(channel)

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
