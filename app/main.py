from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .classroom import PlayerNotFoundException, RoomNotFoundException
from .dependencies import engine, templates
from .model import create_db
from .routers import play, quiz, root


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db(engine)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(play.router)
app.include_router(quiz.router)
app.include_router(root.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "exc": exc}, status_code=exc.status_code)


@app.exception_handler(RoomNotFoundException)
async def room_not_found_exception(request: Request, exc: RoomNotFoundException):
    return templates.TemplateResponse("error_room.html", {"request": request, "room_code": exc.room_code},
                                      status_code=404)


@app.exception_handler(PlayerNotFoundException)
async def http_exception_handler(request: Request, exc: PlayerNotFoundException):
    return templates.TemplateResponse("error.html", {"request": request, "exc": exc}, status_code=404)
