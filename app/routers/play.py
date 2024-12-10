import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, WebSocket
from fastapi.responses import HTMLResponse

from app.dependencies import Controller, ControllerFactory, get_event_bus, jinja_env, templates
from app.model import PlayerRole, TileState
from app.util import EventBus
from app.util.ws_handler import WsHandler

router = APIRouter(prefix="/play")


@router.get("/{room_code}", response_class=HTMLResponse)
async def play_root(request: Request,
                    ctrl: Annotated[Controller, Depends()],
                    room_code: str,
                    player_id: Annotated[uuid.UUID | None, Cookie()] = None):
    pc = ctrl.create_player_connection(room_code, player_id)
    if not pc:
        return templates.TemplateResponse("play/room_closed.html", {"request": request})
    context = {
        "request": request,
        "quiz_name": pc.room.quiz.name,
        "room_code": pc.room.code,
        "connection_id": str(pc.id),
    }
    response = templates.TemplateResponse("play/main.html", context)
    response.set_cookie("player_id", value=pc.player.id, expires=259200, httponly=True)
    return response


class PlayerWsHandler(WsHandler):
    def __init__(self,
                 websocket: WebSocket,
                 ctrl_factory: Annotated[ControllerFactory, Depends()],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)],
                 connection_id: uuid.UUID):
        super().__init__(websocket, ctrl_factory, event_bus)
        self.connection_id = connection_id

    async def on_connect(self, ctrl: Controller) -> uuid.UUID:
        pc = ctrl.set_player_connection_active(self.connection_id, True)
        return pc.player.id

    async def on_disconnect(self, ctrl: Controller):
        ctrl.set_player_connection_active(self.connection_id, False)

    async def on_event(self, ctrl: Controller):
        pc = ctrl.get_player_connection(self.connection_id)
        if not pc.player.name:
            template = 'play/no_name.html'
        elif not pc.game and not ctrl.try_start_game(pc):
            template = 'play/no_game.html'
        else:
            template = 'play/game.html'

        t = jinja_env.get_template(template)
        t.globals['TileState'] = TileState
        t.globals['PlayerRole'] = PlayerRole
        msg = t.render(
            player=pc.player,
            room=pc.room,
            game=pc.game,
            connection_id=str(pc.id)
        )
        await self.send(msg)

    async def on_error(self, ctrl: Controller, exc: Exception):
        print(f'Player connection {self.connection_id} error: {exc}')
        msg = jinja_env.get_template('play/error.html').render(exc=exc)
        await self.send(msg)

    async def on_receive(self, ctrl: Controller, msg):
        pc = ctrl.get_player_connection(self.connection_id)
        if msg['action'] == 'set_name':
            ctrl.set_player_name(pc.room, pc.player, msg['player_name'])
        elif msg['action'] == 'tile_click':
            ctrl.tile_click(pc, msg['tile'])
        elif msg['action'] == 'submit_answer':
            ctrl.submit_answer(pc, msg['answer'])
        elif msg['action'] == 'no_answer':
            ctrl.submit_answer(pc, None)
        elif msg['action'] == 'start_new_game':
            ctrl.start_new_game(pc)
        else:
            print("RECEIVED:", msg)


@router.websocket("/ws/{connection_id}")
async def websocket_endpoint(ws_handler: Annotated[PlayerWsHandler, Depends()]):
    await ws_handler.run()
