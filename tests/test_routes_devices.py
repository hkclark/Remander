"""Tests for device routes."""

from httpx import AsyncClient

from remander.models.enums import DeviceBrand
from tests.factories import create_camera


class TestDeviceList:
    async def test_get_devices_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/devices")
        assert response.status_code == 200
        assert "Devices" in response.text

    async def test_shows_device_in_list(self, client: AsyncClient) -> None:
        await create_camera(name="Front Door Cam", channel=1)
        response = await client.get("/devices")
        assert "Front Door Cam" in response.text

    async def test_shows_device_type_and_brand(self, client: AsyncClient) -> None:
        await create_camera(name="Side Cam", brand=DeviceBrand.REOLINK)
        response = await client.get("/devices")
        assert "camera" in response.text.lower()
        assert "reolink" in response.text.lower()

    async def test_shows_enabled_status(self, client: AsyncClient) -> None:
        await create_camera(name="Enabled Cam", is_enabled=True)
        await create_camera(name="Disabled Cam", is_enabled=False)
        response = await client.get("/devices")
        assert response.status_code == 200


class TestDeviceDetail:
    async def test_get_device_detail(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Garage Cam", channel=3)
        response = await client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "Garage Cam" in response.text

    async def test_device_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/devices/999")
        assert response.status_code == 404


class TestDeviceCreate:
    async def test_get_create_form(self, client: AsyncClient) -> None:
        response = await client.get("/devices/create")
        assert response.status_code == 200
        assert "form" in response.text.lower()

    async def test_post_create_device(self, client: AsyncClient) -> None:
        response = await client.post(
            "/devices/create",
            data={
                "name": "New Camera",
                "device_type": "camera",
                "brand": "reolink",
                "channel": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/devices" in response.headers["location"]


class TestDeviceEdit:
    async def test_get_edit_form(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Edit Me")
        response = await client.get(f"/devices/{cam.id}/edit")
        assert response.status_code == 200
        assert "Edit Me" in response.text

    async def test_post_edit_device(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Old Name")
        response = await client.post(
            f"/devices/{cam.id}/edit",
            data={
                "name": "New Name",
                "device_type": "camera",
                "brand": "reolink",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestDeviceDelete:
    async def test_post_delete_device(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Delete Me")
        response = await client.post(
            f"/devices/{cam.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/devices" in response.headers["location"]
