"""Tests for the data export/import routes."""

import json

from httpx import AsyncClient

from remander.models.device import Device
from remander.models.tag import Tag
from tests.factories import create_camera, create_tag


class TestExportRoute:
    async def test_get_export_returns_json(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/export")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    async def test_get_export_triggers_download(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/export")
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]

    async def test_export_content_is_valid_json(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/export")
        data = response.json()
        assert "export_format_version" in data
        assert "devices" in data


class TestImportRoute:
    async def test_get_import_page_returns_200(self, logged_in_client: AsyncClient) -> None:
        response = await logged_in_client.get("/admin/import")
        assert response.status_code == 200
        assert "Import" in response.text

    async def test_post_import_preview_shows_counts(self, logged_in_client: AsyncClient) -> None:
        await create_tag(name="preview-tag")
        await create_camera(name="preview-cam")

        # Export current data
        export_response = await logged_in_client.get("/admin/export")
        export_data = export_response.content

        response = await logged_in_client.post(
            "/admin/import/preview",
            files={"file": ("backup.json", export_data, "application/json")},
        )
        assert response.status_code == 200
        assert "1" in response.text  # at least one device or tag count
        assert "preview-tag" in response.text or "1 tag" in response.text.lower()

    async def test_post_import_apply_restores_data(self, logged_in_client: AsyncClient) -> None:
        await create_tag(name="restored-tag")
        await create_camera(name="restored-cam")

        export_response = await logged_in_client.get("/admin/export")
        export_json = export_response.text

        # Wipe everything
        await Device.all().delete()
        await Tag.all().delete()

        response = await logged_in_client.post(
            "/admin/import/apply",
            data={"export_json": export_json},
        )
        assert response.status_code == 200
        assert await Tag.exists(name="restored-tag")
        assert await Device.exists(name="restored-cam")

    async def test_post_import_preview_invalid_json_returns_error(
        self, logged_in_client: AsyncClient
    ) -> None:
        response = await logged_in_client.post(
            "/admin/import/preview",
            files={"file": ("bad.json", b"not json at all", "application/json")},
        )
        assert response.status_code == 200
        assert "error" in response.text.lower() or "invalid" in response.text.lower()
