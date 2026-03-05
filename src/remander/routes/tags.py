"""Tag route handlers — list, create, delete, device tag management."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from remander.models.tag import Tag
from remander.services.tag import (
    add_tag_to_device,
    create_tag,
    delete_tag,
    list_tags,
    remove_tag_from_device,
)

router = APIRouter()


@router.get("/tags", response_class=HTMLResponse)
async def tag_list(request: Request) -> HTMLResponse:
    from remander.main import templates

    tags = await list_tags()
    return templates.TemplateResponse(
        request,
        "tags/list.html",
        {"tags": tags},
    )


@router.post("/tags/create")
async def tag_create(
    request: Request,
    name: str = Form(...),
    show_on_dashboard: str | None = Form(None),
) -> RedirectResponse:
    await create_tag(name=name, show_on_dashboard=show_on_dashboard == "on")
    return RedirectResponse(url="/tags", status_code=303)


@router.post("/tags/{tag_id}/delete")
async def tag_delete(request: Request, tag_id: int) -> RedirectResponse:
    await delete_tag(tag_id)
    return RedirectResponse(url="/tags", status_code=303)


@router.post("/tags/{tag_id}/toggle-dashboard")
async def tag_toggle_dashboard(request: Request, tag_id: int) -> RedirectResponse:
    tag = await Tag.get_or_none(id=tag_id)
    if tag:
        tag.show_on_dashboard = not tag.show_on_dashboard
        await tag.save()
    return RedirectResponse(url="/tags", status_code=303)


@router.post("/devices/{device_id}/tags/add")
async def device_add_tag(
    request: Request,
    device_id: int,
    tag_id: str = Form(...),
) -> RedirectResponse:
    await add_tag_to_device(device_id, int(tag_id))
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)


@router.post("/devices/{device_id}/tags/{tag_id}/remove")
async def device_remove_tag(
    request: Request,
    device_id: int,
    tag_id: int,
) -> RedirectResponse:
    await remove_tag_from_device(device_id, tag_id)
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)
