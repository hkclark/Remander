"""Dashboard button CRUD route handlers."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.models.enums import ButtonColor, ButtonOperationType
from remander.services.bitmask import list_hour_bitmasks
from remander.services.dashboard_button import (
    create_dashboard_button,
    delete_dashboard_button,
    get_dashboard_button,
    list_dashboard_buttons,
    list_rules_for_button,
    save_button_rules,
    update_dashboard_button,
    validate_button_rules,
)
from remander.services.tag import list_tags

router = APIRouter(prefix="/dashboard-buttons")

_COLORS = list(ButtonColor)
_OPERATION_TYPES = list(ButtonOperationType)


async def _form_context(
    request: Request,
    button: object = None,
    rules: list = None,
    pending_rules: list[tuple[int, int]] | None = None,
    pending_data: dict | None = None,
    error: str | None = None,
    coverage_warning: list[str] | None = None,
) -> dict:
    """Build the shared template context for the button create/edit form.

    pending_data carries submitted field values back on re-render (e.g. coverage warning),
    so the user doesn't lose their Name/Color/Delay entries.
    """
    from remander.main import templates  # noqa: F401  (used by caller)

    return {
        "button": button,
        "colors": _COLORS,
        "operation_types": _OPERATION_TYPES,
        "hour_bitmasks": await list_hour_bitmasks(),
        "tags": await list_tags(),
        "rules": rules or [],
        "pending_rules": pending_rules,
        "pending_data": pending_data,
        "error": error,
        "coverage_warning": coverage_warning or [],
    }


def _parse_rules(
    rule_tag_ids: list[str], rule_bitmask_ids: list[str]
) -> list[tuple[int, int]]:
    """Zip submitted tag/bitmask ID lists into typed rule pairs, skipping blanks."""
    pairs = []
    for tag_str, bitmask_str in zip(rule_tag_ids, rule_bitmask_ids):
        if tag_str and bitmask_str:
            pairs.append((int(tag_str), int(bitmask_str)))
    return pairs


@router.get("", response_class=HTMLResponse)
async def button_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    buttons = await list_dashboard_buttons()
    return templates.TemplateResponse(
        request,
        "dashboard_buttons/list.html",
        {"buttons": buttons},
    )


@router.get("/create", response_class=HTMLResponse)
async def button_create_form(request: Request) -> HTMLResponse:
    from remander.main import templates

    ctx = await _form_context(request)
    return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)


@router.post("/create")
async def button_create(
    request: Request,
    name: str = Form(...),
    operation_type: str = Form(...),
    color: str = Form(...),
    delay_seconds: str = Form("0"),
    sort_order: str = Form("0"),
    rule_tag_ids: list[str] = Form(default=[]),
    rule_bitmask_ids: list[str] = Form(default=[]),
    force_save: str | None = Form(None),
) -> Response:
    from remander.main import templates

    rules = _parse_rules(rule_tag_ids, rule_bitmask_ids)

    if not rules:
        ctx = await _form_context(request, error="At least one tag-bitmask rule is required.")
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    overlap_names, uncovered_names = await validate_button_rules(rules)

    if overlap_names:
        device_list = ", ".join(overlap_names)
        ctx = await _form_context(
            request,
            pending_rules=rules,
            error=f"These devices appear in multiple tags and would receive conflicting bitmasks: {device_list}",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    if uncovered_names and not force_save:
        ctx = await _form_context(
            request,
            pending_rules=rules,
            pending_data={
                "name": name,
                "operation_type": operation_type,
                "color": color,
                "delay_seconds": delay_seconds,
                "sort_order": sort_order,
            },
            coverage_warning=uncovered_names,
        )
        return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)

    btn = await create_dashboard_button(
        name=name,
        operation_type=ButtonOperationType(operation_type),
        color=ButtonColor(color),
        delay_seconds=int(delay_seconds),
        sort_order=int(sort_order),
    )
    await save_button_rules(btn.id, rules)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)


@router.get("/{button_id}/edit", response_class=HTMLResponse)
async def button_edit_form(request: Request, button_id: int) -> Response:
    from remander.main import templates

    button = await get_dashboard_button(button_id)
    if button is None:
        return HTMLResponse("Button not found", status_code=404)

    existing_rules = await list_rules_for_button(button_id)
    ctx = await _form_context(request, button=button, rules=existing_rules)
    return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)


@router.post("/{button_id}/edit")
async def button_edit(
    request: Request,
    button_id: int,
    name: str = Form(...),
    operation_type: str = Form(...),
    color: str = Form(...),
    delay_seconds: str = Form("0"),
    sort_order: str = Form("0"),
    is_enabled: str | None = Form(None),
    rule_tag_ids: list[str] = Form(default=[]),
    rule_bitmask_ids: list[str] = Form(default=[]),
    force_save: str | None = Form(None),
) -> Response:
    from remander.main import templates

    button = await get_dashboard_button(button_id)
    if button is None:
        return HTMLResponse("Button not found", status_code=404)

    rules = _parse_rules(rule_tag_ids, rule_bitmask_ids)

    if not rules:
        existing_rules = await list_rules_for_button(button_id)
        ctx = await _form_context(
            request,
            button=button,
            rules=existing_rules,
            error="At least one tag-bitmask rule is required.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    overlap_names, uncovered_names = await validate_button_rules(rules)

    if overlap_names:
        device_list = ", ".join(overlap_names)
        ctx = await _form_context(
            request,
            button=button,
            pending_rules=rules,
            error=f"These devices appear in multiple tags and would receive conflicting bitmasks: {device_list}",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    if uncovered_names and not force_save:
        ctx = await _form_context(
            request,
            button=button,
            pending_rules=rules,
            pending_data={
                "name": name,
                "operation_type": operation_type,
                "color": color,
                "delay_seconds": delay_seconds,
                "sort_order": sort_order,
                "is_enabled": is_enabled,
            },
            coverage_warning=uncovered_names,
        )
        return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)

    await update_dashboard_button(
        button_id,
        name=name,
        operation_type=ButtonOperationType(operation_type),
        color=ButtonColor(color),
        delay_seconds=int(delay_seconds),
        sort_order=int(sort_order),
        is_enabled=is_enabled is not None,
    )
    await save_button_rules(button_id, rules)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)


@router.post("/{button_id}/delete")
async def button_delete(request: Request, button_id: int) -> RedirectResponse:
    await delete_dashboard_button(button_id)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)
