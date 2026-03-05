"""Tests for NVR sync service — comparing NVR channels against existing devices."""

from remander.models.enums import ChannelSyncStatus, DeviceBrand, DeviceType
from remander.services.nvr_sync import (
    compare_channels,
    create_device_from_channel,
    sync_all_channels,
    update_device_from_channel,
)
from tests.factories import create_camera


class TestCompareChannels:
    async def test_new_channel_no_existing_device(self, setup_db: None) -> None:
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            }
        ]
        results = compare_channels(channels, [])
        assert len(results) == 1
        assert results[0].status == ChannelSyncStatus.NEW
        assert results[0].device_id is None

    async def test_ok_when_fields_match(self, setup_db: None) -> None:
        device = await create_camera(
            name="Front", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            }
        ]
        results = compare_channels(channels, [device])
        assert results[0].status == ChannelSyncStatus.OK
        assert results[0].device_id == device.id
        assert len(results[0].diffs) == 0

    async def test_changed_when_name_differs(self, setup_db: None) -> None:
        device = await create_camera(
            name="OldName", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "NewName",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            }
        ]
        results = compare_channels(channels, [device])
        assert results[0].status == ChannelSyncStatus.CHANGED
        assert len(results[0].diffs) == 1
        assert results[0].diffs[0].field_name == "name"
        assert results[0].diffs[0].nvr_value == "NewName"
        assert results[0].diffs[0].db_value == "OldName"

    async def test_multiple_diffs(self, setup_db: None) -> None:
        device = await create_camera(
            name="Front", channel=0, model_name="RLC-510A", hw_version="v1", firmware="2.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            }
        ]
        results = compare_channels(channels, [device])
        assert results[0].status == ChannelSyncStatus.CHANGED
        diff_fields = {d.field_name for d in results[0].diffs}
        assert diff_fields == {"model_name", "firmware"}

    async def test_none_and_empty_string_treated_as_equivalent(self, setup_db: None) -> None:
        device = await create_camera(
            name="Front", channel=0, model_name=None, hw_version="", firmware=None
        )
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "",
                "hw_version": None,
                "firmware": "",
                "online": True,
            }
        ]
        results = compare_channels(channels, [device])
        assert results[0].status == ChannelSyncStatus.OK

    async def test_mixed_statuses(self, setup_db: None) -> None:
        device = await create_camera(
            name="Front", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
            {
                "channel": 1,
                "name": "Back",
                "model": "RLC-520A",
                "hw_version": "v2",
                "firmware": "2.0",
                "online": False,
            },
        ]
        results = compare_channels(channels, [device])
        assert results[0].status == ChannelSyncStatus.OK
        assert results[1].status == ChannelSyncStatus.NEW


class TestCreateDeviceFromChannel:
    async def test_creates_reolink_camera(self, setup_db: None) -> None:
        channel_data = {
            "channel": 0,
            "name": "Front",
            "model": "RLC-810A",
            "hw_version": "v1",
            "firmware": "3.0",
            "online": True,
        }
        device = await create_device_from_channel(channel_data)
        assert device.name == "Front"
        assert device.channel == 0
        assert device.device_type == DeviceType.CAMERA
        assert device.brand == DeviceBrand.REOLINK
        assert device.model_name == "RLC-810A"
        assert device.hw_version == "v1"
        assert device.firmware == "3.0"

    async def test_creates_with_none_fields(self, setup_db: None) -> None:
        channel_data = {
            "channel": 5,
            "name": "Cam5",
            "model": None,
            "hw_version": None,
            "firmware": None,
            "online": False,
        }
        device = await create_device_from_channel(channel_data)
        assert device.name == "Cam5"
        assert device.channel == 5
        assert device.model_name is None


class TestUpdateDeviceFromChannel:
    async def test_updates_fields(self, setup_db: None) -> None:
        device = await create_camera(
            name="OldName", channel=0, model_name="OldModel", hw_version="v1", firmware="1.0"
        )
        channel_data = {
            "channel": 0,
            "name": "NewName",
            "model": "NewModel",
            "hw_version": "v2",
            "firmware": "2.0",
            "online": True,
        }
        updated = await update_device_from_channel(device.id, channel_data)
        assert updated is not None
        assert updated.name == "NewName"
        assert updated.model_name == "NewModel"
        assert updated.hw_version == "v2"
        assert updated.firmware == "2.0"

    async def test_returns_none_for_nonexistent(self, setup_db: None) -> None:
        channel_data = {
            "channel": 0,
            "name": "X",
            "model": "Y",
            "hw_version": "v1",
            "firmware": "1.0",
            "online": True,
        }
        result = await update_device_from_channel(9999, channel_data)
        assert result is None


class TestSyncAllChannels:
    async def test_creates_new_and_updates_changed(self, setup_db: None) -> None:
        existing = await create_camera(
            name="OldName", channel=0, model_name="RLC-810A", hw_version="v1", firmware="1.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "NewName",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "2.0",
                "online": True,
            },
            {
                "channel": 1,
                "name": "Back",
                "model": "RLC-520A",
                "hw_version": "v2",
                "firmware": "3.0",
                "online": False,
            },
        ]
        created, updated = await sync_all_channels(channels, [existing])
        assert created == 1
        assert updated == 1

    async def test_skips_ok_channels(self, setup_db: None) -> None:
        existing = await create_camera(
            name="Front", channel=0, model_name="RLC-810A", hw_version="v1", firmware="3.0"
        )
        channels = [
            {
                "channel": 0,
                "name": "Front",
                "model": "RLC-810A",
                "hw_version": "v1",
                "firmware": "3.0",
                "online": True,
            },
        ]
        created, updated = await sync_all_channels(channels, [existing])
        assert created == 0
        assert updated == 0
