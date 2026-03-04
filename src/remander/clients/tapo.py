"""Tapo smart plug client — wraps python-kasa for power control."""

import attrs
from kasa import Device


@attrs.define
class TapoClient:
    """Async client for Tapo smart plugs via python-kasa.

    Each operation connects to the device, performs the action, and disconnects.
    This avoids holding long-lived connections to power devices.
    """

    async def turn_on(self, ip_address: str) -> None:
        """Power on the smart plug at the given IP address."""
        device = await Device.connect(host=ip_address)
        try:
            await device.turn_on()
        finally:
            await device.disconnect()

    async def turn_off(self, ip_address: str) -> None:
        """Power off the smart plug at the given IP address."""
        device = await Device.connect(host=ip_address)
        try:
            await device.turn_off()
        finally:
            await device.disconnect()

    async def is_on(self, ip_address: str) -> bool:
        """Check if the smart plug is currently powered on."""
        device = await Device.connect(host=ip_address)
        try:
            await device.update()
            return device.is_on
        finally:
            await device.disconnect()
