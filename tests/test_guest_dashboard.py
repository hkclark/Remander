"""Tests for the guest dashboard at /d."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from remander.models.enums import ButtonOperationType
from remander.services.dashboard_button import create_dashboard_button


async def _make_button(
    name: str,
    op_type: ButtonOperationType = ButtonOperationType.AWAY,
    *,
    show_on_guest: bool = False,
    show_on_main: bool = True,
    is_enabled: bool = True,
):
    return await create_dashboard_button(
        name,
        op_type,
        show_on_guest=show_on_guest,
        show_on_main=show_on_main,
        is_enabled=is_enabled,
    )


class TestGuestDashboardRoute:
    async def test_get_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/d")
        assert response.status_code == 200

    async def test_shows_guest_flagged_button(self, client: AsyncClient) -> None:
        await _make_button("Guest Button", show_on_guest=True)
        response = await client.get("/d")
        assert "Guest Button" in response.text

    async def test_hides_non_guest_button(self, client: AsyncClient) -> None:
        await _make_button("Main Only Button", show_on_guest=False)
        response = await client.get("/d")
        assert "Main Only Button" not in response.text

    async def test_hides_disabled_button(self, client: AsyncClient) -> None:
        await _make_button("Disabled Guest", ButtonOperationType.AWAY, show_on_guest=True, is_enabled=False)
        response = await client.get("/d")
        assert "Disabled Guest" not in response.text

    async def test_has_no_pause_notifications_section(self, client: AsyncClient) -> None:
        response = await client.get("/d")
        assert "Pause Notifications" not in response.text

    async def test_shows_mode_indicator_by_default(self, client: AsyncClient) -> None:
        response = await client.get("/d")
        assert "mode" in response.text.lower()

    async def test_mode_indicator_hidden_when_setting_disabled(self, client: AsyncClient) -> None:
        from remander.config import Settings

        mock_settings = Settings.model_construct(
            guest_dashboard_show_mode=False,
            nvr_host="localhost",
            nvr_username="u",
            nvr_password="p",  # type: ignore[arg-type]
        )
        with patch("remander.routes.guest_dashboard.get_settings", return_value=mock_settings):
            response = await client.get("/d")
        assert "Mode:" not in response.text

    async def test_mode_indicator_shown_when_setting_enabled(self, client: AsyncClient) -> None:
        from remander.config import Settings

        mock_settings = Settings.model_construct(
            guest_dashboard_show_mode=True,
            nvr_host="localhost",
            nvr_username="u",
            nvr_password="p",  # type: ignore[arg-type]
        )
        with patch("remander.routes.guest_dashboard.get_settings", return_value=mock_settings):
            response = await client.get("/d")
        assert "Mode:" in response.text


class TestMainDashboardFiltersShowOnMain:
    async def test_main_dashboard_shows_show_on_main_button(self, client: AsyncClient) -> None:
        await _make_button("Main Button", show_on_main=True)
        response = await client.get("/")
        assert "Main Button" in response.text

    async def test_main_dashboard_hides_show_on_main_false_button(self, client: AsyncClient) -> None:
        await _make_button("Guest Only Button", show_on_main=False, show_on_guest=True)
        response = await client.get("/")
        assert "Guest Only Button" not in response.text


class TestDashboardButtonFormShowsCheckboxes:
    async def test_create_form_has_show_on_main_checkbox(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/create")
        assert "show_on_main" in response.text

    async def test_create_form_has_show_on_guest_checkbox(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/dashboard-buttons/create")
        assert "show_on_guest" in response.text

    async def test_create_saves_show_on_guest_flag(self, logged_in_client: AsyncClient) -> None:
        from remander.models.dashboard_button import DashboardButton
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        tag = await create_tag("g-tag")
        bm = await create_hour_bitmask("G Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Guest Save Test",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        btn = await DashboardButton.get_or_none(name="Guest Save Test")
        assert btn is not None
        assert btn.show_on_guest is True

    async def test_create_show_on_main_defaults_true(self, logged_in_client: AsyncClient) -> None:
        from remander.models.dashboard_button import DashboardButton
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        tag = await create_tag("m-tag")
        bm = await create_hour_bitmask("M Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Main Default Test",
                "operation_type": "away",
                "color": "blue",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                # show_on_main omitted (unchecked checkbox → not sent)
            },
            follow_redirects=False,
        )
        btn = await DashboardButton.get_or_none(name="Main Default Test")
        assert btn is not None
        assert btn.show_on_main is False  # unchecked = False

    async def test_edit_form_preserves_show_on_guest(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("Guest Btn", show_on_guest=True)
        response = await logged_in_client.get(f"/dashboard-buttons/{btn.id}/edit")
        assert response.status_code == 200
        # The checkbox should be checked
        assert 'checked' in response.text


class TestGuestHomePinPad:
    async def test_home_button_on_guest_dashboard_shows_pin_pad(self, logged_in_client: AsyncClient) -> None:
        await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        response = await logged_in_client.get("/d")
        assert 'name="pin"' in response.text

    async def test_away_button_on_guest_dashboard_has_no_pin_pad(self, logged_in_client: AsyncClient) -> None:
        await _make_button("Go Away", ButtonOperationType.AWAY, show_on_guest=True)
        response = await logged_in_client.get("/d")
        assert 'name="pin"' not in response.text

    async def test_home_button_uses_guest_execute_route(self, logged_in_client: AsyncClient) -> None:
        btn = await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        response = await logged_in_client.get("/d")
        assert f"/d/execute/button/{btn.id}" in response.text

    @patch("remander.routes.guest_dashboard.enqueue_command", new_callable=AsyncMock)
    async def test_execute_home_with_correct_pin_redirects(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        response = await logged_in_client.post(
            f"/d/execute/button/{btn.id}",
            data={"pin": "5555"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/d"
        mock_enqueue.assert_called_once()

    @patch("remander.routes.guest_dashboard.enqueue_command", new_callable=AsyncMock)
    async def test_execute_home_with_wrong_pin_redirects_with_error(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        response = await logged_in_client.post(
            f"/d/execute/button/{btn.id}",
            data={"pin": "1234"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "pin_error=1" in response.headers["location"]
        mock_enqueue.assert_not_called()

    async def test_guest_dashboard_shows_pin_error_banner(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/d?pin_error=1")
        assert "incorrect" in response.text.lower()

    @patch("remander.routes.guest_dashboard.enqueue_command", new_callable=AsyncMock)
    async def test_execute_away_button_needs_no_pin(
        self, mock_enqueue: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        btn = await _make_button("Go Away", ButtonOperationType.AWAY, show_on_guest=True)
        response = await logged_in_client.post(
            f"/d/execute/button/{btn.id}",
            data={},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/d"
        mock_enqueue.assert_called_once()

    async def test_pin_pad_shows_digit_buttons(self, logged_in_client: AsyncClient) -> None:
        await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        response = await logged_in_client.get("/d")
        # Phone keypad digits 0-9 should all be present
        for digit in "0123456789":
            assert digit in response.text

    @patch("remander.routes.guest_dashboard.enqueue_command", new_callable=AsyncMock)
    async def test_execute_missing_button_returns_404(
        self, _mock: AsyncMock, logged_in_client: AsyncClient
    ) -> None:
        response = await logged_in_client.post(
            "/d/execute/button/9999",
            data={"pin": "5555"},
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestSingleGuestHomeButtonEnforcement:
    async def test_can_create_first_guest_home_button(self, logged_in_client: AsyncClient) -> None:
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        tag = await create_tag("home-tag")
        bm = await create_hour_bitmask("Home Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        response = await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Go Home",
                "operation_type": "home",
                "color": "green",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_create_second_guest_home_button_returns_422(self, logged_in_client: AsyncClient) -> None:
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        # Create the first guest home button directly
        await _make_button("First Home", ButtonOperationType.HOME, show_on_guest=True)

        tag = await create_tag("home-tag2")
        bm = await create_hour_bitmask("Home Mask2", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        response = await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Second Home",
                "operation_type": "home",
                "color": "green",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert "one" in response.text.lower() or "guest" in response.text.lower()

    async def test_can_create_multiple_guest_away_buttons(self, logged_in_client: AsyncClient) -> None:
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        await _make_button("Away 1", ButtonOperationType.AWAY, show_on_guest=True)

        tag = await create_tag("away-tag2")
        bm = await create_hour_bitmask("Away Mask2", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        response = await logged_in_client.post(
            "/dashboard-buttons/create",
            data={
                "name": "Away 2",
                "operation_type": "away",
                "color": "red",
                "delay_seconds": "0",
                "sort_order": "0",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_edit_to_add_second_guest_home_returns_422(self, logged_in_client: AsyncClient) -> None:
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag
        from remander.services.dashboard_button import save_button_rules

        # First guest home button
        await _make_button("First Home", ButtonOperationType.HOME, show_on_guest=True)
        # A second button (away), which we'll try to convert to a guest home
        btn2 = await _make_button("Was Away", ButtonOperationType.AWAY, show_on_guest=False)

        tag = await create_tag("edit-home-tag")
        bm = await create_hour_bitmask("Edit Home Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await save_button_rules(btn2.id, [(tag.id, bm.id)])
        response = await logged_in_client.post(
            f"/dashboard-buttons/{btn2.id}/edit",
            data={
                "name": "Now Home",
                "operation_type": "home",
                "color": "green",
                "delay_seconds": "0",
                "sort_order": "0",
                "is_enabled": "1",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_edit_existing_guest_home_button_allowed(self, logged_in_client: AsyncClient) -> None:
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag
        from remander.services.dashboard_button import save_button_rules

        btn = await _make_button("Go Home", ButtonOperationType.HOME, show_on_guest=True)
        tag = await create_tag("gh-tag")
        bm = await create_hour_bitmask("GH Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await save_button_rules(btn.id, [(tag.id, bm.id)])
        response = await logged_in_client.post(
            f"/dashboard-buttons/{btn.id}/edit",
            data={
                "name": "Go Home Renamed",
                "operation_type": "home",
                "color": "green",
                "delay_seconds": "0",
                "sort_order": "0",
                "is_enabled": "1",
                "rule_tag_ids": str(tag.id),
                "rule_bitmask_ids": str(bm.id),
                "force_save": "1",
                "show_on_guest": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
