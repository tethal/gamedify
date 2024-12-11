from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import NoResultFound
from starlette.exceptions import HTTPException as StarletteHTTPException

from .dependencies import engine, templates
from .model import create_db
from .routers import auth, play, quiz, room, root


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db(engine)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(auth.router)
app.include_router(play.router)
app.include_router(quiz.router)
app.include_router(room.router)
app.include_router(root.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 403:
        return RedirectResponse(url=request.url_for('login_form'), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("error.html", {"request": request, "exc": exc}, status_code=exc.status_code)


@app.exception_handler(NoResultFound)
async def http_exception_handler(request: Request, exc: NoResultFound):
    return templates.TemplateResponse("error.html", {"request": request, "exc": exc},
                                      status_code=status.HTTP_404_NOT_FOUND)
