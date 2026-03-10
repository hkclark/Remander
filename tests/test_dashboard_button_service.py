"""Tests for the DashboardButton service layer."""

from remander.models.enums import ButtonColor, ButtonOperationType
from remander.services.dashboard_button import (
    create_dashboard_button,
    delete_dashboard_button,
    get_dashboard_button,
    list_dashboard_buttons,
    update_dashboard_button,
)


class TestCreateDashboardButton:
    async def test_create_returns_button(self) -> None:
        btn = await create_dashboard_button("Set Away", ButtonOperationType.AWAY)
        assert btn.id is not None
        assert btn.name == "Set Away"
        assert btn.operation_type == ButtonOperationType.AWAY

    async def test_defaults(self) -> None:
        btn = await create_dashboard_button("Home", ButtonOperationType.HOME)
        assert btn.color == ButtonColor.BLUE
        assert btn.delay_seconds == 0
        assert btn.sort_order == 0
        assert btn.is_enabled is True

    async def test_custom_fields(self) -> None:
        btn = await create_dashboard_button(
            "Red Away",
            ButtonOperationType.AWAY,
            color=ButtonColor.RED,
            delay_seconds=30,
            sort_order=5,
        )
        assert btn.color == ButtonColor.RED
        assert btn.delay_seconds == 30
        assert btn.sort_order == 5


class TestGetDashboardButton:
    async def test_get_existing(self) -> None:
        created = await create_dashboard_button("Btn", ButtonOperationType.HOME)
        fetched = await get_dashboard_button(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_missing_returns_none(self) -> None:
        result = await get_dashboard_button(9999)
        assert result is None


class TestListDashboardButtons:
    async def test_ordered_by_sort_order(self) -> None:
        await create_dashboard_button("B", ButtonOperationType.AWAY, sort_order=2)
        await create_dashboard_button("A", ButtonOperationType.HOME, sort_order=1)
        buttons = await list_dashboard_buttons()
        assert [b.name for b in buttons] == ["A", "B"]

    async def test_enabled_only_excludes_disabled(self) -> None:
        await create_dashboard_button("Active", ButtonOperationType.AWAY, is_enabled=True)
        await create_dashboard_button("Inactive", ButtonOperationType.HOME, is_enabled=False)
        buttons = await list_dashboard_buttons(enabled_only=True)
        names = [b.name for b in buttons]
        assert "Active" in names
        assert "Inactive" not in names

    async def test_all_includes_disabled(self) -> None:
        await create_dashboard_button("Active", ButtonOperationType.AWAY, is_enabled=True)
        await create_dashboard_button("Inactive", ButtonOperationType.HOME, is_enabled=False)
        buttons = await list_dashboard_buttons()
        assert len(buttons) == 2


class TestUpdateDashboardButton:
    async def test_update_name(self) -> None:
        btn = await create_dashboard_button("Old", ButtonOperationType.AWAY)
        updated = await update_dashboard_button(btn.id, name="New")
        assert updated is not None
        assert updated.name == "New"

    async def test_update_missing_returns_none(self) -> None:
        result = await update_dashboard_button(9999, name="X")
        assert result is None


class TestDeleteDashboardButton:
    async def test_delete_existing(self) -> None:
        btn = await create_dashboard_button("Delete Me", ButtonOperationType.AWAY)
        deleted = await delete_dashboard_button(btn.id)
        assert deleted is True
        assert await get_dashboard_button(btn.id) is None

    async def test_delete_missing_returns_false(self) -> None:
        result = await delete_dashboard_button(9999)
        assert result is False
