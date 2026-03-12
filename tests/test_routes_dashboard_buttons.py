"""Tests for dashboard button CRUD routes and button execution."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.enums import ButtonOperationType, CommandType
from remander.models.command import Command
from remander.services.bitmask import create_hour_bitmask
from remander.services.dashboard_button import create_dashboard_button, save_button_rules
from remander.models.enums import HourBitmaskSubtype
from remander.services.tag import create_tag
from tests.factories import create_device


async def _make_button(name: str, op_type: ButtonOperationType, **kwargs):
    """Helper: create a button (no rules needed for most tests)."""
    return await create_dashboard_button(name, op_type, **kwargs)


async def _make_button_with_rule(name: str, op_type: ButtonOperationType, **kwargs):
    """Helper: create a button with one tag-bitmask rule (covers all devices)."""
    bm = await create_hour_bitmask(name, HourBitmaskSubtype.STATIC, static_value="1" * 24)
    tag = await create_tag(f"tag-{name.lower().replace(' ', '-')}")
    btn = await create_dashboard_button(name, op_type, **kwargs)
    await save_button_rules(btn.id, [(tag.id, bm.id)])
    return btn, tag, bm


class TestButtonList:
    async def test_get_list_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons")
        assert response.status_code == 200

    async def test_shows_button_in_list(self, logged_in_client: AsyncClient) -> None:
        await _make_button("Go Away", ButtonOperationType.AWAY)
        response = await logged_in_client.get("/dashboard-buttons")
        assert "Go Away" in response.text

    async def test_shows_empty_message_when_no_buttons(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons")
        assert "No buttons configured" in response.text


class TestButtonCreate:
    async def test_get_create_form_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/create")
        assert response.status_code == 200
        assert "form" in response.text.lower()

    async def test_create_form_shows_operation_types(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/create")
        assert "away" in response.text.lower()
        assert "home" in response.text.lower()
        assert "other" in response.text.lower()

    async def test_create_form_shows_color_options(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/create")
        # Color picker renders hex swatches
        assert "#3B82F6" in response.text  # blue
        assert "#EF4444" in response.text  # red

    async def test_post_create_redirects(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag("away-tag")
        bm = await create_hour_bitmask("Away Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        response = await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Set Away",
                "operation_type": "away",
                "color": "#EF4444",
                "delay_seconds": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "sort_order": "0",
                "force_save": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/dashboard-buttons" in response.headers["location"]

    async def test_post_create_without_rules_returns_422(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Set Away",
                "operation_type": "away",
                "color": "#EF4444",
                "delay_seconds": "0",
                "sort_order": "0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "required" in response.text.lower()

    async def test_post_create_stores_delay_seconds(self, logged_in_client: AsyncClient) -> None:
        tag = await create_tag("delay-tag")
        bm = await create_hour_bitmask("Delay Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Delayed Away",
                "operation_type": "away",
                "color": "#EF4444",
                "delay_seconds": "45",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "sort_order": "0",
                "force_save": "1",
            },
            follow_redirects=True,
        )
        response = await logged_in_client.get("/dashboard-buttons")
        assert "45" in response.text


class TestButtonEdit:
    async def test_get_edit_form_returns_200(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("Edit Me", ButtonOperationType.HOME)
        response = await logged_in_client.get(f"/dashboard-buttons/{btn.id}/edit")
        assert response.status_code == 200
        assert "Edit Me" in response.text

    async def test_get_edit_form_404_for_missing(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/9999/edit")
        assert response.status_code == 404

    async def test_post_edit_updates_name(self, logged_in_client: AsyncClient) -> None:
        btn, tag, bm = await _make_button_with_rule("Old Name", ButtonOperationType.AWAY)
        response = await logged_in_client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "New Name",
                "operation_type": "away",
                "color": "#3B82F6",
                "delay_seconds": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "sort_order": "0",
                "is_enabled": "1",
                "force_save": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        await btn.refresh_from_db()
        assert btn.name == "New Name"

    async def test_post_edit_without_rules_returns_422(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("No Rules", ButtonOperationType.AWAY)
        response = await logged_in_client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "No Rules",
                "operation_type": "away",
                "color": "#3B82F6",
                "delay_seconds": "0",
                "sort_order": "0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_post_edit_can_disable(self, logged_in_client: AsyncClient) -> None:
        btn, tag, bm = await _make_button_with_rule("Active", ButtonOperationType.AWAY, is_enabled=True)
        await logged_in_client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "Active",
                "operation_type": "away",
                "color": "#3B82F6",
                "delay_seconds": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "sort_order": "0",
                # is_enabled omitted → unchecked checkbox
                "force_save": "1",
            },
            follow_redirects=False,
        )
        await btn.refresh_from_db()
        assert btn.is_enabled is False


class TestButtonDelete:
    async def test_post_delete_redirects(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("Delete Me", ButtonOperationType.HOME)
        response = await logged_in_client.post(
            f"/dashboard-buttons/{btn.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_post_delete_removes_button(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("Gone", ButtonOperationType.AWAY)
        await logged_in_client.post(f"/dashboard-buttons/{btn.id}/delete", follow_redirects=False)
        response = await logged_in_client.get("/dashboard-buttons")
        assert "Gone" not in response.text


class TestExecuteButton:
    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_execute_away_button(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Away", ButtonOperationType.AWAY)
        response = await logged_in_client.post(
            f"/commands/execute/button/{btn.id}", follow_redirects=False
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_execute_home_button(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Home", ButtonOperationType.HOME)
        response = await logged_in_client.post(
            f"/commands/execute/button/{btn.id}", follow_redirects=False
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_execute_other_button(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Custom", ButtonOperationType.OTHER)
        response = await logged_in_client.post(
            f"/commands/execute/button/{btn.id}", follow_redirects=False
        )
        assert response.status_code == 303
        mock_enqueue.assert_called_once()

    async def test_execute_missing_button_returns_404(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/commands/execute/button/9999", follow_redirects=False
        )
        assert response.status_code == 404

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_away_button_creates_set_away_now_command(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Away", ButtonOperationType.AWAY)
        await logged_in_client.post(f"/commands/execute/button/{btn.id}", follow_redirects=False)
        cmd = await Command.filter(command_type=CommandType.SET_AWAY_NOW).first()
        assert cmd is not None
        assert cmd.dashboard_button_id == btn.id

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_other_button_creates_apply_bitmask_command(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Custom", ButtonOperationType.OTHER)
        await logged_in_client.post(f"/commands/execute/button/{btn.id}", follow_redirects=False)
        cmd = await Command.filter(command_type=CommandType.APPLY_BITMASK).first()
        assert cmd is not None

    @patch("remander.routes.commands.enqueue_command", new_callable=AsyncMock)
    async def test_button_with_delay_stores_delay_seconds(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button(
            "Delayed", ButtonOperationType.AWAY, delay_seconds=30
        )
        await logged_in_client.post(f"/commands/execute/button/{btn.id}", follow_redirects=False)
        cmd = await Command.filter(dashboard_button_id=btn.id).first()
        assert cmd is not None
        assert cmd.delay_seconds == 30


class TestDashboardShowsButtons:
    async def test_dashboard_shows_configured_buttons(self, logged_in_client: AsyncClient) -> None:
        await _make_button("My Away Button", ButtonOperationType.AWAY)
        response = await logged_in_client.get("/")
        assert "My Away Button" in response.text

    async def test_dashboard_excludes_disabled_buttons(self, logged_in_client: AsyncClient) -> None:
        await _make_button("Invisible", ButtonOperationType.AWAY, is_enabled=False)
        response = await logged_in_client.get("/")
        assert "Invisible" not in response.text

    async def test_dashboard_shows_empty_message_with_no_buttons(
        self, logged_in_client: AsyncClient
    ) -> None:
        response = await logged_in_client.get("/")
        assert "No dashboard buttons configured" in response.text
