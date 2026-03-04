"""Tests for the Sonoff Mini R2 client — RED phase (TDD).

All tests mock httpx so no real hardware is needed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from remander.clients.sonoff import SonoffClient


@pytest.fixture
def sonoff_client() -> SonoffClient:
    return SonoffClient()


class TestTurnOn:
    async def test_turn_on(self, sonoff_client: SonoffClient) -> None:
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("remander.clients.sonoff.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await sonoff_client.turn_on("192.168.1.201")

            mock_client.post.assert_awaited_once()
            call_args = mock_client.post.call_args
            assert "zeroconf/switch" in call_args[0][0]
            assert call_args[1]["json"]["data"]["switch"] == "on"


class TestTurnOff:
    async def test_turn_off(self, sonoff_client: SonoffClient) -> None:
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("remander.clients.sonoff.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await sonoff_client.turn_off("192.168.1.201")

            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["data"]["switch"] == "off"


class TestIsOn:
    async def test_is_on_true(self, sonoff_client: SonoffClient) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {"data": {"switch": "on"}}

        with patch("remander.clients.sonoff.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await sonoff_client.is_on("192.168.1.201")
            assert result is True

    async def test_is_on_false(self, sonoff_client: SonoffClient) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {"data": {"switch": "off"}}

        with patch("remander.clients.sonoff.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await sonoff_client.is_on("192.168.1.201")
            assert result is False
