from fastapi.templating import Jinja2Templates
from sqlmodel import Session, create_engine

templates = Jinja2Templates(directory="templates")
engine = create_engine("sqlite:///gamedify.db", echo=True, connect_args={"check_same_thread": False})


def get_db():
    with Session(engine) as session:
        yield session
