"""Sonoff Mini R2 client — direct HTTP API for power control."""

import attrs
import httpx


@attrs.define
class SonoffClient:
    """Async client for Sonoff Mini R2 switches via their local HTTP API (DIY mode).

    The Sonoff Mini R2 exposes a simple JSON API on port 8081 when in DIY mode.
    """

    async def turn_on(self, ip_address: str) -> None:
        """Power on the switch at the given IP address."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{ip_address}:8081/zeroconf/switch",
                json={"data": {"switch": "on"}},
            )
            response.raise_for_status()

    async def turn_off(self, ip_address: str) -> None:
        """Power off the switch at the given IP address."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{ip_address}:8081/zeroconf/switch",
                json={"data": {"switch": "off"}},
            )
            response.raise_for_status()

    async def is_on(self, ip_address: str) -> bool:
        """Check if the switch is currently on by querying device info."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{ip_address}:8081/zeroconf/info",
                json={"data": {}},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]["switch"] == "on"
