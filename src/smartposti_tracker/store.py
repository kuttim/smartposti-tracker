"""Persistence for "already seen" event keys.

Implement :class:`StateStore` to keep state somewhere else (Redis, SQLite, ...).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Protocol, Set, Union


class StateStore(Protocol):
    def get_seen(self, tracking_code: str) -> Optional[Set[str]]:
        """Return seen event keys, or ``None`` if the code was never checked."""

    def set_seen(self, tracking_code: str, keys: Iterable[str]) -> None:
        """Replace the seen event keys for ``tracking_code``."""


class MemoryStore:
    """In-process store; state is lost when the process exits."""

    def __init__(self) -> None:
        self._data: Dict[str, Set[str]] = {}

    def get_seen(self, tracking_code: str) -> Optional[Set[str]]:
        seen = self._data.get(tracking_code)
        return set(seen) if seen is not None else None

    def set_seen(self, tracking_code: str, keys: Iterable[str]) -> None:
        self._data[tracking_code] = set(keys)


class JsonFileStore:
    """Store state in a JSON file, written on every update."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    def _load(self) -> Dict[str, list]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get_seen(self, tracking_code: str) -> Optional[Set[str]]:
        seen = self._load().get(tracking_code)
        return set(seen) if seen is not None else None

    def set_seen(self, tracking_code: str, keys: Iterable[str]) -> None:
        data = self._load()
        data[tracking_code] = sorted(keys)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(self.path)
