"""Tests for tag routes."""

from httpx import AsyncClient

from tests.factories import create_camera, create_tag


class TestTagList:
    async def test_get_tags_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/tags")
        assert response.status_code == 200
        assert "Tags" in response.text

    async def test_shows_tag_with_device_count(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="outdoor")
        cam = await create_camera(name="Front Cam")
        await cam.tags.add(tag)
        response = await logged_in_client.get("/tags")
        assert "outdoor" in response.text


class TestTagCreate:
    async def test_post_create_tag(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/tags/create",
            data={"name": "indoor"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/tags" in response.headers["location"]


class TestTagDelete:
    async def test_post_delete_tag(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="delete-me")
        response = await logged_in_client.post(
            f"/tags/{tag.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/tags" in response.headers["location"]


class TestTagEdit:
    async def test_get_edit_form(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="editable")
        response = await logged_in_client.get(f"/tags/{tag.id}/edit")
        assert response.status_code == 200
        assert "editable" in response.text
        assert "Edit Tag" in response.text

    async def test_get_edit_nonexistent_returns_404(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/tags/99999/edit")
        assert response.status_code == 404

    async def test_post_edit_tag(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="before")
        response = await logged_in_client.post(
            f"/tags/{tag.id}/edit",
            data={"name": "after", "show_on_dashboard": "on"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/tags" in response.headers["location"]

    async def test_post_edit_updates_values(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="old")
        await logged_in_client.post(
            f"/tags/{tag.id}/edit",
            data={"name": "new"},
            follow_redirects=False,
        )
        from remander.models.tag import Tag

        updated = await Tag.get(id=tag.id)
        assert updated.name == "new"
        assert updated.show_on_dashboard is False

    async def test_post_edit_nonexistent_returns_404(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/tags/99999/edit",
            data={"name": "nope"},
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestDeviceTagManagement:
    async def test_add_tag_to_device(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Tag Target")
        tag = await create_tag(name="patio")
        response = await logged_in_client.post(
            f"/devices/{cam.id}/tags/add",
            data={"tag_id": str(tag.id)},
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_remove_tag_from_device(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Untag Target")
        tag = await create_tag(name="garage")
        await cam.tags.add(tag)
        response = await logged_in_client.post(
            f"/devices/{cam.id}/tags/{tag.id}/remove",
            follow_redirects=False,
        )
        assert response.status_code == 303
