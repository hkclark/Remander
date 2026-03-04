"""Tests for the Tapo power client — RED phase (TDD).

All tests mock the python-kasa Device so no real hardware is needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from remander.clients.tapo import TapoClient


@pytest.fixture
def mock_device() -> MagicMock:
    """Create a mock kasa Device."""
    device = MagicMock()
    device.turn_on = AsyncMock()
    device.turn_off = AsyncMock()
    device.update = AsyncMock()
    device.disconnect = AsyncMock()
    device.is_on = True
    return device


@pytest.fixture
def tapo_client() -> TapoClient:
    return TapoClient()


class TestTurnOn:
    async def test_turn_on(self, tapo_client: TapoClient, mock_device: MagicMock) -> None:
        with patch("remander.clients.tapo.Device.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_device
            await tapo_client.turn_on("192.168.1.200")
            mock_device.turn_on.assert_awaited_once()
            mock_device.disconnect.assert_awaited_once()


class TestTurnOff:
    async def test_turn_off(self, tapo_client: TapoClient, mock_device: MagicMock) -> None:
        with patch("remander.clients.tapo.Device.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_device
            await tapo_client.turn_off("192.168.1.200")
            mock_device.turn_off.assert_awaited_once()
            mock_device.disconnect.assert_awaited_once()


class TestIsOn:
    async def test_is_on_true(self, tapo_client: TapoClient, mock_device: MagicMock) -> None:
        mock_device.is_on = True
        with patch("remander.clients.tapo.Device.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_device
            result = await tapo_client.is_on("192.168.1.200")
            assert result is True
            mock_device.update.assert_awaited_once()
            mock_device.disconnect.assert_awaited_once()

    async def test_is_on_false(self, tapo_client: TapoClient, mock_device: MagicMock) -> None:
        mock_device.is_on = False
        with patch("remander.clients.tapo.Device.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_device
            result = await tapo_client.is_on("192.168.1.200")
            assert result is False
