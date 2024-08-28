import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect

from app.classroom import Player, Room, find_room_by_code
from app.dependencies import jinja_env, templates

router = APIRouter(prefix="/play")


def _render_game_content(room: Room, player: Player, connection_id: str) -> str:
    if not player.name:
        template = 'no_name'
    else:
        template = 'no_game'
    return jinja_env.get_template(f'play/{template}.html').render(
        player=player,
        room=room,
        connection_id=connection_id,
    )


class PlayerConnection:
    def __init__(self,
                 room_code: str,
                 connection_id: str,
                 player_id: Annotated[str, Cookie()]):
        self.room = find_room_by_code(room_code)
        self.player = self.room.get_player(player_id)
        self.id = connection_id

    def response(self):
        return HTMLResponse(_render_game_content(self.room, self.player, self.id))


@router.get("/{room_code}", response_class=HTMLResponse)
async def play_root(request: Request,
                    room_code: str,
                    player_id: Annotated[str | None, Cookie()] = None):
    room = find_room_by_code(room_code)
    player = room.get_or_create_player(player_id)
    context = {
        "request": request,
        "quiz_name": f"Literatura",
        "room_code": room.code,
        "connection_id": str(uuid.uuid4()),
    }
    response = templates.TemplateResponse("play/main.html", context)
    response.set_cookie("player_id", value=player.id, expires=259200, httponly=True)
    return response


@router.websocket("/ws/{room_code}/{connection_id}")
async def websocket_endpoint(websocket: WebSocket,
                             room_code: str,
                             connection_id: str):
    try:
        room = find_room_by_code(room_code)
        player = room.get_player(websocket.cookies.get('player_id'))
        queue = asyncio.Queue()

        def post_event(source_connection_id: str, event: str):
            if source_connection_id != connection_id:
                queue.put_nowait(event)

        async def handle_events():
            while await queue.get() != 'close':
                await websocket.send_text(_render_game_content(room, player, connection_id))

        await websocket.accept()
        asyncio.ensure_future(handle_events())
        with player.subscribe(post_event):
            while True:
                # we don't care about the received message, we just want to keep the connection alive
                # and detect when the client disconnects
                await websocket.receive_text()
    except KeyError:
        # room or player not found, close the connection gracefully
        # avoids "ASGI callable returned without sending handshake" error
        await websocket.close()
    except WebSocketDisconnect:
        # consume the exception to avoid log noise
        pass


@router.put("/{room_code}/{connection_id}/set_name", response_class=HTMLResponse)
async def play_set_name(pc: Annotated[PlayerConnection, Depends()],
                        player_name: Annotated[str, Form()] = ''):
    pc.player.set_name(player_name, pc.id)
    return pc.response()
