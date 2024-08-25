import uuid

from sqlmodel import Field, SQLModel, select
from sqlmodel import Session


class Quiz(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str


def create_db(engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(Quiz)).all():
            for i in range(1, 4):
                session.add(Quiz(name=f"Quiz {i}"))
            session.commit()
