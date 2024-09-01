import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import Controller, templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request,
                     ctrl: Annotated[Controller, Depends()],
                     session_id: Annotated[uuid.UUID | None, Cookie()] = None):
    if session_id and ctrl.get_user_for_session(session_id):
        return RedirectResponse(url=request.url_for('quiz_root'), status_code=status.HTTP_303_SEE_OTHER)
    context = {"request": request}
    return templates.TemplateResponse("login.html", context)


@router.post("/login", response_class=HTMLResponse)
async def login_form(request: Request,
                     username: Annotated[str, Form()],
                     password: Annotated[str, Form()],
                     ctrl: Annotated[Controller, Depends()]):
    session = ctrl.login(username, password)
    if session:
        response = RedirectResponse(url=request.url_for('quiz_root'), status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("session_id", value=str(session.id), expires=259200,
                            secure=True, httponly=True, samesite="lax")
        return response

    context = {"request": request, "username": username, "invalid_login": True}
    return templates.TemplateResponse("login.html", context)


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request,
                 ctrl: Annotated[Controller, Depends()],
                 session_id: Annotated[uuid.UUID | None, Cookie()] = None):
    if session_id:
        ctrl.logout(session_id)
    response = RedirectResponse(url=request.url_for('root'), status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_id")
    return response
