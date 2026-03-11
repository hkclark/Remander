"""Tests for bitmask routes."""

from httpx import AsyncClient

from remander.models.enums import HourBitmaskSubtype
from remander.services.bitmask import create_hour_bitmask, create_zone_mask


class TestBitmaskList:
    async def test_get_bitmasks_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/bitmasks")
        assert response.status_code == 200
        assert "Bitmasks" in response.text

    async def test_shows_hour_bitmask(self, logged_in_client: AsyncClient) -> None:
        await create_hour_bitmask(
            name="All Day", subtype=HourBitmaskSubtype.STATIC, static_value="1" * 24
        )
        response = await logged_in_client.get("/bitmasks")
        assert "All Day" in response.text

    async def test_shows_zone_mask(self, logged_in_client: AsyncClient) -> None:
        await create_zone_mask(name="Full Zone", mask_value="1" * 4800)
        response = await logged_in_client.get("/bitmasks")
        assert "Full Zone" in response.text


class TestHourBitmaskDetail:
    async def test_get_hour_bitmask_detail(self, logged_in_client: AsyncClient) -> None:
        bm = await create_hour_bitmask(
            name="Night Only", subtype=HourBitmaskSubtype.STATIC, static_value="0" * 8 + "1" * 16
        )
        response = await logged_in_client.get(f"/bitmasks/hour/{bm.id}")
        assert response.status_code == 200
        assert "Night Only" in response.text

    async def test_hour_bitmask_not_found(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/bitmasks/hour/999")
        assert response.status_code == 404


class TestHourBitmaskCreate:
    async def test_get_create_form(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/bitmasks/hour/create")
        assert response.status_code == 200
        assert "form" in response.text.lower()

    async def test_post_create_static(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/bitmasks/hour/create",
            data={
                "name": "Morning",
                "subtype": "static",
                "static_value": "1" * 8 + "0" * 16,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/bitmasks" in response.headers["location"]


class TestHourBitmaskEdit:
    async def test_get_edit_form(self, logged_in_client: AsyncClient) -> None:
        bm = await create_hour_bitmask(
            name="Edit Me", subtype=HourBitmaskSubtype.STATIC, static_value="1" * 24
        )
        response = await logged_in_client.get(f"/bitmasks/hour/{bm.id}/edit")
        assert response.status_code == 200
        assert "Edit Me" in response.text

    async def test_post_edit(self, logged_in_client: AsyncClient) -> None:
        bm = await create_hour_bitmask(
            name="Old Name", subtype=HourBitmaskSubtype.STATIC, static_value="1" * 24
        )
        response = await logged_in_client.post(
            f"/bitmasks/hour/{bm.id}/edit",
            data={
                "name": "New Name",
                "subtype": "static",
                "static_value": "0" * 24,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestHourBitmaskDelete:
    async def test_post_delete(self, logged_in_client: AsyncClient) -> None:
        bm = await create_hour_bitmask(
            name="Delete Me", subtype=HourBitmaskSubtype.STATIC, static_value="1" * 24
        )
        response = await logged_in_client.post(
            f"/bitmasks/hour/{bm.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/bitmasks" in response.headers["location"]


class TestZoneMaskDetail:
    async def test_get_zone_mask_detail(self, logged_in_client: AsyncClient) -> None:
        zm = await create_zone_mask(name="Full Zone", mask_value="1" * 4800)
        response = await logged_in_client.get(f"/bitmasks/zone/{zm.id}")
        assert response.status_code == 200
        assert "Full Zone" in response.text

    async def test_zone_mask_not_found(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/bitmasks/zone/999")
        assert response.status_code == 404


class TestZoneMaskCreate:
    async def test_get_create_form(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/bitmasks/zone/create")
        assert response.status_code == 200

    async def test_post_create(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/bitmasks/zone/create",
            data={"name": "Test Zone", "mask_value": "1" * 4800},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/bitmasks" in response.headers["location"]


class TestZoneMaskDelete:
    async def test_post_delete(self, logged_in_client: AsyncClient) -> None:
        zm = await create_zone_mask(name="Delete Zone", mask_value="0" * 4800)
        response = await logged_in_client.post(
            f"/bitmasks/zone/{zm.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
