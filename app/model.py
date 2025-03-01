import unicodedata
import enum
import os
import uuid
from datetime import datetime, timedelta
from random import shuffle
from typing import Optional

from alembic.config import Config
from alembic import command
from sqlalchemy import Column, Enum, delete, text, update
from sqlmodel import Field, Relationship, SQLModel, select
from sqlmodel import Session

from app.util import azk


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str


class UserSession(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    expires_at: datetime

    # entities
    user: User = Relationship()


class Quiz(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    is_public: bool = False

    # entities
    rooms: list["Room"] = Relationship(back_populates="quiz", cascade_delete=False)
    owner: User = Relationship()
    questions: list["Question"] = Relationship(back_populates="quiz", cascade_delete=True)


class Question(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    text: str
    quiz_id: uuid.UUID = Field(foreign_key="quiz.id", ondelete="CASCADE")

    # entities
    quiz: Quiz = Relationship(back_populates="questions")
    answers: list["Answer"] = Relationship(back_populates="question", cascade_delete=True)


class Answer(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    text: str
    question_id: uuid.UUID = Field(foreign_key="question.id", ondelete="CASCADE")

    # entities
    question: Question = Relationship(back_populates="answers")


class PlayerConnection(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", ondelete="CASCADE")
    room_code: str = Field(foreign_key="room.code", ondelete="CASCADE")
    active_count: int = False
    game_id: uuid.UUID | None = Field(foreign_key="game.id", ondelete="SET NULL")

    # entities
    player: "Player" = Relationship()
    room: "Room" = Relationship()
    game: "Game" = Relationship()


class Room(SQLModel, table=True):
    code: str = Field(primary_key=True)
    quiz_id: uuid.UUID = Field(foreign_key="quiz.id", ondelete="RESTRICT")
    owner_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")

    # entities
    quiz: Quiz = Relationship(back_populates="rooms")
    owner: User = Relationship()
    games: list["Game"] = Relationship(back_populates="room", cascade_delete=True)


class PlayerRole(enum.Enum):
    A = "A"
    B = "B"

    def swap(self):
        return PlayerRole.A if self == PlayerRole.B else PlayerRole.B


class Player(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str | None = None

    # entities
    connections: list[PlayerConnection] = Relationship(back_populates="player")


class Game(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_code: str = Field(foreign_key="room.code", ondelete="CASCADE")
    player_a_id: uuid.UUID = Field(foreign_key="player.id", ondelete="RESTRICT")
    player_b_id: uuid.UUID = Field(foreign_key="player.id", ondelete="RESTRICT")
    player_on_turn_role: PlayerRole = Field(sa_column=Column(Enum(PlayerRole)))
    is_over: bool = False
    rows: int
    last_question: str | None
    last_answer: str | None
    last_answer_time: datetime | None


    # entities
    room: Room = Relationship(back_populates="games")
    player_a: Player = Relationship(sa_relationship_kwargs=dict(foreign_keys="[Game.player_a_id]"))
    player_b: Player = Relationship(sa_relationship_kwargs=dict(foreign_keys="[Game.player_b_id]"))
    tiles: list["Tile"] = Relationship(back_populates="game", cascade_delete=True)

    @property
    def board_view_box(self):
        return azk.BoardLayout(self.rows).view_box

    @property
    def player_on_turn(self) -> Player:
        return self.player_a if self.player_on_turn_role == PlayerRole.A else self.player_b

    @property
    def last_player_on_turn(self) -> Player:
        role = self.player_on_turn_role
        if not (self.is_over and self.is_last_answer_correct):
            role = role.swap()
        return self.player_a if role == PlayerRole.A else self.player_b

    @property
    def selected_tile(self) -> Optional["Tile"]:
        return next((t for t in self.tiles if t.state == TileState.SELECTED), None)

    def get_opponent(self, player: Player) -> Player:
        assert player in (self.player_a, self.player_b)
        return self.player_a if player == self.player_b else self.player_b

    def is_player_active(self, player: Player) -> bool:
        return any(pc.active_count for pc in player.connections if pc.game == self)

    def is_opponent_active(self, player: Player) -> bool:
        opponent = self.get_opponent(player)
        return any(pc.active_count for pc in opponent.connections if pc.game == self)

    def get_tile_by_index(self, index: int) -> Optional["Tile"]:
        return next((t for t in self.tiles if t.index == index), None)

    @property
    def show_last_answer(self) -> bool:
        return self.last_question and self.last_answer_time and datetime.now() < self.last_answer_time + timedelta(seconds=6)

    @property
    def last_answer_text(self) -> str:
        return self.last_answer if self.last_answer else "Nevím"

    @property
    def last_question_text(self) -> str:
        return self.last_question.split('|')[0] if self.last_question else ''

    @property
    def last_question_correct_answers(self) -> list[str]:
        return self.last_question.split('|')[1:] if self.last_question else []

    @property
    def is_last_answer_correct(self) -> bool:

        def normalize(s: str) -> str:
            return ''.join(
                c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip().lower()

        if not self.last_question or not self.last_answer:
            return False

        answer = normalize(self.last_answer)
        return any(normalize(a) == answer for a in self.last_question_correct_answers)

    @property
    def last_tile_winner(self) -> Player | None:
        role = self.player_on_turn_role
        if self.is_last_answer_correct and not self.is_over:
            role = role.swap()
        return self.player_a if role == PlayerRole.A else self.player_b

class TileState(enum.Enum):
    DEFAULT = "DEFAULT"
    SELECTED = "SELECTED"
    A = "A"
    B = "B"

    @staticmethod
    def from_role(role: PlayerRole) -> "TileState":
        return TileState.A if role == PlayerRole.A else TileState.B


class Tile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    game_id: uuid.UUID = Field(foreign_key="game.id", ondelete="CASCADE")
    row: int
    col: int
    state: TileState = Field(sa_column=Column(Enum(TileState)), default=TileState.DEFAULT)
    question: str  # a list of strings separated by '|', the first one is the question, the rest are answers

    # entities
    game: Game = Relationship(back_populates="tiles")

    @property
    def layout(self):
        return azk.TileLayout(self.row, self.col)

    @property
    def index(self):
        return self.layout.id

    @property
    def x(self):
        return self.layout.x

    @property
    def y(self):
        return self.layout.y

    @property
    def question_text(self) -> str:
        return self.question.split('|')[0]

    @property
    def answers(self) -> list[str]:
        return self.question.split('|')[1:]


test_quiz = {
    'Hlavní město Francie': ('Paříž',),
    'Nejvyšší hora světa': ('Mount Everest', 'Everest'),
    'Hlavní město České republiky': ('Praha',),
    'Země původu pizzy': ('Itálie',),
    'Nejdelší řeka na světě': ('Amazonka', 'Nil'),
    'Autor románu Harry Potter': ('J.K. Rowlingová', 'Rowlingová', 'Rowling'),
    'Planeta nejbližší Slunci': ('Merkur',),
    'Hlavní město Německa': ('Berlín',),
    'Největší oceán na světě': ('Tichý', 'Tichý oceán', 'Pacifik'),
    'Vítěz prvního světového poháru ve fotbale': ('Uruguay',),
    'Nejdelší kost v lidském těle': ('Stehenní', 'Stehenní kost', 'femur'),
    'Město, kde se nachází Opera House': ('Sydney',),
    'Hlavní město Španělska': ('Madrid',),
    'Chemický prvek s označením "O"': ('Kyslík',),
    'Hlavní město Itálie': ('Řím',),
    'Stát známý pro fjordy': ('Norsko',),
    'Kdo namaloval Monu Lisu?': ('Leonardo da Vinci', 'da Vinci', 'Leonardo'),
    'Který pták neumí létat a žije v Antarktidě?': ('Tučňák',),
    'Hlavní město Japonska': ('Tokio', 'Tokyo'),
    'Příjmení vynálezce žárovky': ('Edison',),
    'Největší kontinent': ('Asie',),
    'Nejmenší oceán na světě': ('Severní ledový', 'Severní ledový oceán', 'Arktický', 'Arktický oceán'),
    'Země, kde vznikl balet': ('Itálie', 'Francie'),
    'Kolik nohou má pavouk?': ('8', 'osm'),
    'Jakou barvu má chlorofyl?': ('zelenou', 'zelená'),
    'Nejbližší planeta k Zemi': ('Venuše',),
    'Hlavní město Řecka': ('Atény', 'Athény'),
    'Kdo objevil Ameriku?': ('Kolumbus', 'Kryštof Kolumbus', 'Columbus'),
    'Jméno hrdiny knížek o Bradavicích': ('Harry Potter', 'Harry', 'Potter Harry'),
    'Jaké je hlavní město Polska?': ('Varšava',),
    'Země, která má tvar boty': ('Itálie',),
    'Největší savec na světě': ('Velryba', 'modrá velryba',),
    'Jaká část těla produkuje inzulin?': ('Slinivka', 'slinivka břišní', 'Pancreas'),
    'Hlavní město Nizozemska': ('Amsterdam',),
    'Kdo napsal Babičku?': ('Božena Němcová', 'Němcová'),
    'Nejvyšší hora v Česku': ('Sněžka',)
}


def create_db(engine):
    if not os.path.isfile("gamedify.db"):
        SQLModel.metadata.create_all(engine)
        command.stamp(Config("alembic.ini"), "head")
    else:
        command.upgrade(Config("alembic.ini"), "head")
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))  # for SQLite only
    with Session(engine) as session:
        if os.environ.get('GAMEDIFY_PROD', '0') == '1':
            session.exec(delete(Room))
            session.exec(delete(Game))
            session.exec(delete(PlayerConnection))
        else:
            session.exec(update(PlayerConnection).values(active_count=0))
        session.commit()
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin = User(username="admin",
                         hashed_password="$2b$12$VwxFLsSrDOZEQs3HXqHQzOv7rRhJEG4jHFxOd7UGFjSiuDFRyQvEK")
            session.add(admin)
            session.commit()
        if not session.exec(select(Quiz)).all():
            for i in 17, 21, 30, 36:
                quiz = Quiz(name=f"Testovací kvíz {i} otázek", owner=admin)
                session.add(quiz)
                questions = list(test_quiz.items())
                shuffle(questions)
                for question, answers in questions[:i]:
                    q = Question(text=question, quiz=quiz)
                    session.add(q)
                    for answer in answers:
                        session.add(Answer(text=answer, question=q))
            session.commit()
        if not session.exec(select(Room)).all() and os.environ.get('GAMEDIFY_PROD', '0') != '1':
            quiz = session.exec(select(Quiz).where(Quiz.name == "Testovací kvíz 21 otázek")).first()
            session.add(Room(code="1234", quiz=quiz, owner=admin))
            session.commit()
