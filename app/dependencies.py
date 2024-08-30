from typing import Annotated

from fastapi import Depends
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, create_engine

from app.util import EventBus

jinja_env = Environment(loader=FileSystemLoader("templates"))
templates = Jinja2Templates(env=jinja_env)
engine = create_engine("sqlite:///gamedify.db", echo=True, connect_args={"check_same_thread": False})
_event_bus = EventBus()


class DbFactory:
    def __call__(self):
        return Session(engine)


def get_db(db_factory: Annotated[DbFactory, Depends()]):
    with db_factory() as db:
        yield db


def get_event_bus():
    return _event_bus
