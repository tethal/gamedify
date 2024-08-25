from jinja2_fragments.fastapi import Jinja2Blocks
from sqlmodel import Session, create_engine

templates = Jinja2Blocks(directory="templates")
engine = create_engine("sqlite:///gamedify.db", echo=True, connect_args={"check_same_thread": False})


def get_db():
    with Session(engine) as session:
        yield session
