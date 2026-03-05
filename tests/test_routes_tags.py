"""Tests for tag routes."""

from httpx import AsyncClient

from tests.factories import create_camera, create_tag


class TestTagList:
    async def test_get_tags_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/tags")
        assert response.status_code == 200
        assert "Tags" in response.text

    async def test_shows_tag_with_device_count(self, client: AsyncClient) -> None:
        tag = await create_tag(name="outdoor")
        cam = await create_camera(name="Front Cam")
        await cam.tags.add(tag)
        response = await client.get("/tags")
        assert "outdoor" in response.text


class TestTagCreate:
    async def test_post_create_tag(self, client: AsyncClient) -> None:
        response = await client.post(
            "/tags/create",
            data={"name": "indoor"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/tags" in response.headers["location"]


class TestTagDelete:
    async def test_post_delete_tag(self, client: AsyncClient) -> None:
        tag = await create_tag(name="delete-me")
        response = await client.post(
            f"/tags/{tag.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/tags" in response.headers["location"]


class TestDeviceTagManagement:
    async def test_add_tag_to_device(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Tag Target")
        tag = await create_tag(name="patio")
        response = await client.post(
            f"/devices/{cam.id}/tags/add",
            data={"tag_id": str(tag.id)},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_remove_tag_from_device(self, client: AsyncClient) -> None:
        cam = await create_camera(name="Untag Target")
        tag = await create_tag(name="garage")
        await cam.tags.add(tag)
        response = await client.post(
            f"/devices/{cam.id}/tags/{tag.id}/remove",
            follow_redirects=False,
        )
        assert response.status_code == 303
