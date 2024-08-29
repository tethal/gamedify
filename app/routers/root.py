from typing import Annotated

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.classroom import RoomNotFoundException, find_room_by_code
from app.dependencies import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("root.html", context)


@router.post("/")
async def root_code_submit(request: Request, code: Annotated[str, Form()] = ''):
    try:
        room = find_room_by_code(code)
        return RedirectResponse(url=f'/play/{room.code}', status_code=status.HTTP_303_SEE_OTHER)
    except RoomNotFoundException:
        context = {"request": request, "invalid_code": True, "value": code}
        return templates.TemplateResponse("root.html", context)
