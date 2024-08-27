import contextlib
import uuid
from typing import Callable, ContextManager


class RoomNotFoundException(KeyError):
    def __init__(self, room_code: str):
        super().__init__('Room not found')
        self.room_code = room_code


class PlayerNotFoundException(KeyError):
    def __init__(self, player_id: str):
        super().__init__('Player not found')
        self.player_id = player_id


class Player:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.subscribers: list[Callable[[str, str], None]] = []
        self.name: str | None = None

    @contextlib.contextmanager
    def subscribe(self, callback: Callable[[str, str], None]) -> ContextManager:
        self.subscribers.append(callback)
        callback('', 'update')
        yield
        self.subscribers.remove(callback)
        callback('', 'close')

    def notify(self, source_connection_id: str = '', event: str = 'update'):
        for subscriber in self.subscribers:
            subscriber(source_connection_id, event)

    def set_name(self, name: str, source_connection_id: str):
        self.name = name
        self.notify(source_connection_id)

    def reject_name(self):
        self.name = None
        self.notify()


class Room:
    def __init__(self):
        self.code = '123-456'
        self.players: dict[str, Player] = {}

    def get_or_create_player(self, player_id: str | None) -> Player:
        if not player_id or player_id not in self.players:
            player = Player()
            self.players[player.id] = player
            return player
        return self.players[player_id]

    def get_player(self, player_id: str) -> Player:
        if player_id not in self.players:
            raise PlayerNotFoundException(player_id)
        return self.players.get(player_id)


# This is a fake room that will be used until we implement room creation
_room = Room()


def find_room_by_code(room_code: str) -> Room:
    if room_code == _room.code:
        return _room
    raise RoomNotFoundException(room_code)
