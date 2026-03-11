"""Tests for bulk tag service — channel spec parsing and device filtering."""

import pytest

from remander.services.bulk_tag import find_devices_for_bulk, parse_channel_spec
from tests.factories import create_camera, create_power_device


class TestParseChannelSpec:
    def test_single_number(self) -> None:
        assert parse_channel_spec("1") == {1}

    def test_comma_list(self) -> None:
        assert parse_channel_spec("1, 2, 3") == {1, 2, 3}

    def test_range(self) -> None:
        assert parse_channel_spec("2-4") == {2, 3, 4}

    def test_mixed(self) -> None:
        assert parse_channel_spec("2-4,6,8-9") == {2, 3, 4, 6, 8, 9}

    def test_empty_string(self) -> None:
        assert parse_channel_spec("") == set()

    def test_whitespace_only(self) -> None:
        assert parse_channel_spec("   ") == set()

    def test_spaces_around_range(self) -> None:
        assert parse_channel_spec("1 - 3") == {1, 2, 3}

    def test_spaces_around_commas(self) -> None:
        assert parse_channel_spec(" 1 , 3 , 5 ") == {1, 3, 5}

    def test_invalid_text_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_channel_spec("abc")

    def test_invalid_range_reversed_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_channel_spec("5-3")

    def test_invalid_range_text_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_channel_spec("a-b")


class TestFindDevicesForBulk:
    async def test_name_wildcard_matches_substring(self) -> None:
        cam1 = await create_camera(name="Front Camera", channel=1)
        cam2 = await create_camera(name="Back Camera", channel=2)
        cam3 = await create_camera(name="Garden Sensor", channel=3)

        result = find_devices_for_bulk([cam1, cam2, cam3], name_pattern="*camera*")
        assert {d.name for d in result} == {"Front Camera", "Back Camera"}

    async def test_name_wildcard_case_insensitive(self) -> None:
        cam = await create_camera(name="Front Camera", channel=1)
        result = find_devices_for_bulk([cam], name_pattern="*CAMERA*")
        assert len(result) == 1

    async def test_name_wildcard_no_match(self) -> None:
        cam = await create_camera(name="Front Camera", channel=1)
        result = find_devices_for_bulk([cam], name_pattern="*garden*")
        assert result == []

    async def test_channel_spec_matches_cameras(self) -> None:
        cam1 = await create_camera(name="Ch1", channel=1)
        cam2 = await create_camera(name="Ch2", channel=2)
        cam3 = await create_camera(name="Ch5", channel=5)

        result = find_devices_for_bulk([cam1, cam2, cam3], channel_spec={1, 2})
        assert {d.channel for d in result} == {1, 2}

    async def test_channel_spec_excludes_power_devices(self) -> None:
        cam = await create_camera(name="Cam", channel=1)
        pwr = await create_power_device(name="Plug")

        result = find_devices_for_bulk([cam, pwr], channel_spec={1})
        assert len(result) == 1
        assert result[0].name == "Cam"

    async def test_both_filters_intersection(self) -> None:
        cam1 = await create_camera(name="Front Camera", channel=1)
        cam2 = await create_camera(name="Front Camera Alt", channel=5)
        cam3 = await create_camera(name="Back Camera", channel=1)

        result = find_devices_for_bulk(
            [cam1, cam2, cam3], name_pattern="front*", channel_spec={1}
        )
        assert len(result) == 1
        assert result[0].name == "Front Camera"

    async def test_no_filters_returns_all(self) -> None:
        cam1 = await create_camera(name="A", channel=1)
        cam2 = await create_camera(name="B", channel=2)

        result = find_devices_for_bulk([cam1, cam2])
        assert len(result) == 2
