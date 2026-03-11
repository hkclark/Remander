"""Data export/import route handlers."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from remander.services.data_export import export_data
from remander.services.data_import import apply_import, migrate_to_current_format, preview_import

router = APIRouter(prefix="/admin")


@router.get("/export")
async def data_export() -> Response:
    """Download all application data as a JSON file."""
    data = await export_data()
    filename = f"remander-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/import", response_class=HTMLResponse)
async def import_page(request: Request) -> HTMLResponse:
    from remander.main import templates

    return templates.TemplateResponse(request, "admin/data_import.html", {})


@router.post("/import/preview", response_class=HTMLResponse)
async def import_preview(request: Request, file: UploadFile) -> HTMLResponse:
    from remander.main import templates

    raw = await file.read()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return templates.TemplateResponse(
            request,
            "admin/_import_preview.html",
            {"error": f"Invalid JSON: {exc}", "counts": None},
        )

    try:
        data = migrate_to_current_format(data)
        counts = preview_import(data)
        # Embed validated JSON for the confirm step
        export_json = json.dumps(data)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "admin/_import_preview.html",
            {"error": str(exc), "counts": None},
        )

    return templates.TemplateResponse(
        request,
        "admin/_import_preview.html",
        {"counts": counts, "export_json": export_json, "error": None},
    )


@router.post("/import/apply", response_class=HTMLResponse)
async def import_apply(request: Request, export_json: str = Form(...)) -> HTMLResponse:
    from remander.main import templates

    try:
        data = json.loads(export_json)
    except (json.JSONDecodeError, ValueError) as exc:
        return templates.TemplateResponse(
            request,
            "partials/toast.html",
            {"message": f"Import failed: invalid JSON — {exc}", "level": "error"},
        )

    result = await apply_import(data)
    if result.success:
        c = result.counts
        message = (
            f"Restored: {c.device_count} device(s), {c.tag_count} tag(s), "
            f"{c.user_count} user(s), {c.dashboard_button_count} button(s)"
        )
        return templates.TemplateResponse(
            request,
            "admin/_import_preview.html",
            {"counts": None, "export_json": None, "error": None, "success_message": message},
        )
    return templates.TemplateResponse(
        request,
        "admin/_import_preview.html",
        {"counts": None, "export_json": None, "error": result.error},
    )
