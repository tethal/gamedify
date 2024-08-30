import asyncio
import json
import uuid
from typing import Annotated

from fastapi import Depends, WebSocket, WebSocketDisconnect

from app.ctrl import Controller, ControllerFactory
from app.dependencies import get_event_bus
from app.util import EventBus


class WsHandler:
    def __init__(self,
                 websocket: WebSocket,
                 ctrl_factory: Annotated[ControllerFactory, Depends()],
                 event_bus: Annotated[EventBus, Depends(get_event_bus)]):
        self.websocket = websocket
        self.ctrl_factory = ctrl_factory
        self.event_bus = event_bus
        self.event = asyncio.Event()
        self.event.set()

    async def on_connect(self, ctrl: Controller) -> uuid.UUID:
        pass

    async def on_disconnect(self, ctrl: Controller):
        pass

    async def on_error(self, ctrl: Controller, exc: Exception):
        pass

    async def on_event(self, ctrl: Controller):
        pass

    async def on_receive(self, ctrl: Controller, msg):
        pass

    async def send(self, msg: str):
        await self.websocket.send_text(msg)

    async def _dispatch_loop(self):
        while True:
            await self.event.wait()
            self.event.clear()
            with self.ctrl_factory() as ctrl:
                try:
                    await self.on_event(ctrl)
                except Exception as exc:
                    await self.on_error(ctrl, exc)

    async def _receive_loop(self):
        while True:
            msg = await self.websocket.receive_text()
            with self.ctrl_factory() as ctrl:
                try:
                    await self.on_receive(ctrl, json.loads(msg))
                except Exception as exc:
                    await self.on_error(ctrl, exc)

    async def run(self):
        with self.ctrl_factory() as ctrl:
            try:
                topic = await self.on_connect(ctrl)
            except Exception as exc:
                await self.on_error(ctrl, exc)
                await self.websocket.close()
                return

        await self.websocket.accept()
        self.event_bus.subscribe(topic, self.event.set)
        task = asyncio.create_task(self._dispatch_loop())
        try:
            await self._receive_loop()
        except WebSocketDisconnect:
            # consume the exception to avoid log noise
            pass
        finally:
            task.cancel()
            self.event_bus.unsubscribe(topic, self.event.set)

            with self.ctrl_factory() as ctrl:
                try:
                    await self.on_disconnect(ctrl)
                except Exception as exc:
                    await self.on_error(ctrl, exc)
