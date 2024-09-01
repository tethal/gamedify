import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.dependencies import Controller, ControllerFactory, current_user, get_db, get_event_bus, jinja_env, templates
from app.model import Room, User
from app.routers.ws_util import WsHandler
from app.util import EventBus

router = APIRouter(prefix="/room")


@router.get("/{room_code}", response_class=HTMLResponse)
async def room_root(request: Request,
                    room_code: str,
                    db: Annotated[Session, Depends(get_db)],
                    user: Annotated[User, Depends(current_user)]):
    room = db.exec(select(Room).where(Room.code == room_code, Room.owner == user)).one()
    context = {"request": request, "room": room}
    return templates.TemplateResponse("room/main.html", context)


class RoomWsHandler(WsHandler):
    def __init__(self,
                 websocket: WebSocket,
                 ctrl_factory: Annotated[ControllerFactory, Depends()],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)],
                 room_code: str):
        super().__init__(websocket, ctrl_factory, event_bus)
        self.room_code = room_code

    async def on_connect(self, ctrl: Controller) -> str:
        if session_id := self.websocket.cookies.get('session_id'):
            if user := ctrl.get_user_for_session(uuid.UUID(session_id)):
                room = ctrl.get_room(self.room_code)
                if room.owner == user:
                    return self.room_code
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    async def on_disconnect(self, ctrl: Controller):
        pass

    async def on_event(self, ctrl: Controller):
        players = ctrl.get_room_players(self.room_code)
        msg = jinja_env.get_template(f'room/dynamic_content.html').render({
            'players': players,
        })
        await self.send(msg)

    async def on_error(self, ctrl: Controller, exc: Exception):
        msg = jinja_env.get_template('room/error.html').render({'exc': exc})
        await self.send(msg)

    async def on_receive(self, ctrl: Controller, msg):
        room = ctrl.get_room(self.room_code)
        if msg['action'] == 'reject_name':
            player = ctrl.get_player(uuid.UUID(msg['player_id']))
            ctrl.set_player_name(room, player, None)


@router.websocket("/ws/{room_code}")
async def websocket_endpoint(ws_handler: Annotated[RoomWsHandler, Depends()]):
    await ws_handler.run()
