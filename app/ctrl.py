import unicodedata
import uuid
from datetime import datetime, timedelta
from random import shuffle
from typing import Sequence

import bcrypt
from sqlalchemy import null
from sqlmodel import Session, select

from app.model import Game, Player, PlayerConnection, PlayerRole, Room, Tile, TileState, User, UserSession
from app.util import EventBus
from app.util import azk


class ControllerImpl:
    def __init__(self, db: Session, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def login(self, username: str, password: str) -> UserSession | None:
        user = self.db.exec(select(User).where(User.username == username)).one_or_none()
        if not user:
            return None
        if not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
            return None
        session = UserSession(user_id=user.id, expires_at=datetime.now() + timedelta(days=3))
        self.db.add(session)
        self.db.commit()
        return session

    def logout(self, session_id: uuid.UUID):
        session = self.db.exec(select(UserSession).where(UserSession.id == session_id)).one_or_none()
        if session:
            self.db.delete(session)
            self.db.commit()

    def get_user_for_session(self, session_id: uuid.UUID) -> User | None:
        session = self.db.exec(select(UserSession).where(UserSession.id == session_id)).one_or_none()
        if not session or session.expires_at < datetime.now():
            return None
        return session.user

    def is_room_code_valid(self, code: str) -> bool:
        return self.db.get(Room, code) is not None

    def create_player_connection(self, room_code: str, player_id: uuid.UUID | None) -> PlayerConnection | None:
        if not self.is_room_code_valid(room_code):
            return None
        player = self.db.get(Player, player_id) if player_id else None
        if not player:
            player = Player()
            self.db.add(player)
        pc = self.db.exec(select(PlayerConnection).where(PlayerConnection.room_code == room_code,
                                                         PlayerConnection.player_id == player.id)).one_or_none()
        if not pc:
            pc = PlayerConnection(room_code=room_code, player_id=player.id)
            self.db.add(pc)
        self.db.commit()
        return pc

    def get_player_connection(self, connection_id: uuid.UUID) -> PlayerConnection | None:
        return self.db.exec(select(PlayerConnection).where(PlayerConnection.id == connection_id)).one_or_none()

    def set_player_connection_active(self, connection_id: uuid.UUID, active: bool) -> PlayerConnection:
        pc = self.get_player_connection(connection_id)
        if not pc:
            return None
        pc.active_count = max(0, pc.active_count + (1 if active else -1))
        self.db.add(pc)
        self.db.commit()
        self.event_bus.notify(pc.room.code)
        if pc.game:
            self.event_bus.notify(pc.game.player_a_id)
            self.event_bus.notify(pc.game.player_b_id)
        return pc

    def set_player_name(self, room: Room, player: Player, name: str | None):
        player.name = name
        self.db.add(player)
        self.db.commit()
        pc = self.db.exec(select(PlayerConnection).where(PlayerConnection.room_code == room.code,
                                                         PlayerConnection.player_id == player.id)).one_or_none()
        if pc.game:
            self.event_bus.notify(pc.game.player_a_id)
            self.event_bus.notify(pc.game.player_b_id)
        else:
            self.event_bus.notify(player.id)
        self.event_bus.notify(room.code)

    def get_player(self, player_id: uuid.UUID) -> Player:
        return self.db.exec(select(Player).where(Player.id == player_id)).one()

    def get_room(self, room_code: str) -> Room:
        return self.db.exec(select(Room).where(Room.code == room_code)).one()

    def room_delete(self, room: Room):
        pcs = self.db.exec(select(PlayerConnection).where(PlayerConnection.room_code == room.code)).all()
        for pc in pcs:
            self.event_bus.notify(pc.player_id)
        self.event_bus.notify(room.code)
        self.db.delete(room)
        self.db.commit()

    def get_room_players(self, room_code: str) -> Sequence[Player]:
        return self.db.exec(
            select(Player).join(PlayerConnection).where(PlayerConnection.room_code == room_code,
                                                        PlayerConnection.active_count > 0).distinct()).all()

    def get_room_games(self, room_code: str) -> Sequence[Game]:
        return self.db.exec(
            select(Game).outerjoin(PlayerConnection).where(
                PlayerConnection.room_code == room_code, PlayerConnection.active_count > 0).distinct()).all()

    def get_waiting_pcs(self, room_code: str) -> Sequence[PlayerConnection]:
        return self.db.exec(
            select(PlayerConnection).join(Player)
            .where(PlayerConnection.room_code == room_code, PlayerConnection.active_count > 0,
                   PlayerConnection.game == null(), Player.name != null())
        ).all()

    def try_start_game(self, pc: PlayerConnection) -> bool:
        pending_pc = next((ppc for ppc in self.get_waiting_pcs(pc.room_code) if ppc.player_id != pc.player_id), None)
        if not pending_pc:
            return False

        quiz = pc.room.quiz
        layout = azk.BoardLayout.from_max_tile_count(len(quiz.questions))

        game = Game(room=pc.room, player_a=pending_pc.player, player_b=pc.player,
                    player_on_turn_role=PlayerRole.A, rows=layout.rows)
        pc.game = game
        pending_pc.game = game
        self.db.add(game)
        self.db.add(pending_pc)
        self.db.add(pc)
        questions = list(quiz.questions)
        shuffle(questions)
        for question, (row, col) in zip(questions, layout.tiles):
            tile = Tile(game=game,
                        row=row, col=col,
                        question="|".join([question.text] + [a.text for a in question.answers]))
            self.db.add(tile)
        self.db.commit()
        self.event_bus.notify(pc.room_code)
        self.event_bus.notify(pending_pc.player_id)
        self.event_bus.notify(pc.player.id)
        return True

    def tile_click(self, pc: PlayerConnection, tile_index: int):
        if not pc.game or pc.game.player_on_turn != pc.player or pc.game.selected_tile is not None:
            return
        tile = pc.game.get_tile_by_index(tile_index)
        if not tile or tile.state != TileState.DEFAULT:
            return
        tile.state = TileState.SELECTED
        self.db.add(tile)
        self.db.commit()
        self.event_bus.notify(pc.game.player_a_id)
        self.event_bus.notify(pc.game.player_b_id)

    def submit_answer(self, pc: PlayerConnection, answer: str | None):

        def normalize(s: str) -> str:
            return ''.join(
                c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip().lower()

        if not pc.game or pc.game.player_on_turn != pc.player or not pc.game.selected_tile:
            return
        invalid = True
        if answer:
            answer = normalize(answer)
            for a in pc.game.selected_tile.answers:
                if normalize(a) == answer:
                    invalid = False
                    break
        tile = pc.game.selected_tile
        player_role = pc.game.player_on_turn_role
        if invalid:
            player_role = player_role.swap()
        tile.state = TileState.from_role(player_role)
        if azk.is_winner_move(pc.game, tile):
            pc.game.player_on_turn_role = player_role
            pc.game.is_over = True
        else:
            pc.game.player_on_turn_role = pc.game.player_on_turn_role.swap()
        self.db.add(pc.game)
        self.db.commit()
        self.event_bus.notify(pc.game.player_a_id)
        self.event_bus.notify(pc.game.player_b_id)

    def start_new_game(self, pc: PlayerConnection):
        if not pc.game:
            return
        players = [pc.game.player_a, pc.game.player_b]
        opponent = pc.game.get_opponent(pc.player)
        if pc.game.is_player_active(opponent):
            pc.game = None
            self.db.add(pc)
        else:
            self.db.delete(pc.game)
        self.db.commit()
        self.event_bus.notify(pc.room_code)
        for player in players:
            self.event_bus.notify(player.id)
