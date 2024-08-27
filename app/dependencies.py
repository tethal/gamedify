from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, create_engine

jinja_env = Environment(loader=FileSystemLoader("templates"))
templates = Jinja2Templates(env=jinja_env)
engine = create_engine("sqlite:///gamedify.db", echo=True, connect_args={"check_same_thread": False})


def get_db():
    with Session(engine) as session:
        yield session
