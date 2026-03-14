"""Tests for ingress/egress notification mute — DashboardButton mute fields and service layer."""

import pytest

from remander.models.enums import ButtonOperationType
from remander.services.dashboard_button import (
    create_dashboard_button,
    get_mute_device_ids_for_button,
    list_mute_tags_for_button,
    save_button_mute_tags,
    update_dashboard_button,
)
from tests.factories import create_camera, create_tag


class TestDashboardButtonMuteDefaults:
    async def test_mute_disabled_by_default(self) -> None:
        btn = await create_dashboard_button("Go Away", ButtonOperationType.AWAY)
        assert btn.mute_notifications_enabled is False

    async def test_mute_duration_defaults_to_180(self) -> None:
        btn = await create_dashboard_button("Go Away", ButtonOperationType.AWAY)
        assert btn.mute_duration_seconds == 180

    async def test_create_with_mute_enabled(self) -> None:
        btn = await create_dashboard_button(
            "Quiet Away",
            ButtonOperationType.AWAY,
            mute_notifications_enabled=True,
            mute_duration_seconds=90,
        )
        assert btn.mute_notifications_enabled is True
        assert btn.mute_duration_seconds == 90

    async def test_update_enables_mute(self) -> None:
        btn = await create_dashboard_button("Home", ButtonOperationType.HOME)
        assert btn.mute_notifications_enabled is False

        updated = await update_dashboard_button(btn.id, mute_notifications_enabled=True, mute_duration_seconds=120)
        assert updated.mute_notifications_enabled is True
        assert updated.mute_duration_seconds == 120


class TestDashboardButtonMuteTagModel:
    async def test_save_and_list_mute_tags(self) -> None:
        btn = await create_dashboard_button("Mute Away", ButtonOperationType.AWAY)
        tag1 = await create_tag(name="indoor")
        tag2 = await create_tag(name="outdoor")

        await save_button_mute_tags(btn.id, [tag1.id, tag2.id])

        tags = await list_mute_tags_for_button(btn.id)
        tag_ids = {t.id for t in tags}
        assert tag_ids == {tag1.id, tag2.id}

    async def test_save_replaces_existing_mute_tags(self) -> None:
        btn = await create_dashboard_button("Mute Home", ButtonOperationType.HOME)
        tag1 = await create_tag(name="front")
        tag2 = await create_tag(name="back")

        await save_button_mute_tags(btn.id, [tag1.id, tag2.id])
        await save_button_mute_tags(btn.id, [tag2.id])  # replace with only tag2

        tags = await list_mute_tags_for_button(btn.id)
        assert len(tags) == 1
        assert tags[0].id == tag2.id

    async def test_save_empty_list_clears_mute_tags(self) -> None:
        btn = await create_dashboard_button("Mute Clear", ButtonOperationType.AWAY)
        tag = await create_tag(name="clear-me")

        await save_button_mute_tags(btn.id, [tag.id])
        await save_button_mute_tags(btn.id, [])

        tags = await list_mute_tags_for_button(btn.id)
        assert tags == []

    async def test_duplicate_tag_raises_or_deduplicates(self) -> None:
        """Saving the same tag twice must not create duplicate rows."""
        btn = await create_dashboard_button("Dedup Mute", ButtonOperationType.AWAY)
        tag = await create_tag(name="dup-tag")

        await save_button_mute_tags(btn.id, [tag.id, tag.id])

        tags = await list_mute_tags_for_button(btn.id)
        assert len(tags) == 1


class TestGetMuteDeviceIds:
    async def test_returns_device_ids_for_mute_tags(self) -> None:
        btn = await create_dashboard_button("Mute Devices", ButtonOperationType.AWAY)
        tag = await create_tag(name="mute-cam-group")
        cam1 = await create_camera(name="Mute Cam 1", channel=0)
        cam2 = await create_camera(name="Mute Cam 2", channel=1)
        await tag.devices.add(cam1, cam2)

        await save_button_mute_tags(btn.id, [tag.id])

        device_ids = await get_mute_device_ids_for_button(btn.id, {cam1.id, cam2.id})
        assert set(device_ids) == {cam1.id, cam2.id}

    async def test_filters_to_enabled_device_ids_only(self) -> None:
        """Devices not in the enabled_device_ids set are excluded."""
        btn = await create_dashboard_button("Filter Mute", ButtonOperationType.AWAY)
        tag = await create_tag(name="filter-group")
        cam1 = await create_camera(name="Enabled Cam", channel=0)
        cam2 = await create_camera(name="Excluded Cam", channel=1)
        await tag.devices.add(cam1, cam2)

        await save_button_mute_tags(btn.id, [tag.id])

        # Only cam1 is in the enabled set
        device_ids = await get_mute_device_ids_for_button(btn.id, {cam1.id})
        assert set(device_ids) == {cam1.id}
        assert cam2.id not in device_ids

    async def test_returns_empty_when_no_mute_tags(self) -> None:
        btn = await create_dashboard_button("No Mute Tags", ButtonOperationType.AWAY)
        cam = await create_camera(name="Any Cam", channel=0)

        device_ids = await get_mute_device_ids_for_button(btn.id, {cam.id})
        assert device_ids == []
