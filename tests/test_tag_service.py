"""Tests for the tag service — RED phase (TDD)."""

import pytest

from remander.models.tag import Tag
from remander.services.tag import (
    add_tag_to_device,
    create_tag,
    delete_tag,
    get_devices_by_tag,
    list_dashboard_tags,
    list_tags,
    remove_tag_from_device,
    update_tag,
)
from tests.factories import create_camera


class TestCreateTag:
    async def test_create_tag(self) -> None:
        tag = await create_tag(name="outdoor")
        assert tag.id is not None
        assert tag.name == "outdoor"

    async def test_create_duplicate_tag_fails(self) -> None:
        await create_tag(name="indoor")
        with pytest.raises(Exception):
            await create_tag(name="indoor")


class TestListTags:
    async def test_list_tags_empty(self) -> None:
        tags = await list_tags()
        assert tags == []

    async def test_list_tags_with_device_counts(self) -> None:
        tag1 = await create_tag(name="front-yard")
        tag2 = await create_tag(name="back-yard")

        cam1 = await create_camera(name="Cam 1")
        cam2 = await create_camera(name="Cam 2")

        await tag1.devices.add(cam1, cam2)
        await tag2.devices.add(cam1)

        tags = await list_tags()
        assert len(tags) == 2

        # Verify we get device counts — tags are returned with a device_count annotation
        tag_dict = {t.name: t.device_count for t in tags}
        assert tag_dict["front-yard"] == 2
        assert tag_dict["back-yard"] == 1

    async def test_list_tags_zero_device_count(self) -> None:
        await create_tag(name="empty-tag")
        tags = await list_tags()
        assert len(tags) == 1
        assert tags[0].device_count == 0


class TestDeleteTag:
    async def test_delete_tag(self) -> None:
        tag = await create_tag(name="doomed")
        result = await delete_tag(tag.id)
        assert result is True
        assert await Tag.get_or_none(id=tag.id) is None

    async def test_delete_nonexistent_tag_returns_false(self) -> None:
        result = await delete_tag(99999)
        assert result is False


class TestAddTagToDevice:
    async def test_add_tag_to_device(self) -> None:
        camera = await create_camera(name="Tagged Cam")
        tag = await create_tag(name="outdoor")

        await add_tag_to_device(camera.id, tag.id)

        tags = await camera.tags.all()
        assert len(tags) == 1
        assert tags[0].name == "outdoor"

    async def test_add_tag_twice_is_idempotent(self) -> None:
        camera = await create_camera(name="Double Cam")
        tag = await create_tag(name="front")

        await add_tag_to_device(camera.id, tag.id)
        await add_tag_to_device(camera.id, tag.id)

        tags = await camera.tags.all()
        assert len(tags) == 1


class TestRemoveTagFromDevice:
    async def test_remove_tag_from_device(self) -> None:
        camera = await create_camera(name="Untagged Cam")
        tag = await create_tag(name="removable")
        await camera.tags.add(tag)

        await remove_tag_from_device(camera.id, tag.id)

        tags = await camera.tags.all()
        assert len(tags) == 0

    async def test_remove_nonexistent_tag_is_no_op(self) -> None:
        camera = await create_camera(name="No-op Cam")
        # Should not raise
        await remove_tag_from_device(camera.id, 99999)


class TestShowOnDashboard:
    async def test_default_is_false(self) -> None:
        tag = await create_tag(name="hidden")
        assert tag.show_on_dashboard is False

    async def test_can_create_with_show_on_dashboard(self) -> None:
        tag = await create_tag(name="visible", show_on_dashboard=True)
        assert tag.show_on_dashboard is True


class TestListDashboardTags:
    async def test_returns_only_dashboard_tags(self) -> None:
        await create_tag(name="hidden-tag", show_on_dashboard=False)
        await create_tag(name="visible-tag", show_on_dashboard=True)
        tags = await list_dashboard_tags()
        assert len(tags) == 1
        assert tags[0].name == "visible-tag"

    async def test_empty_when_no_dashboard_tags(self) -> None:
        await create_tag(name="not-on-dash")
        tags = await list_dashboard_tags()
        assert tags == []


class TestUpdateTag:
    async def test_update_tag_name(self) -> None:
        tag = await create_tag(name="old-name")
        updated = await update_tag(tag.id, name="new-name")
        assert updated is not None
        assert updated.name == "new-name"
        refreshed = await Tag.get(id=tag.id)
        assert refreshed.name == "new-name"

    async def test_update_tag_dashboard(self) -> None:
        tag = await create_tag(name="mytag", show_on_dashboard=False)
        updated = await update_tag(tag.id, show_on_dashboard=True)
        assert updated is not None
        assert updated.show_on_dashboard is True

    async def test_update_tag_both_fields(self) -> None:
        tag = await create_tag(name="original")
        updated = await update_tag(tag.id, name="renamed", show_on_dashboard=True)
        assert updated.name == "renamed"
        assert updated.show_on_dashboard is True

    async def test_update_nonexistent_tag_returns_none(self) -> None:
        result = await update_tag(99999, name="nope")
        assert result is None


class TestGetDevicesByTag:
    async def test_get_devices_by_tag(self) -> None:
        cam1 = await create_camera(name="Outdoor 1")
        cam2 = await create_camera(name="Outdoor 2")
        cam3 = await create_camera(name="Indoor 1")

        outdoor = await create_tag(name="outdoor")
        indoor = await create_tag(name="indoor")

        await outdoor.devices.add(cam1, cam2)
        await indoor.devices.add(cam3)

        devices = await get_devices_by_tag("outdoor")
        assert len(devices) == 2
        names = {d.name for d in devices}
        assert names == {"Outdoor 1", "Outdoor 2"}

    async def test_get_devices_by_nonexistent_tag(self) -> None:
        devices = await get_devices_by_tag("no-such-tag")
        assert devices == []
