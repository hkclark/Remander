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

    Login is intentionally minimal: only the authentication token exchange plus a
    single batched GetDevInfo + GetChannelstatus request (sets is_nvr and channel
    online state).  All other data is fetched lazily on first use so that the
    critical workflow path pays only for what it actually needs.

    Methods that require full host discovery (list_channels, get_ptz_presets,
    get_push_schedules) call _ensure_host_data() internally, which runs
    get_host_data() once and caches the result.

    The push schedule API version (GetPushV20 vs legacy GetPush) is detected
    once on first use via _detect_push_v20() and cached for the lifetime of
    this client instance.
    """

    host: str
    port: int
    username: str
    password: str
    use_https: bool = False
    timeout: int = 15
    _nvr: Host = attrs.field(init=False)
    # True once get_host_data() has been called (needed for admin operations)
    _host_data_loaded: bool = attrs.field(init=False, default=False)
    # None = not yet detected, True = GetPushV20 supported, False = legacy GetPush
    _push_v20: bool | None = attrs.field(init=False, default=None)

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
        """Authenticate with the NVR and perform minimal initialisation.

        Only two commands are sent after the token exchange:
          - GetDevInfo   → sets is_nvr so camera_online() works correctly
          - GetChannelstatus → seeds _channel_online and _channels

        This replaces the previous get_host_data() call which sent ~15 commands
        and took ~8s. Full host data is fetched lazily when needed.
        """
        logger.info("NVR login to %s:%s", self.host, self.port)
        t0 = time.monotonic()
        await self._nvr.login()
        # Single batched request: device type + channel online/offline state
        body = [
            {"cmd": "GetDevInfo", "action": 0, "param": {}},
            {"cmd": "GetChannelstatus"},
        ]
        json_data = await self._nvr.send(body, expected_response_type="json")
        if json_data:
            self._nvr.map_host_json_response(json_data)
        elapsed = time.monotonic() - t0
        logger.info("NVR login completed in %.1fs", elapsed)

    async def logout(self) -> None:
        """Close the NVR session."""
        logger.info("NVR logout from %s:%s", self.host, self.port)
        await self._nvr.logout()

    async def list_channels(self) -> list[dict]:
        """Return metadata for all connected camera channels."""
        await self._ensure_host_data()
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

    async def get_ptz_presets(self, channel: int) -> dict[str, int]:
        """Return available PTZ presets for a channel as {name: preset_id}.

        Requires full host data (populated on demand via get_host_data()).
        """
        await self._ensure_host_data()
        return self._nvr.ptz_presets(channel)

    async def get_push_schedules(self) -> list[dict]:
        """Fetch push notification schedule tables for all channels.

        Returns a list of dicts, one per channel:
            {"channel": int, "name": str, "table": {"MD": "...", "AI_PEOPLE": "...", ...}}

        Uses the GetPushV20 API (falls back to GetPush for legacy firmware).
        Leverages reolink-aio's send() to handle auth and HTTP transport.
        """
        await self._ensure_host_data()
        t0 = time.monotonic()
        results = []
        use_v20 = await self._detect_push_v20(next(iter(self._nvr.channels), 0))
        for ch in self._nvr.channels:
            if use_v20:
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

    async def refresh_channel_states(self) -> None:
        """Refresh channel online/offline status from the NVR.

        Sends a targeted GetChannelstatus request and processes the response
        through reolink-aio's normal response mapper so that is_channel_online()
        reflects the current state. Works whether or not _channels is populated.
        """
        await self._nvr.get_state("GetChannelstatus")

    async def is_channel_online(self, channel: int) -> bool:
        """Check if a camera channel is currently online (reads in-memory cache)."""
        online = self._nvr.camera_online(channel)
        logger.debug("NVR channel %d online=%s", channel, online)
        return online

    # --- Private helpers ---

    async def _ensure_host_data(self) -> None:
        """Fetch full host data if not already loaded.

        get_host_data() populates camera names, models, firmware versions, PTZ
        presets, and API capability versions. It is only needed for admin operations
        (channel listing, PTZ preset discovery, push schedule inspection) and is
        not called during normal workflow execution.
        """
        if not self._host_data_loaded:
            logger.info("NVR fetching full host data (first admin request)")
            await self._nvr.get_host_data()
            self._host_data_loaded = True
            self._push_v20 = self._nvr.api_version("GetPush") >= 1

    async def _detect_push_v20(self, channel: int) -> bool:
        """Detect and cache whether this NVR supports GetPushV20.

        Tries GetPushV20 once; if the NVR returns a successful response (code=0)
        the result is cached as True, otherwise False (falls back to legacy GetPush).
        If full host data was already loaded, the API version is read from the
        reolink-aio capability cache instead.
        """
        if self._push_v20 is not None:
            return self._push_v20
        body = [{"cmd": "GetPushV20", "action": 0, "param": {"channel": channel}}]
        response = await self._nvr.send(body, expected_response_type="json")
        self._push_v20 = bool(response) and response[0].get("code", 1) == 0
        logger.info(
            "NVR push schedule API detected: %s",
            "GetPushV20" if self._push_v20 else "GetPush (legacy)",
        )
        return self._push_v20

    # --- Detection type → Reolink push schedule table key ---

    _PUSH_SCHEDULE_KEY: dict[DetectionType, str] = {
        DetectionType.MOTION: "MD",
        DetectionType.PERSON: "AI_PEOPLE",
        DetectionType.VEHICLE: "AI_VEHICLE",
        DetectionType.ANIMAL: "AI_DOG_CAT",
        DetectionType.FACE: "AI_FACE",
        DetectionType.PACKAGE: "AI_PACKAGE",
    }

    async def _api_get_alarm(self, channel: int, detection_type: DetectionType) -> str:
        """Fetch alarm schedule bitmask from NVR push notification schedule."""
        nvr_key = self._PUSH_SCHEDULE_KEY[detection_type]
        if await self._detect_push_v20(channel):
            body = [{"cmd": "GetPushV20", "action": 0, "param": {"channel": channel}}]
        else:
            body = [{"cmd": "GetPush", "action": 0, "param": {"channel": channel}}]
        response = await self._nvr.send(body, expected_response_type="json")
        if not response:
            raise RuntimeError(f"Empty response getting push schedule for ch={channel}")
        value = response[0].get("value", {})
        schedule = value.get("Push", {}).get("schedule", {})
        table = schedule.get("table", {})
        if isinstance(table, str):
            # Legacy GetPush: single flat string for MD only
            if detection_type == DetectionType.MOTION:
                return table
            raise RuntimeError(f"Legacy push schedule does not support {detection_type}")
        bitmask = table.get(nvr_key, "")
        if not bitmask:
            raise RuntimeError(f"No {nvr_key} in push schedule table for ch={channel}")
        return bitmask

    async def _api_set_alarm(
        self, channel: int, detection_type: DetectionType, hour_bitmask: str
    ) -> None:
        """Set alarm schedule bitmask in NVR push notification schedule.

        Accepts 24-char (per-hour) or 168-char (7 days × 24 hours) bitmasks.
        24-char bitmasks are expanded to 168 chars by repeating for each day.
        """
        nvr_key = self._PUSH_SCHEDULE_KEY[detection_type]
        # Expand 24-char per-hour bitmask to 168-char (7 days × 24 hours/day)
        nvr_bitmask = hour_bitmask * 7 if len(hour_bitmask) == 24 else hour_bitmask
        if await self._detect_push_v20(channel):
            body = [
                {
                    "cmd": "SetPushV20",
                    "action": 0,
                    "param": {
                        "Push": {"schedule": {"channel": channel, "table": {nvr_key: nvr_bitmask}}}
                    },
                }
            ]
        else:
            body = [
                {
                    "cmd": "SetPush",
                    "action": 0,
                    "param": {"Push": {"schedule": {"channel": channel, "table": nvr_bitmask}}},
                }
            ]
        await self._nvr.send(body, expected_response_type="json")

    async def _api_get_zones(self, channel: int, detection_type: DetectionType) -> str:
        """Fetch detection zone mask via direct NVR HTTP API."""
        raise NotImplementedError("Detection zone read — requires integration testing")

    async def _api_set_zones(
        self, channel: int, detection_type: DetectionType, zone_mask: str
    ) -> None:
        """Set detection zone mask via direct NVR HTTP API."""
        raise NotImplementedError("Detection zone write — requires integration testing")
