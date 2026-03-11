"""Tests for the Reolink NVR client — RED phase (TDD).

All tests mock the reolink-aio Host class so no real NVR is needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from remander.clients.reolink import ReolinkNVRClient
from remander.models.enums import DetectionType


@pytest.fixture
def mock_host() -> MagicMock:
    """Create a mock reolink-aio Host."""
    host = MagicMock()
    host.login = AsyncMock()
    host.logout = AsyncMock()
    host.get_host_data = AsyncMock()
    host.channels = [0, 1, 2]
    host.num_channels = 3
    host.camera_model.return_value = "RLC-810A"
    host.camera_name.return_value = "Front Door"
    host.camera_hardware_version.return_value = "IPC_523128M8MP"
    host.camera_sw_version.return_value = "v3.1.0.2347"
    host.camera_online.return_value = True
    host.set_ptz_command = AsyncMock()
    host.supported.return_value = True
    return host


@pytest.fixture
def client(mock_host: MagicMock) -> ReolinkNVRClient:
    with patch("remander.clients.reolink.Host", return_value=mock_host):
        return ReolinkNVRClient(
            host="192.168.1.100",
            port=443,
            username="admin",
            password="testpass",
        )


class TestLogin:
    async def test_login(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        await client.login()
        mock_host.login.assert_awaited_once()

    async def test_login_fetches_host_data(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        await client.login()
        mock_host.get_host_data.assert_awaited_once()


class TestLogout:
    async def test_logout(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        await client.logout()
        mock_host.logout.assert_awaited_once()


class TestListChannels:
    async def test_list_channels(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        channels = await client.list_channels()
        assert len(channels) == 3
        assert channels[0]["channel"] == 0
        assert channels[0]["name"] == "Front Door"
        assert channels[0]["model"] == "RLC-810A"

    async def test_list_channels_includes_metadata(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        channels = await client.list_channels()
        ch = channels[0]
        assert "hw_version" in ch
        assert "firmware" in ch
        assert "online" in ch


class TestGetChannelInfo:
    async def test_get_channel_info(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        info = await client.get_channel_info(0)
        assert info["channel"] == 0
        assert info["name"] == "Front Door"
        assert info["model"] == "RLC-810A"
        assert info["hw_version"] == "IPC_523128M8MP"
        assert info["firmware"] == "v3.1.0.2347"
        assert info["online"] is True


class TestAlarmSchedule:
    async def test_get_alarm_schedule(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        mock_host._host = "192.168.1.100"
        mock_host._port = 443
        mock_host.token = "test_token"

        # Mock the HTTP call for alarm schedule
        expected_bitmask = "111111111111111111111111"
        with patch.object(ReolinkNVRClient, "_api_get_alarm", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_bitmask
            result = await client.get_alarm_schedule(0, DetectionType.MOTION)
            assert result == expected_bitmask
            mock_get.assert_awaited_once_with(0, DetectionType.MOTION)

    async def test_set_alarm_schedule(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        bitmask = "000000111111111111110000"
        with patch.object(ReolinkNVRClient, "_api_set_alarm", new_callable=AsyncMock) as mock_set:
            await client.set_alarm_schedule(0, DetectionType.MOTION, bitmask)
            mock_set.assert_awaited_once_with(0, DetectionType.MOTION, bitmask)


class TestAlarmScheduleAPIImpl:
    """Tests for _api_get_alarm and _api_set_alarm using mocked send()."""

    async def test_api_get_alarm_returns_bitmask(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(
            return_value=[{"value": {"Push": {"schedule": {"table": {"MD": "1" * 168}}}}}]
        )
        result = await client._api_get_alarm(0, DetectionType.MOTION)
        assert result == "1" * 168

    async def test_api_get_alarm_uses_correct_key_for_person(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(
            return_value=[
                {"value": {"Push": {"schedule": {"table": {"MD": "0" * 168, "AI_PEOPLE": "1" * 168}}}}}
            ]
        )
        result = await client._api_get_alarm(0, DetectionType.PERSON)
        assert result == "1" * 168

    async def test_api_get_alarm_uses_GetPushV20(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(
            return_value=[{"value": {"Push": {"schedule": {"table": {"MD": "1" * 168}}}}}]
        )
        await client._api_get_alarm(0, DetectionType.MOTION)
        cmd = mock_host.send.call_args[0][0][0]["cmd"]
        assert cmd == "GetPushV20"

    async def test_api_get_alarm_uses_GetPush_for_legacy(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=0)
        mock_host.send = AsyncMock(
            return_value=[{"value": {"Push": {"schedule": {"table": "1" * 168}}}}]
        )
        result = await client._api_get_alarm(0, DetectionType.MOTION)
        assert result == "1" * 168
        cmd = mock_host.send.call_args[0][0][0]["cmd"]
        assert cmd == "GetPush"

    async def test_api_set_alarm_expands_24_char_bitmask_to_168(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(return_value=[{}])
        await client._api_set_alarm(0, DetectionType.MOTION, "0" * 24)
        body = mock_host.send.call_args[0][0][0]
        table = body["param"]["Push"]["schedule"]["table"]
        assert table["MD"] == "0" * 168

    async def test_api_set_alarm_uses_168_char_bitmask_unchanged(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(return_value=[{}])
        bitmask = "1" * 100 + "0" * 68
        await client._api_set_alarm(0, DetectionType.MOTION, bitmask)
        body = mock_host.send.call_args[0][0][0]
        table = body["param"]["Push"]["schedule"]["table"]
        assert table["MD"] == bitmask

    async def test_api_set_alarm_uses_SetPushV20_with_correct_key(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(return_value=[{}])
        await client._api_set_alarm(0, DetectionType.PERSON, "0" * 24)
        body = mock_host.send.call_args[0][0][0]
        assert body["cmd"] == "SetPushV20"
        assert "AI_PEOPLE" in body["param"]["Push"]["schedule"]["table"]
        assert body["param"]["Push"]["schedule"]["channel"] == 0

    async def test_api_set_alarm_vehicle_uses_AI_VEHICLE(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.api_version = MagicMock(return_value=1)
        mock_host.send = AsyncMock(return_value=[{}])
        await client._api_set_alarm(0, DetectionType.VEHICLE, "0" * 24)
        body = mock_host.send.call_args[0][0][0]
        table = body["param"]["Push"]["schedule"]["table"]
        assert "AI_VEHICLE" in table


class TestDetectionZones:
    async def test_get_detection_zones(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        expected_mask = "1" * 4800
        with patch.object(ReolinkNVRClient, "_api_get_zones", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_mask
            result = await client.get_detection_zones(0, DetectionType.MOTION)
            assert result == expected_mask

    async def test_set_detection_zones(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mask = "1" * 4800
        with patch.object(ReolinkNVRClient, "_api_set_zones", new_callable=AsyncMock) as mock_set:
            await client.set_detection_zones(0, DetectionType.MOTION, mask)
            mock_set.assert_awaited_once_with(0, DetectionType.MOTION, mask)


class TestPTZ:
    async def test_move_to_preset(self, client: ReolinkNVRClient, mock_host: MagicMock) -> None:
        await client.move_to_preset(0, preset_index=1, speed=50)
        mock_host.set_ptz_command.assert_awaited_once_with(0, preset=1, speed=50)

    def test_get_ptz_presets_returns_name_to_id_dict(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.ptz_presets.return_value = {"Back Yard": 1, "Gate": 2, "Driveway": 3}
        result = client.get_ptz_presets(0)
        assert result == {"Back Yard": 1, "Gate": 2, "Driveway": 3}
        mock_host.ptz_presets.assert_called_once_with(0)

    def test_get_ptz_presets_returns_empty_dict_when_no_presets(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.ptz_presets.return_value = {}
        result = client.get_ptz_presets(0)
        assert result == {}


class TestChannelOnline:
    async def test_is_channel_online_true(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.camera_online.return_value = True
        assert await client.is_channel_online(0) is True

    async def test_is_channel_online_false(
        self, client: ReolinkNVRClient, mock_host: MagicMock
    ) -> None:
        mock_host.camera_online.return_value = False
        assert await client.is_channel_online(1) is False
