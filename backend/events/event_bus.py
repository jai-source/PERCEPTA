import asyncio
from typing import Callable, Dict, List, Union, Awaitable
from .event_types import PerceptualEvent, EventType, Modality
import logging

logger = logging.getLogger(__name__)

EventHandler = Callable[[PerceptualEvent], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._subscribers: Dict[Union[EventType, Modality, str], List[EventHandler]] = {}
        self._all_events_subscribers: List[EventHandler] = []
        self._history: List[PerceptualEvent] = []
        self.max_history: int = 1000

    def subscribe(self, topic: Union[EventType, Modality, str], handler: EventHandler):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to topic: {topic}")

    def subscribe_all(self, handler: EventHandler):
        self._all_events_subscribers.append(handler)
        logger.debug("Subscribed to all events")

    async def publish(self, event: PerceptualEvent):
        # Store in history
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history.pop(0)

        handlers = []
        
        # Topic matches
        for topic in [event.event_type, event.modality, event.source]:
            if topic in self._subscribers:
                handlers.extend(self._subscribers[topic])
                
        # All events subscribers
        handlers.extend(self._all_events_subscribers)
        
        # Deduplicate handlers (maintain list order)
        unique_handlers = []
        for h in handlers:
            if h not in unique_handlers:
                unique_handlers.append(h)
        
        if unique_handlers:
            tasks = [asyncio.create_task(handler(event)) for handler in unique_handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(self, limit: int = 100) -> List[PerceptualEvent]:
        return self._history[-limit:]
