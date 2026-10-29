"""Typed views of the tracking API response."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Event:
    """A single tracking event, e.g. "The item is in sorting"."""

    timestamp: datetime
    description: str
    raw: Dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @property
    def key(self) -> str:
        """Stable, locale-independent identifier used for de-duplication."""
        return self.raw.get("timestamp") or self.timestamp.isoformat()

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            timestamp=_parse_ts(data["timestamp"]),
            description=data.get("eventDescription") or "",
            raw=data,
        )


@dataclass(frozen=True)
class Shipment:
    """A tracked shipment and its events, ordered oldest first."""

    tracking_code: str
    shipment_id: str
    status: Optional[str]
    events: List[Event]
    raw: Dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @property
    def latest_event(self) -> Optional[Event]:
        return self.events[-1] if self.events else None

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Shipment":
        events = sorted(
            (Event.from_api(e) for e in data.get("events") or []),
            key=lambda e: e.timestamp,
        )
        return cls(
            tracking_code=data.get("displayId") or "",
            shipment_id=data.get("shipmentId") or "",
            status=(data.get("status") or {}).get("main"),
            events=events,
            raw=data,
        )
