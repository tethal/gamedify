import contextlib
import uuid
from typing import Annotated, ContextManager, Sequence

from fastapi import Depends
from sqlmodel import Session, select

from app.dependencies import DbFactory, get_db, get_event_bus
from app.model import Player, PlayerConnection, Room
from app.util import EventBus


class Controller:
    def __init__(self,
                 db: Annotated[Session, Depends(get_db)],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)]):
        self.db = db
        self.event_bus = event_bus

    def is_room_code_valid(self, code: str) -> bool:
        return self.db.get(Room, code) is not None

    def create_player_connection(self, room_code: str, player_id: uuid.UUID) -> PlayerConnection | None:
        if not self.is_room_code_valid(room_code):
            return None
        player = self.db.get(Player, player_id)
        if not player:
            player = Player()
            self.db.add(player)
        pc = PlayerConnection(room_code=room_code, player_id=player.id)
        self.db.add(pc)
        self.db.commit()
        return pc

    def get_player_connection(self, connection_id: uuid.UUID) -> PlayerConnection:
        return self.db.exec(select(PlayerConnection).where(PlayerConnection.id == connection_id)).one()

    def set_player_connection_active(self, connection_id: uuid.UUID, active: bool) -> PlayerConnection:
        pc = self.get_player_connection(connection_id)
        pc.active = active
        self.db.add(pc)
        self.db.commit()
        self.event_bus.notify(pc.room.code)
        return pc

    def set_player_name(self, room: Room, player: Player, name: str | None):
        player.name = name
        self.db.add(player)
        self.db.commit()
        self.event_bus.notify(player.id)
        self.event_bus.notify(room.code)

    def get_player(self, player_id: uuid.UUID) -> Player:
        return self.db.exec(select(Player).where(Player.id == player_id)).one()

    def get_room(self, room_code: str) -> Room:
        return self.db.exec(select(Room).where(Room.code == room_code)).one()

    def get_room_players(self, room_code: str) -> Sequence[Player]:
        return self.db.exec(
            select(Player).join(PlayerConnection).where(PlayerConnection.room_code == room_code,
                                                        PlayerConnection.active).distinct()).all()


class ControllerFactory:
    def __init__(self,
                 db_factory: Annotated[DbFactory, Depends()],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)]):
        self.db_factory = db_factory
        self.event_bus = event_bus

    @contextlib.contextmanager
    def __call__(self) -> ContextManager[Controller]:
        with self.db_factory() as db:
            yield Controller(db, self.event_bus)
