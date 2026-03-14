"""Dashboard button CRUD route handlers."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from remander.models.dashboard_button import DashboardButton
from remander.app_colors import PALETTE
from remander.models.enums import ButtonOperationType
from remander.services.bitmask import list_hour_bitmasks
from remander.services.dashboard_button import (
    create_dashboard_button,
    delete_dashboard_button,
    get_dashboard_button,
    list_dashboard_buttons,
    list_mute_tags_for_button,
    list_rules_for_button,
    save_button_mute_tags,
    save_button_rules,
    update_dashboard_button,
    validate_button_rules,
)
from remander.services.tag import list_tags

router = APIRouter(prefix="/dashboard-buttons")

_OPERATION_TYPES = list(ButtonOperationType)


async def _form_context(
    request: Request,
    button: object = None,
    rules: list = None,
    pending_rules: list[tuple[int, int]] | None = None,
    pending_data: dict | None = None,
    error: str | None = None,
    coverage_warning: list[str] | None = None,
    existing_mute_tag_ids: list[int] | None = None,
) -> dict:
    """Build the shared template context for the button create/edit form.

    pending_data carries submitted field values back on re-render (e.g. coverage warning),
    so the user doesn't lose their Name/Color/Delay entries.
    """
    from remander.main import templates  # noqa: F401  (used by caller)

    from remander.services.app_config import get_custom_colors

    return {
        "button": button,
        "palette": PALETTE,
        "custom_colors": await get_custom_colors(),
        "operation_types": _OPERATION_TYPES,
        "hour_bitmasks": await list_hour_bitmasks(),
        "tags": await list_tags(),
        "rules": rules or [],
        "pending_rules": pending_rules,
        "pending_data": pending_data,
        "error": error,
        "coverage_warning": coverage_warning or [],
        "existing_mute_tag_ids": existing_mute_tag_ids or [],
    }


async def _check_guest_home_conflict(
    operation_type: str,
    show_on_guest: str | None,
    exclude_id: int | None = None,
) -> bool:
    """Return True if adding a guest Home button would violate the one-per-guest-dashboard rule."""
    if show_on_guest is None or operation_type != "home":
        return False
    qs = DashboardButton.filter(
        show_on_guest=True,
        operation_type=ButtonOperationType.HOME,
        is_enabled=True,
    )
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    return await qs.exists()


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
    from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule

    buttons = await list_dashboard_buttons()

    # Fetch rule counts for all buttons in one query
    button_ids = [b.id for b in buttons]
    all_rules = await DashboardButtonBitmaskRule.filter(dashboard_button_id__in=button_ids)
    rule_counts: dict[int, int] = {}
    for rule in all_rules:
        rule_counts[rule.dashboard_button_id] = rule_counts.get(rule.dashboard_button_id, 0) + 1

    return templates.TemplateResponse(
        request,
        "dashboard_buttons/list.html",
        {"buttons": buttons, "rule_counts": rule_counts},
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
    show_on_main: str | None = Form(None),
    show_on_guest: str | None = Form(None),
    mute_notifications_enabled: str | None = Form(None),
    mute_duration_seconds: str = Form("180"),
    mute_tag_ids: list[str] = Form(default=[]),
) -> Response:
    from remander.main import templates

    rules = _parse_rules(rule_tag_ids, rule_bitmask_ids)
    mute_enabled = mute_notifications_enabled is not None
    mute_tag_id_ints = [int(t) for t in mute_tag_ids if t]
    submitted = {
        "name": name,
        "operation_type": operation_type,
        "color": color,
        "delay_seconds": delay_seconds,
        "sort_order": sort_order,
        "show_on_main": show_on_main,
        "show_on_guest": show_on_guest,
        "mute_notifications_enabled": mute_notifications_enabled,
        "mute_duration_seconds": mute_duration_seconds,
    }

    if not rules:
        ctx = await _form_context(
            request,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            error="At least one tag-bitmask rule is required.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    if mute_enabled and not mute_tag_id_ints:
        ctx = await _form_context(
            request,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=[],
            error="At least one mute tag is required when notification mute is enabled.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    overlap_names, uncovered_names = await validate_button_rules(rules)

    if overlap_names:
        device_list = ", ".join(overlap_names)
        ctx = await _form_context(
            request,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            error=f"These devices appear in multiple tags and would receive conflicting bitmasks: {device_list}",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    if uncovered_names and not force_save:
        ctx = await _form_context(
            request,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            coverage_warning=uncovered_names,
        )
        return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)

    if await _check_guest_home_conflict(operation_type, show_on_guest):
        ctx = await _form_context(
            request,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            error="Only one Home button can be assigned to the Guest Dashboard.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    btn = await create_dashboard_button(
        name=name,
        operation_type=ButtonOperationType(operation_type),
        color=color,
        delay_seconds=int(delay_seconds),
        sort_order=int(sort_order),
        show_on_main=show_on_main is not None,
        show_on_guest=show_on_guest is not None,
        mute_notifications_enabled=mute_enabled,
        mute_duration_seconds=int(mute_duration_seconds) if mute_duration_seconds else 180,
    )
    await save_button_rules(btn.id, rules)
    if mute_enabled:
        await save_button_mute_tags(btn.id, mute_tag_id_ints)
    if color not in PALETTE:
        from remander.services.app_config import add_custom_color
        await add_custom_color(color)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)


@router.get("/{button_id}/edit", response_class=HTMLResponse)
async def button_edit_form(request: Request, button_id: int) -> Response:
    from remander.main import templates

    button = await get_dashboard_button(button_id)
    if button is None:
        return HTMLResponse("Button not found", status_code=404)

    existing_rules = await list_rules_for_button(button_id)
    existing_mute_tags = await list_mute_tags_for_button(button_id)
    existing_mute_tag_ids = [t.id for t in existing_mute_tags]
    ctx = await _form_context(
        request,
        button=button,
        rules=existing_rules,
        existing_mute_tag_ids=existing_mute_tag_ids,
    )
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
    show_on_main: str | None = Form(None),
    show_on_guest: str | None = Form(None),
    mute_notifications_enabled: str | None = Form(None),
    mute_duration_seconds: str = Form("180"),
    mute_tag_ids: list[str] = Form(default=[]),
) -> Response:
    from remander.main import templates

    button = await get_dashboard_button(button_id)
    if button is None:
        return HTMLResponse("Button not found", status_code=404)

    rules = _parse_rules(rule_tag_ids, rule_bitmask_ids)
    mute_enabled = mute_notifications_enabled is not None
    mute_tag_id_ints = [int(t) for t in mute_tag_ids if t]
    submitted = {
        "name": name,
        "operation_type": operation_type,
        "color": color,
        "delay_seconds": delay_seconds,
        "sort_order": sort_order,
        "is_enabled": is_enabled,
        "show_on_main": show_on_main,
        "show_on_guest": show_on_guest,
        "mute_notifications_enabled": mute_notifications_enabled,
        "mute_duration_seconds": mute_duration_seconds,
    }

    if not rules:
        existing_rules = await list_rules_for_button(button_id)
        ctx = await _form_context(
            request,
            button=button,
            rules=existing_rules,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            error="At least one tag-bitmask rule is required.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    if mute_enabled and not mute_tag_id_ints:
        existing_rules = await list_rules_for_button(button_id)
        ctx = await _form_context(
            request,
            button=button,
            rules=existing_rules,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=[],
            error="At least one mute tag is required when notification mute is enabled.",
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
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
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
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            coverage_warning=uncovered_names,
        )
        return templates.TemplateResponse(request, "dashboard_buttons/form.html", ctx)

    if await _check_guest_home_conflict(operation_type, show_on_guest, exclude_id=button_id):
        ctx = await _form_context(
            request,
            button=button,
            pending_rules=rules,
            pending_data=submitted,
            existing_mute_tag_ids=mute_tag_id_ints,
            error="Only one Home button can be assigned to the Guest Dashboard.",
        )
        return templates.TemplateResponse(
            request, "dashboard_buttons/form.html", ctx, status_code=422
        )

    await update_dashboard_button(
        button_id,
        name=name,
        operation_type=ButtonOperationType(operation_type),
        color=color,
        delay_seconds=int(delay_seconds),
        sort_order=int(sort_order),
        is_enabled=is_enabled is not None,
        show_on_main=show_on_main is not None,
        show_on_guest=show_on_guest is not None,
        mute_notifications_enabled=mute_enabled,
        mute_duration_seconds=int(mute_duration_seconds) if mute_duration_seconds else 180,
    )
    await save_button_rules(button_id, rules)
    await save_button_mute_tags(button_id, mute_tag_id_ints if mute_enabled else [])
    if color not in PALETTE:
        from remander.services.app_config import add_custom_color
        await add_custom_color(color)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)


@router.post("/{button_id}/delete")
async def button_delete(request: Request, button_id: int) -> RedirectResponse:
    await delete_dashboard_button(button_id)
    return RedirectResponse(url="/dashboard-buttons", status_code=303)
