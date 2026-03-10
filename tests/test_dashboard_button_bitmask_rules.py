"""Tests for dashboard button per-tag bitmask rule validation and persistence."""

from httpx import AsyncClient

from remander.models.enums import ButtonOperationType, HourBitmaskSubtype
from remander.services.bitmask import create_hour_bitmask
from remander.services.dashboard_button import create_dashboard_button
from remander.services.tag import create_tag
from tests.factories import create_device


async def _make_button(name: str, op_type: ButtonOperationType = ButtonOperationType.AWAY):
    return await create_dashboard_button(name, op_type)


async def _make_bitmask(name: str = "mask"):
    return await create_hour_bitmask(name, HourBitmaskSubtype.STATIC, static_value="1" * 24)


class TestValidateButtonRules:
    async def test_no_rules_all_enabled_devices_are_uncovered(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        cam = await create_device(name="Front Cam", is_enabled=True)
        overlaps, uncovered = await validate_button_rules([])
        assert cam.name in uncovered
        assert overlaps == []

    async def test_disabled_devices_excluded_from_coverage_check(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        await create_device(name="Off Cam", is_enabled=False)
        overlaps, uncovered = await validate_button_rules([])
        assert "Off Cam" not in uncovered

    async def test_tagged_device_not_uncovered(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        cam = await create_device(name="Tagged Cam", is_enabled=True)
        tag = await create_tag("mytag")
        await tag.devices.add(cam)
        bm = await _make_bitmask()
        overlaps, uncovered = await validate_button_rules([(tag.id, bm.id)])
        assert cam.name not in uncovered
        assert overlaps == []

    async def test_overlap_detected_when_device_in_two_tags(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        cam = await create_device(name="Shared Cam", is_enabled=True)
        tag1 = await create_tag("tag-a")
        tag2 = await create_tag("tag-b")
        await tag1.devices.add(cam)
        await tag2.devices.add(cam)
        bm = await _make_bitmask()
        overlaps, uncovered = await validate_button_rules([(tag1.id, bm.id), (tag2.id, bm.id)])
        assert "Shared Cam" in overlaps

    async def test_no_overlap_when_devices_in_different_tags(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        cam1 = await create_device(name="Cam A", is_enabled=True)
        cam2 = await create_device(name="Cam B", is_enabled=True)
        tag1 = await create_tag("tag-a")
        tag2 = await create_tag("tag-b")
        await tag1.devices.add(cam1)
        await tag2.devices.add(cam2)
        bm = await _make_bitmask()
        overlaps, uncovered = await validate_button_rules([(tag1.id, bm.id), (tag2.id, bm.id)])
        assert overlaps == []
        assert uncovered == []

    async def test_uncovered_devices_listed_when_some_tags_missing(self) -> None:
        from remander.services.dashboard_button import validate_button_rules

        cam_covered = await create_device(name="Covered", is_enabled=True)
        await create_device(name="Not Covered", is_enabled=True)
        tag = await create_tag("partial")
        await tag.devices.add(cam_covered)
        bm = await _make_bitmask()
        overlaps, uncovered = await validate_button_rules([(tag.id, bm.id)])
        assert "Not Covered" in uncovered
        assert "Covered" not in uncovered
        assert overlaps == []


class TestSaveButtonRules:
    async def test_save_creates_rule_records(self) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("Test")
        tag = await create_tag("t1")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 1
        assert rules[0].tag_id == tag.id
        assert rules[0].hour_bitmask_id == bm.id

    async def test_save_multiple_rules(self) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("Test")
        tag1 = await create_tag("t1")
        tag2 = await create_tag("t2")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag1.id, bm.id), (tag2.id, bm.id)])
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 2

    async def test_save_replaces_existing_rules(self) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("Test")
        tag1 = await create_tag("t1")
        tag2 = await create_tag("t2")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag1.id, bm.id)])
        await save_button_rules(btn.id, [(tag2.id, bm.id)])
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 1
        assert rules[0].tag_id == tag2.id

    async def test_save_empty_clears_all_rules(self) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("Test")
        tag = await create_tag("t1")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        await save_button_rules(btn.id, [])
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 0

    async def test_rules_cascade_deleted_with_button(self) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule
        from remander.services.dashboard_button import delete_dashboard_button, save_button_rules

        btn = await _make_button("Test")
        tag = await create_tag("t1")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        await delete_dashboard_button(btn.id)
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 0


class TestListRulesForButton:
    async def test_list_returns_saved_rules(self) -> None:
        from remander.services.dashboard_button import list_rules_for_button, save_button_rules

        btn = await _make_button("Test")
        tag = await create_tag("t1")
        bm = await _make_bitmask()
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        rules = await list_rules_for_button(btn.id)
        assert len(rules) == 1
        assert rules[0].tag_id == tag.id

    async def test_list_returns_empty_when_no_rules(self) -> None:
        from remander.services.dashboard_button import list_rules_for_button

        btn = await _make_button("Test")
        rules = await list_rules_for_button(btn.id)
        assert rules == []


