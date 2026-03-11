"""Tests for tag routes."""

from httpx import AsyncClient

from remander.models.tag import Tag
from tests.factories import create_camera, create_power_device, create_tag


class TestTagColors:
    async def test_create_tag_with_color_stores_color(self, logged_in_client: AsyncClient) -> None:
        await logged_in_client.post(
            "/tags/create",
            data={"name": "colored-tag", "color": "emerald"},
            follow_redirects=False,
        )
        tag = await Tag.get(name="colored-tag")
        assert tag.color == "emerald"

    async def test_create_tag_without_color_is_none(self, logged_in_client: AsyncClient) -> None:
        await logged_in_client.post(
            "/tags/create",
            data={"name": "no-color-tag"},
            follow_redirects=False,
        )
        tag = await Tag.get(name="no-color-tag")
        assert tag.color is None

    async def test_edit_tag_updates_color(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="recolored")
        await logged_in_client.post(
            f"/tags/{tag.id}/edit",
            data={"name": "recolored", "color": "violet"},
            follow_redirects=False,
        )
        updated = await Tag.get(id=tag.id)
        assert updated.color == "violet"

    async def test_tag_list_shows_color_swatch(self, logged_in_client: AsyncClient) -> None:
        await create_tag(name="sky-tag", color="sky")
        response = await logged_in_client.get("/tags")
        assert "sky" in response.text

    async def test_device_list_uses_tag_color(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Color Cam")
        tag = await create_tag(name="rose-tag", color="rose")
        await cam.tags.add(tag)
        response = await logged_in_client.get("/devices")
        # The colored badge class should appear (not just hardcoded blue)
        assert "rose" in response.text


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


class TestBulkPreview:
    async def test_preview_by_name_wildcard(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="outdoor")
        await create_camera(name="Front Camera", channel=1)
        await create_camera(name="Back Camera", channel=2)
        await create_camera(name="Garden Sensor", channel=3)

        response = await logged_in_client.post(
            "/tags/bulk-preview",
            data={"tag_id": str(tag.id), "operation": "tag", "name_pattern": "*camera*", "channel_spec": ""},
        )
        assert response.status_code == 200
        assert "Front Camera" in response.text
        assert "Back Camera" in response.text
        assert "Garden Sensor" not in response.text

    async def test_preview_by_channel_spec(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="patio")
        await create_camera(name="Ch1", channel=1)
        await create_camera(name="Ch2", channel=2)
        await create_camera(name="Ch5", channel=5)

        response = await logged_in_client.post(
            "/tags/bulk-preview",
            data={"tag_id": str(tag.id), "operation": "tag", "name_pattern": "", "channel_spec": "1-2"},
        )
        assert response.status_code == 200
        assert "Ch1" in response.text
        assert "Ch2" in response.text
        assert "Ch5" not in response.text

    async def test_preview_no_matches_shows_message(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="empty")
        await create_camera(name="Front Camera", channel=1)

        response = await logged_in_client.post(
            "/tags/bulk-preview",
            data={"tag_id": str(tag.id), "operation": "tag", "name_pattern": "*garden*", "channel_spec": ""},
        )
        assert response.status_code == 200
        assert "No devices matched" in response.text

    async def test_preview_shows_channel_note(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="note-test")
        response = await logged_in_client.post(
            "/tags/bulk-preview",
            data={"tag_id": str(tag.id), "operation": "tag", "name_pattern": "", "channel_spec": "1"},
        )
        assert response.status_code == 200
        assert "camera" in response.text.lower()

    async def test_preview_invalid_channel_spec_returns_error(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="bad-spec")
        response = await logged_in_client.post(
            "/tags/bulk-preview",
            data={"tag_id": str(tag.id), "operation": "tag", "name_pattern": "", "channel_spec": "abc"},
        )
        assert response.status_code == 200
        assert "Invalid" in response.text


class TestBulkApply:
    async def test_tag_operation_applies_tag_to_devices(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="security")
        cam1 = await create_camera(name="Cam A", channel=1)
        cam2 = await create_camera(name="Cam B", channel=2)

        response = await logged_in_client.post(
            "/tags/bulk-apply",
            data={"tag_id": str(tag.id), "operation": "tag", "device_ids": [str(cam1.id), str(cam2.id)]},
        )
        assert response.status_code == 200
        assert "2" in response.text  # count in toast

        await cam1.fetch_related("tags")
        await cam2.fetch_related("tags")
        assert any(t.id == tag.id for t in cam1.tags)
        assert any(t.id == tag.id for t in cam2.tags)

    async def test_untag_operation_removes_tag_from_devices(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="indoor")
        cam = await create_camera(name="Cam C", channel=3)
        await cam.tags.add(tag)

        response = await logged_in_client.post(
            "/tags/bulk-apply",
            data={"tag_id": str(tag.id), "operation": "untag", "device_ids": [str(cam.id)]},
        )
        assert response.status_code == 200
        assert "1" in response.text

        await cam.fetch_related("tags")
        assert not any(t.id == tag.id for t in cam.tags)

    async def test_zero_devices_shows_zero_in_toast(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag(name="empty-apply")

        response = await logged_in_client.post(
            "/tags/bulk-apply",
            data={"tag_id": str(tag.id), "operation": "tag", "device_ids": []},
        )
        assert response.status_code == 200
        assert "0" in response.text
