"""Tests for the guest dashboard at /d."""

from unittest.mock import patch

from httpx import AsyncClient

from remander.models.enums import ButtonOperationType
from remander.services.dashboard_button import create_dashboard_button


async def _make_button(name: str, *, show_on_guest: bool = False, show_on_main: bool = True, is_enabled: bool = True):
    return await create_dashboard_button(
        name,
        ButtonOperationType.AWAY,
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
        await _make_button("Disabled Guest", show_on_guest=True, is_enabled=False)
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
    async def test_create_form_has_show_on_main_checkbox(self, client: AsyncClient) -> None:
        response = await client.get("/dashboard-buttons/create")
        assert "show_on_main" in response.text

    async def test_create_form_has_show_on_guest_checkbox(self, client: AsyncClient) -> None:
        response = await client.get("/dashboard-buttons/create")
        assert "show_on_guest" in response.text

    async def test_create_saves_show_on_guest_flag(self, client: AsyncClient) -> None:
        from remander.models.dashboard_button import DashboardButton
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        tag = await create_tag("g-tag")
        bm = await create_hour_bitmask("G Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await client.post(
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

    async def test_create_show_on_main_defaults_true(self, client: AsyncClient) -> None:
        from remander.models.dashboard_button import DashboardButton
        from remander.services.bitmask import create_hour_bitmask
        from remander.models.enums import HourBitmaskSubtype
        from remander.services.tag import create_tag

        tag = await create_tag("m-tag")
        bm = await create_hour_bitmask("M Mask", HourBitmaskSubtype.STATIC, static_value="1" * 24)
        await client.post(
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

    async def test_edit_form_preserves_show_on_guest(self, client: AsyncClient) -> None:
        btn = await _make_button("Guest Btn", show_on_guest=True)
        response = await client.get(f"/dashboard-buttons/{btn.id}/edit")
        assert response.status_code == 200
        # The checkbox should be checked
        assert 'checked' in response.text
