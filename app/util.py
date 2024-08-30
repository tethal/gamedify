import uuid
from collections import defaultdict
from typing import Callable

Listener = Callable[[], None]


class EventBus:
    def __init__(self):
        self._listeners: dict[uuid.UUID, list[Listener]] = defaultdict(list)

    def subscribe(self, topic: uuid.UUID, listener: Listener):
        self._listeners[topic].append(listener)

    def unsubscribe(self, topic: uuid.UUID, listener: Listener):
        self._listeners[topic].remove(listener)
        if not self._listeners[topic]:
            del self._listeners[topic]

    def notify(self, topic: uuid.UUID):
        for listener in self._listeners[topic]:
            listener()
