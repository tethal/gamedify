import uuid

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel, select
from sqlmodel import Session


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str
    hashed_password: str


class Quiz(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    rooms: list["Room"] = Relationship(back_populates="quiz", cascade_delete=False)
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    owner: User = Relationship()
    is_public: bool = False


class PlayerConnection(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", ondelete="CASCADE")
    room_code: str = Field(foreign_key="room.code", ondelete="CASCADE")
    active: bool = False
    player: "Player" = Relationship()
    room: "Room" = Relationship()


class Room(SQLModel, table=True):
    code: str = Field(primary_key=True)
    quiz_id: uuid.UUID = Field(foreign_key="quiz.id", ondelete="RESTRICT")
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    quiz: Quiz = Relationship(back_populates="rooms")
    owner: User = Relationship()
    games: list["Game"] = Relationship(back_populates="room")


class Player(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str | None = None
    # rooms: list[Room] = Relationship(back_populates="players", link_model=PlayerRoomLink)


class Game(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_code: str = Field(foreign_key="room.code", ondelete="CASCADE")
    room: Room = Relationship(back_populates="games")
    player_a_id: uuid.UUID = Field(foreign_key="player.id", ondelete="RESTRICT")
    player_a: Player = Relationship(sa_relationship_kwargs=dict(foreign_keys="[Game.player_a_id]"))
    player_b_id: uuid.UUID = Field(foreign_key="player.id", ondelete="RESTRICT")
    player_b: Player = Relationship(sa_relationship_kwargs=dict(foreign_keys="[Game.player_b_id]"))


def create_db(engine):
    SQLModel.metadata.create_all(engine)
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))  # for SQLite only
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(username="admin", hashed_password="admin")
            session.add(admin)
            session.commit()
        if not session.exec(select(Quiz)).all():
            for i in range(1, 4):
                session.add(Quiz(name=f"Quiz {i}", owner=admin))
            session.commit()
        if not session.exec(select(Room)).all():
            quiz = session.exec(select(Quiz)).first()
            session.add(Room(code="123-456", quiz=quiz, owner=admin))
            session.commit()
