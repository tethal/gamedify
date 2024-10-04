import contextlib
import uuid
from typing import Annotated, ContextManager

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, create_engine

from app.ctrl import ControllerImpl
from app.util import EventBus

jinja_env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
templates = Jinja2Templates(env=jinja_env)
engine = create_engine("sqlite:///gamedify.db", echo=False, connect_args={"check_same_thread": False})
_event_bus = EventBus()


class DbFactory:
    def __call__(self):
        return Session(engine)


def get_db(db_factory: Annotated[DbFactory, Depends()]):
    with db_factory() as db:
        yield db


def get_event_bus():
    return _event_bus


class Controller(ControllerImpl):
    def __init__(self, db: Annotated[Session, Depends(get_db)], event_bus: Annotated[EventBus, Depends(get_event_bus)]):
        super().__init__(db, event_bus)


class ControllerFactory:
    def __init__(self,
                 db_factory: Annotated[DbFactory, Depends()],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)]):
        self.db_factory = db_factory
        self.event_bus = event_bus

    @contextlib.contextmanager
    def __call__(self) -> ContextManager[Controller]:
        with self.db_factory() as db:
            yield ControllerImpl(db, self.event_bus)


async def current_user(ctrl: Annotated[Controller, Depends()],
                       session_id: Annotated[uuid.UUID | None, Cookie()] = None):
    if session_id:
        if user := ctrl.get_user_for_session(session_id):
            return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


async def current_user_opt(ctrl: Annotated[Controller, Depends()],
                           session_id: Annotated[uuid.UUID | None, Cookie()] = None):
    if session_id:
        if user := ctrl.get_user_for_session(session_id):
            return user
    return None