class TestButtonCreateRouteWithRules:
    async def test_create_with_rules_redirects(self, client: AsyncClient) -> None:
        tag = await create_tag("my-tag")
        bm = await _make_bitmask("My Mask")
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Test Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_create_without_rules_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Test Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "required" in response.text.lower()

    async def test_create_without_rules_preserves_field_values(self, client: AsyncClient) -> None:
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "My Preserved Name",
                "operation_type": "other",
                "color": "red",
                "delay_seconds": "30",
                "sort_order": "7",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "My Preserved Name" in response.text
        assert 'value="30"' in response.text
        assert 'value="7"' in response.text

    async def test_create_with_overlapping_tags_returns_422_with_device_names(
        self, client: AsyncClient
    ) -> None:
        cam = await create_device(name="Shared Camera", is_enabled=True)
        tag1 = await create_tag("tag-one")
        tag2 = await create_tag("tag-two")
        await tag1.devices.add(cam)
        await tag2.devices.add(cam)
        bm = await _make_bitmask()
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Test Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": [str(tag1.id), str(tag2.id)],
                "rule_bitmask_ids": [str(bm.id), str(bm.id)],
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "Shared Camera" in response.text

    async def test_create_with_overlapping_tags_preserves_field_values(
        self, client: AsyncClient
    ) -> None:
        cam = await create_device(name="Overlap Cam", is_enabled=True)
        tag1 = await create_tag("ov-tag-a")
        tag2 = await create_tag("ov-tag-b")
        await tag1.devices.add(cam)
        await tag2.devices.add(cam)
        bm = await _make_bitmask()
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Overlap Preserved",
                "operation_type": "other",
                "color": "red",
                "delay_seconds": "15",
                "sort_order": "3",
                "rule_tag_ids": [str(tag1.id), str(tag2.id)],
                "rule_bitmask_ids": [str(bm.id), str(bm.id)],
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "Overlap Preserved" in response.text
        assert 'value="15"' in response.text
        assert 'value="3"' in response.text

    async def test_create_with_uncovered_devices_shows_warning(
        self, client: AsyncClient
    ) -> None:
        cam_tagged = await create_device(name="Tagged Cam", is_enabled=True)
        await create_device(name="Uncovered Cam", is_enabled=True)
        tag = await create_tag("partial-tag")
        await tag.devices.add(cam_tagged)
        bm = await _make_bitmask()
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Test Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "Uncovered Cam" in response.text

    async def test_create_warning_preserves_submitted_field_values(
        self, client: AsyncClient
    ) -> None:
        """Field values (name, color, delay, sort) must survive the coverage-warning re-render."""
        cam_tagged = await create_device(name="Tagged Cam", is_enabled=True)
        await create_device(name="Uncovered Cam", is_enabled=True)
        tag = await create_tag("partial-tag-2")
        await tag.devices.add(cam_tagged)
        bm = await _make_bitmask()
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "My Special Button",
                "operation_type": "other",
                "color": "red",
                "delay_seconds": "42",
                "sort_order": "5",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "My Special Button" in response.text
        assert 'value="42"' in response.text
        assert 'value="5"' in response.text

    async def test_create_with_force_save_saves_despite_uncovered(
        self, client: AsyncClient
    ) -> None:
        cam_tagged = await create_device(name="Tagged Cam", is_enabled=True)
        await create_device(name="Uncovered Cam", is_enabled=True)
        tag = await create_tag("partial-tag")
        await tag.devices.add(cam_tagged)
        bm = await _make_bitmask()
        response = await client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Force Save Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestButtonEditRouteWithRules:
    async def test_edit_form_shows_existing_rules(self, client: AsyncClient) -> None:
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("My Button")
        tag = await create_tag("edit-tag")
        bm = await _make_bitmask("Edit Mask")
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        response = await client.get(f"/dashboard-buttons/{btn.id}/edit")
        assert response.status_code == 200
        assert "edit-tag" in response.text
        assert "Edit Mask" in response.text

    async def test_edit_without_rules_returns_422(self, client: AsyncClient) -> None:
        btn = await _make_button("My Button")
        response = await client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "My Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "is_enabled": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_edit_without_rules_preserves_submitted_field_values(
        self, client: AsyncClient
    ) -> None:
        btn = await _make_button("Old Name")
        response = await client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "New Unsaved Name",
                "operation_type": "other",
                "color": "red",
                "delay_seconds": "99",
                "sort_order": "4",
                "is_enabled": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "New Unsaved Name" in response.text
        assert 'value="99"' in response.text
        assert 'value="4"' in response.text

    async def test_edit_with_overlapping_tags_returns_422_with_device_names(
        self, client: AsyncClient
    ) -> None:
        btn = await _make_button("My Button")
        cam = await create_device(name="Overlap Device", is_enabled=True)
        tag1 = await create_tag("e-tag1")
        tag2 = await create_tag("e-tag2")
        await tag1.devices.add(cam)
        await tag2.devices.add(cam)
        bm = await _make_bitmask()
        response = await client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "My Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "is_enabled": "1",
                "rule_tag_ids": [str(tag1.id), str(tag2.id)],
                "rule_bitmask_ids": [str(bm.id), str(bm.id)],
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "Overlap Device" in response.text

    async def test_edit_with_overlapping_tags_preserves_submitted_field_values(
        self, client: AsyncClient
    ) -> None:
        btn = await _make_button("Old Name")
        cam = await create_device(name="Edit Overlap Cam", is_enabled=True)
        tag1 = await create_tag("eo-tag1")
        tag2 = await create_tag("eo-tag2")
        await tag1.devices.add(cam)
        await tag2.devices.add(cam)
        bm = await _make_bitmask()
        response = await client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "Changed Name",
                "operation_type": "other",
                "color": "red",
                "delay_seconds": "55",
                "sort_order": "2",
                "is_enabled": "1",
                "rule_tag_ids": [str(tag1.id), str(tag2.id)],
                "rule_bitmask_ids": [str(bm.id), str(bm.id)],
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "Changed Name" in response.text
        assert 'value="55"' in response.text
        assert 'value="2"' in response.text

    async def test_edit_saves_rules_on_valid_submit(self, client: AsyncClient) -> None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule

        btn = await _make_button("My Button")
        tag = await create_tag("new-tag")
        bm = await _make_bitmask()
        response = await client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "My Button",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "is_enabled": "1",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id=btn.id)
        assert len(rules) == 1
        assert rules[0].tag_id == tag.id
