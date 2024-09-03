from collections import defaultdict
from typing import Any, Callable

Listener = Callable[[], None]


class EventBus:
    def __init__(self):
        self._listeners: dict[Any, list[Listener]] = defaultdict(list)

    def subscribe(self, topic: Any, listener: Listener):
        self._listeners[topic].append(listener)

    def unsubscribe(self, topic: Any, listener: Listener):
        self._listeners[topic].remove(listener)
        if not self._listeners[topic]:
            del self._listeners[topic]

    def notify(self, topic: Any):
        for listener in self._listeners[topic]:
            listener()
