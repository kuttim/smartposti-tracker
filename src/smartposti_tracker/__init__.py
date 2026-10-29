"""Unofficial client for SmartPosti / Posti parcel tracking."""

__version__ = "0.1.0"

from .client import TrackingClient
from .exceptions import APIError, AuthError, ShipmentNotFound, TrackingError
from .models import Event, Shipment
from .store import JsonFileStore, MemoryStore, StateStore
from .watcher import EventHandler, Watcher

__all__ = [
    "TrackingClient",
    "Watcher",
    "EventHandler",
    "Shipment",
    "Event",
    "StateStore",
    "MemoryStore",
    "JsonFileStore",
    "TrackingError",
    "AuthError",
    "APIError",
    "ShipmentNotFound",
]
