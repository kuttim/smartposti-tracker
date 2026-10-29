"""Detect new tracking events and dispatch them to handlers."""
from __future__ import annotations

import logging
import time
from typing import Callable, Iterable, List, Optional

from .client import TrackingClient
from .exceptions import TrackingError
from .models import Event, Shipment
from .store import MemoryStore, StateStore

log = logging.getLogger(__name__)

#: Called as ``handler(shipment, new_events)`` whenever new events appear.
EventHandler = Callable[[Shipment, List[Event]], None]


class Watcher:
    """Poll one or more shipments and call handlers for unseen events.

    :param client: a :class:`TrackingClient` (created with defaults if omitted).
    :param store: where seen event keys are kept (in-memory by default).
    :param handlers: callables invoked with ``(shipment, new_events)``.
    :param notify_on_first_check: if ``False`` (default) the first check of a
        code only records existing events as seen; handlers fire for later ones.
    """

    def __init__(
        self,
        client: Optional[TrackingClient] = None,
        store: Optional[StateStore] = None,
        handlers: Iterable[EventHandler] = (),
        notify_on_first_check: bool = False,
    ):
        self.client = client or TrackingClient()
        self.store = store or MemoryStore()
        self.handlers: List[EventHandler] = list(handlers)
        self.notify_on_first_check = notify_on_first_check

    def add_handler(self, handler: EventHandler) -> EventHandler:
        """Register a handler; usable as a decorator."""
        self.handlers.append(handler)
        return handler

    def check(self, tracking_code: str) -> List[Event]:
        """Check one shipment once and return its new events."""
        shipment = self.client.get_shipment(tracking_code)
        seen = self.store.get_seen(tracking_code)
        first_check = seen is None
        new = [e for e in shipment.events if e.key not in (seen or set())]
        self.store.set_seen(tracking_code, (e.key for e in shipment.events))
        if new and (not first_check or self.notify_on_first_check):
            for handler in self.handlers:
                handler(shipment, new)
        return new

    def check_all(self, tracking_codes: Iterable[str]) -> None:
        """Check every code; errors are logged so one bad code doesn't stop the rest."""
        for code in tracking_codes:
            try:
                self.check(code)
            except TrackingError as exc:
                log.warning("%s: %s", code, exc)

    def run(self, tracking_codes: Iterable[str], interval: float = 600) -> None:
        """Poll forever, sleeping ``interval`` seconds between rounds."""
        codes = list(tracking_codes)
        while True:
            self.check_all(codes)
            time.sleep(interval)
