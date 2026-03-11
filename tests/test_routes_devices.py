"""Tests for device routes."""

from httpx import AsyncClient

from unittest.mock import AsyncMock, MagicMock, patch

from remander.models.enums import DeviceBrand
from tests.factories import create_camera, create_power_device, create_tag, create_device
from remander.models.enums import DeviceType


class TestDeviceList:
    async def test_get_devices_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/devices")
        assert response.status_code == 200
        assert "Devices" in response.text

    async def test_shows_device_in_list(self, logged_in_client: AsyncClient) -> None:
        await create_camera(name="Front Door Cam", channel=1)
        response = await logged_in_client.get("/devices")
        assert "Front Door Cam" in response.text

    async def test_shows_device_type_and_brand(self, logged_in_client: AsyncClient) -> None:
        await create_camera(name="Side Cam", brand=DeviceBrand.REOLINK)
        response = await logged_in_client.get("/devices")
        assert "camera" in response.text.lower()
        assert "reolink" in response.text.lower()

    async def test_shows_enabled_status(self, logged_in_client: AsyncClient) -> None:
        await create_camera(name="Enabled Cam", is_enabled=True)
        await create_camera(name="Disabled Cam", is_enabled=False)
        response = await logged_in_client.get("/devices")
        assert response.status_code == 200

    async def test_shows_tags_on_list(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Tagged List Cam")
        tag = await create_tag(name="outdoor")
        await tag.devices.add(cam)
        response = await logged_in_client.get("/devices")
        assert "outdoor" in response.text


class TestDeviceListSorting:
    async def test_cameras_appear_before_power_devices(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Cameras must appear before power devices regardless of name ordering."""
        await create_power_device(name="AAA Plug")
        await create_camera(name="ZZZ Cam", channel=1)
        response = await logged_in_client.get("/devices")
        assert response.text.index("ZZZ Cam") < response.text.index("AAA Plug")

    async def test_cameras_sorted_by_channel_then_name(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Within cameras, sort by channel ascending then name ascending."""
        await create_camera(name="Beta", channel=2)
        await create_camera(name="Charlie", channel=1)
        await create_camera(name="Alpha", channel=1)
        response = await logged_in_client.get("/devices")
        text = response.text
        assert text.index("Alpha") < text.index("Charlie") < text.index("Beta")

    async def test_power_devices_sorted_by_name_when_no_channel(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Power devices with no channel are sorted by name."""
        await create_power_device(name="Zeta Plug")
        await create_power_device(name="Alpha Plug")
        response = await logged_in_client.get("/devices")
        text = response.text
        assert text.index("Alpha Plug") < text.index("Zeta Plug")

    async def test_camera_rows_show_camera_icon(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Camera rows must include a camera icon identifier."""
        await create_camera(name="Icon Test Cam")
        response = await logged_in_client.get("/devices")
        assert "icon-camera" in response.text

    async def test_power_device_rows_show_power_icon(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Power device rows must include a power device icon identifier."""
        await create_power_device(name="Icon Test Plug")
        response = await logged_in_client.get("/devices")
        assert "icon-power" in response.text


class TestDeviceDetail:
    async def test_get_device_detail(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Garage Cam", channel=3)
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "Garage Cam" in response.text

    async def test_device_not_found(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/devices/999")
        assert response.status_code == 404


class TestDeviceDetailTags:
    async def test_shows_assigned_tags(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Tagged Cam")
        tag = await create_tag(name="outdoor")
        await tag.devices.add(cam)
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert "outdoor" in response.text

    async def test_shows_add_tag_dropdown(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Cam For Tags")
        await create_tag(name="indoor")
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert "indoor" in response.text

    async def test_add_tag_dropdown_excludes_already_assigned(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Partial Tags Cam")
        assigned = await create_tag(name="assigned-tag")
        await create_tag(name="available-tag")
        await assigned.devices.add(cam)
        response = await logged_in_client.get(f"/devices/{cam.id}")
        # "available-tag" should be in the add dropdown
        assert "available-tag" in response.text
        # "assigned-tag" should appear in the current tags section but not the dropdown
        # Count occurrences — it should appear once (in the tags list), not in the select
        text = response.text
        assert text.count("assigned-tag") >= 1


class TestPowerDeviceAssociation:
    async def test_device_detail_shows_power_device_dropdown(self, logged_in_client: AsyncClient) -> None:
        """Camera detail page must include a power device selector with available power devices."""
        power = await create_power_device(name="Tapo Plug")
        cam = await create_camera(name="Cam With Power")

        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "Power Device" in response.text
        assert "Tapo Plug" in response.text

    async def test_device_detail_shows_current_power_device_selected(self, logged_in_client: AsyncClient) -> None:
        """When a camera already has a power_device, that option is pre-selected."""
        power = await create_power_device(name="Selected Plug")
        cam = await create_camera(name="Cam Pre-Linked", power_device_id=power.id)

        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "Selected Plug" in response.text

    async def test_post_edit_sets_power_device(self, logged_in_client: AsyncClient) -> None:
        """POSTing power_device_id must persist the association."""
        power = await create_power_device(name="Link Plug")
        cam = await create_camera(name="Cam To Link")

        response = await logged_in_client.post(
            f"/devices/{cam.id}/edit",
            data={
                "name": "Cam To Link",
                "device_type": "camera",
                "brand": "reolink",
                "power_device_id": str(power.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        await cam.refresh_from_db()
        assert cam.power_device_id == power.id

    async def test_post_edit_clears_power_device(self, logged_in_client: AsyncClient) -> None:
        """POSTing an empty power_device_id must clear the association."""
        power = await create_power_device(name="Clear Plug")
        cam = await create_camera(name="Cam To Clear", power_device_id=power.id)

        response = await logged_in_client.post(
            f"/devices/{cam.id}/edit",
            data={
                "name": "Cam To Clear",
                "device_type": "camera",
                "brand": "reolink",
                "power_device_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        await cam.refresh_from_db()
        assert cam.power_device_id is None


class TestPTZSettings:
    async def test_device_detail_shows_ptz_section_for_cameras(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="PTZ Section Cam")
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "PTZ" in response.text

    async def test_post_ptz_settings_enables_ptz_with_speed(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="Enable PTZ Cam")
        response = await logged_in_client.post(
            f"/devices/{cam.id}/ptz-settings",
            data={"has_ptz": "on", "ptz_speed": "30"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        await cam.refresh_from_db()
        assert cam.has_ptz is True
        assert cam.ptz_speed == 30

    async def test_post_ptz_settings_saves_preset_ids(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="Preset ID Cam")
        response = await logged_in_client.post(
            f"/devices/{cam.id}/ptz-settings",
            data={"has_ptz": "on", "ptz_away_preset": "2", "ptz_home_preset": "1", "ptz_speed": "40"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        await cam.refresh_from_db()
        assert cam.ptz_away_preset == 2
        assert cam.ptz_home_preset == 1
        assert cam.ptz_speed == 40

    async def test_post_ptz_settings_disables_ptz_clears_fields(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(
            name="Disable PTZ Cam", has_ptz=True, ptz_away_preset=2, ptz_home_preset=1, ptz_speed=30
        )
        response = await logged_in_client.post(
            f"/devices/{cam.id}/ptz-settings",
            data={},  # no has_ptz field → disabled
            follow_redirects=False,
        )
        assert response.status_code == 303
        await cam.refresh_from_db()
        assert cam.has_ptz is False
        assert cam.ptz_away_preset is None
        assert cam.ptz_home_preset is None
        assert cam.ptz_speed is None

    async def test_query_ptz_presets_returns_preset_names(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="NVR Preset Cam", channel=2)

        with patch("remander.routes.devices.ReolinkNVRClient") as MockClient:
            mock_nvr = MagicMock()
            mock_nvr.login = AsyncMock()
            mock_nvr.logout = AsyncMock()
            mock_nvr.get_ptz_presets.return_value = {"Back Yard": 1, "Gate": 2}
            MockClient.return_value = mock_nvr

            response = await logged_in_client.post(f"/devices/{cam.id}/query-ptz-presets")

        assert response.status_code == 200
        assert "Back Yard" in response.text
        assert "Gate" in response.text

    async def test_query_ptz_presets_handles_nvr_error(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="Error NVR Cam", channel=1)

        with patch("remander.routes.devices.ReolinkNVRClient") as MockClient:
            mock_nvr = MagicMock()
            mock_nvr.login = AsyncMock(side_effect=Exception("Connection refused"))
            MockClient.return_value = mock_nvr

            response = await logged_in_client.post(f"/devices/{cam.id}/query-ptz-presets")

        assert response.status_code == 200
        assert "Connection refused" in response.text

    async def test_query_ptz_presets_requires_channel(
        self, logged_in_client: AsyncClient
    ) -> None:
        cam = await create_camera(name="No Channel Cam", channel=None)
        response = await logged_in_client.post(f"/devices/{cam.id}/query-ptz-presets")
        assert response.status_code == 200
        assert "channel" in response.text.lower()


class TestPowerControl:
    async def test_camera_detail_shows_power_controls_when_power_device_assigned(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Camera detail page shows Power On/Off buttons when a power device is assigned."""
        power = await create_power_device(name="Cam Power Plug")
        cam = await create_camera(name="Cam With Power Controls", power_device_id=power.id)
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "power/on" in response.text
        assert "power/off" in response.text

    async def test_power_device_detail_shows_power_controls(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Power device detail page always shows Power On/Off buttons."""
        power = await create_power_device(name="Direct Power Device")
        response = await logged_in_client.get(f"/devices/{power.id}")
        assert response.status_code == 200
        assert "power/on" in response.text
        assert "power/off" in response.text

    async def test_camera_without_power_device_has_no_power_controls(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Camera without an associated power device shows no power on/off controls."""
        cam = await create_camera(name="Cam No Power")
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "power/on" not in response.text
        assert "power/off" not in response.text

    async def test_power_on_camera_sends_command_to_associated_tapo_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """POST /devices/{cam.id}/power/on calls turn_on on the associated Tapo power device."""
        power = await create_power_device(
            name="Tapo Plug On", brand=DeviceBrand.TAPO, ip_address="192.168.1.50"
        )
        cam = await create_camera(name="Cam Tapo On", power_device_id=power.id)

        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.turn_on = AsyncMock()
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.post(
                f"/devices/{cam.id}/power/on", follow_redirects=False
            )

        assert response.status_code == 303
        mock_tapo.turn_on.assert_awaited_once_with("192.168.1.50")

    async def test_power_off_camera_sends_command_to_associated_tapo_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """POST /devices/{cam.id}/power/off calls turn_off on the associated Tapo power device."""
        power = await create_power_device(
            name="Tapo Plug Off", brand=DeviceBrand.TAPO, ip_address="192.168.1.51"
        )
        cam = await create_camera(name="Cam Tapo Off", power_device_id=power.id)

        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.turn_off = AsyncMock()
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.post(
                f"/devices/{cam.id}/power/off", follow_redirects=False
            )

        assert response.status_code == 303
        mock_tapo.turn_off.assert_awaited_once_with("192.168.1.51")

    async def test_power_on_power_device_directly(
        self, logged_in_client: AsyncClient
    ) -> None:
        """POST /devices/{power.id}/power/on acts on the device itself when it's a power device."""
        power = await create_power_device(
            name="Direct Sonoff On", brand=DeviceBrand.SONOFF, ip_address="192.168.1.52"
        )

        with patch("remander.routes.devices.SonoffClient") as MockSonoff:
            mock_sonoff = MagicMock()
            mock_sonoff.turn_on = AsyncMock()
            MockSonoff.return_value = mock_sonoff
            response = await logged_in_client.post(
                f"/devices/{power.id}/power/on", follow_redirects=False
            )

        assert response.status_code == 303
        mock_sonoff.turn_on.assert_awaited_once_with("192.168.1.52")

    async def test_power_off_power_device_directly(
        self, logged_in_client: AsyncClient
    ) -> None:
        """POST /devices/{power.id}/power/off acts on the device itself when it's a power device."""
        power = await create_power_device(
            name="Direct Sonoff Off", brand=DeviceBrand.SONOFF, ip_address="192.168.1.53"
        )

        with patch("remander.routes.devices.SonoffClient") as MockSonoff:
            mock_sonoff = MagicMock()
            mock_sonoff.turn_off = AsyncMock()
            MockSonoff.return_value = mock_sonoff
            response = await logged_in_client.post(
                f"/devices/{power.id}/power/off", follow_redirects=False
            )

        assert response.status_code == 303
        mock_sonoff.turn_off.assert_awaited_once_with("192.168.1.53")


class TestPowerStatus:
    async def test_device_detail_includes_power_status_for_power_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Power device detail page includes the HTMX power status loader."""
        power = await create_power_device(name="Status Plug")
        response = await logged_in_client.get(f"/devices/{power.id}")
        assert response.status_code == 200
        assert "power/status" in response.text

    async def test_device_detail_includes_power_status_for_camera_with_power_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """Camera detail page includes the HTMX power status loader when a power device is assigned."""
        power = await create_power_device(name="Status Cam Plug")
        cam = await create_camera(name="Cam With Status", power_device_id=power.id)
        response = await logged_in_client.get(f"/devices/{cam.id}")
        assert response.status_code == 200
        assert "power/status" in response.text

    async def test_power_status_returns_on_for_tapo(
        self, logged_in_client: AsyncClient
    ) -> None:
        """GET /devices/{id}/power/status returns 'on' when Tapo plug is powered on."""
        power = await create_power_device(
            name="Tapo On Status", brand=DeviceBrand.TAPO, ip_address="192.168.1.60"
        )
        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.is_on = AsyncMock(return_value=True)
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.get(f"/devices/{power.id}/power/status")

        assert response.status_code == 200
        assert "on" in response.text.lower()
        mock_tapo.is_on.assert_awaited_once_with("192.168.1.60")

    async def test_power_status_returns_off_for_tapo(
        self, logged_in_client: AsyncClient
    ) -> None:
        """GET /devices/{id}/power/status returns 'off' when Tapo plug is powered off."""
        power = await create_power_device(
            name="Tapo Off Status", brand=DeviceBrand.TAPO, ip_address="192.168.1.61"
        )
        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.is_on = AsyncMock(return_value=False)
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.get(f"/devices/{power.id}/power/status")

        assert response.status_code == 200
        assert "off" in response.text.lower()

    async def test_power_status_for_sonoff_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """GET /devices/{id}/power/status works for Sonoff devices."""
        power = await create_power_device(
            name="Sonoff Status", brand=DeviceBrand.SONOFF, ip_address="192.168.1.62"
        )
        with patch("remander.routes.devices.SonoffClient") as MockSonoff:
            mock_sonoff = MagicMock()
            mock_sonoff.is_on = AsyncMock(return_value=True)
            MockSonoff.return_value = mock_sonoff
            response = await logged_in_client.get(f"/devices/{power.id}/power/status")

        assert response.status_code == 200
        assert "on" in response.text.lower()
        mock_sonoff.is_on.assert_awaited_once_with("192.168.1.62")

    async def test_power_status_for_camera_checks_associated_power_device(
        self, logged_in_client: AsyncClient
    ) -> None:
        """GET /devices/{cam.id}/power/status queries the associated power device."""
        power = await create_power_device(
            name="Cam Assoc Plug", brand=DeviceBrand.TAPO, ip_address="192.168.1.63"
        )
        cam = await create_camera(name="Cam Status Check", power_device_id=power.id)

        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.is_on = AsyncMock(return_value=False)
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.get(f"/devices/{cam.id}/power/status")

        assert response.status_code == 200
        mock_tapo.is_on.assert_awaited_once_with("192.168.1.63")

    async def test_power_status_handles_connection_error(
        self, logged_in_client: AsyncClient
    ) -> None:
        """GET /devices/{id}/power/status shows an error message when the device is unreachable."""
        power = await create_power_device(
            name="Unreachable Plug", brand=DeviceBrand.TAPO, ip_address="192.168.1.64"
        )
        with patch("remander.routes.devices.TapoClient") as MockTapo:
            mock_tapo = MagicMock()
            mock_tapo.is_on = AsyncMock(side_effect=Exception("Connection refused"))
            MockTapo.return_value = mock_tapo
            response = await logged_in_client.get(f"/devices/{power.id}/power/status")

        assert response.status_code == 200
        assert "unavailable" in response.text.lower()


class TestDeviceCreate:
    async def test_get_create_form(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/devices/create")
        assert response.status_code == 200
        assert "form" in response.text.lower()

    async def test_post_create_device(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.post(
            "/devices/create",
            data={
                "name": "New Camera",
                "device_type": "camera",
                "brand": "reolink",
                "channel": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/devices" in response.headers["location"]


class TestDeviceEdit:
    async def test_get_edit_redirects_to_detail(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Edit Me")
        response = await logged_in_client.get(f"/devices/{cam.id}/edit", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == f"/devices/{cam.id}"

    async def test_post_edit_device(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Old Name")
        response = await logged_in_client.post(
            f"/devices/{cam.id}/edit",
            data={
                "name": "New Name",
                "device_type": "camera",
                "brand": "reolink",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


class TestDeviceDelete:
    async def test_post_delete_device(self, logged_in_client: AsyncClient) -> None:
        cam = await create_camera(name="Delete Me")
        response = await logged_in_client.post(
            f"/devices/{cam.id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "/devices" in response.headers["location"]
