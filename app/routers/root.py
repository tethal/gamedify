from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.ctrl import Controller
from app.dependencies import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("root.html", context)


@router.post("/")
async def root_code_submit(request: Request,
                           ctrl: Annotated[Controller, Depends()],
                           code: Annotated[str, Form()] = ''):
    if ctrl.is_room_code_valid(code):
        return RedirectResponse(url=f'/play/{code}', status_code=status.HTTP_303_SEE_OTHER)
    else:
        context = {"request": request, "invalid_code": True, "value": code}
        return templates.TemplateResponse("root.html", context)
