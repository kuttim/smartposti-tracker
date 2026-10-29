# smartposti-tracker

[![CI](https://github.com/kuttim/smartposti-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/kuttim/smartposti-tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/smartposti-tracker)](https://pypi.org/project/smartposti-tracker/)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)

An unofficial Python library and CLI for tracking **SmartPosti** (Estonia, Latvia,
Lithuania) and **Posti** (Finland) parcels. It also watches parcels and tells you
when new tracking events appear.

```text
$ smartposti-track watch JJFI12345678901234567 --interval 300
NEW  JJFI12345678901234567  2026-10-29 06:46  The item is in sorting
NEW  JJFI12345678901234567  2026-10-29 11:02  The item has arrived at the parcel locker
```

> **Disclaimer.** This project is not affiliated with or endorsed by Posti Group.
> It uses the same public endpoints as the tracking page on
> [smartposti.ee](https://www.smartposti.ee/saadetise-jalgimine), and they are not
> documented. They may change or stop working without notice. Please poll
> responsibly (every few minutes, not every second).

## Features

- **No browser needed.** Plain HTTP via `requests`, with no Selenium or Playwright.
- **Library first.** Typed `Shipment` and `Event` models, and a small exception hierarchy.
- **Watcher with pluggable parts.** You choose where seen events are stored
  (memory, JSON file, or your own store) and what happens when one arrives
  (print, Telegram, email, webhook, and so on).
- **CLI** for quick lookups, and a `--once` mode for cron or Windows Task Scheduler.
- **Localized events** in `en`, `et`, `fi`, `lv`, `lt`.

## Installation

```bash
pip install smartposti-tracker
```

For development:

```bash
git clone https://github.com/kuttim/smartposti-tracker.git
cd smartposti-tracker
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Command line

```bash
# Current status and full history
smartposti-track status JJFI12345678901234567

# Raw API response as JSON
smartposti-track status JJFI12345678901234567 --json

# Poll every 5 minutes and print only new events (Ctrl+C to stop)
smartposti-track watch CODE1 CODE2 --interval 300 --bell

# Check once and exit. Good for cron or Task Scheduler
smartposti-track watch CODE --once --state ~/.smartposti_state.json

# Events in Estonian
smartposti-track --locale et status CODE
```

`python -m smartposti_tracker ...` also works.

On the first `watch` check, existing events are only recorded, not reported.
Pass `--notify-existing` to print them too.

## Library usage

### Look up a shipment

```python
from smartposti_tracker import TrackingClient, ShipmentNotFound

client = TrackingClient(locale="en")

try:
    shipment = client.get_shipment("JJFI12345678901234567")
except ShipmentNotFound:
    print("No such parcel")
else:
    print(shipment.status)                    # "IN_TRANSPORT"
    for event in shipment.events:             # oldest first
        print(event.timestamp, event.description)
    print(shipment.latest_event)
```

`shipment.raw` and `event.raw` hold the original API data.

### Watch for new events

```python
from smartposti_tracker import JsonFileStore, Watcher

watcher = Watcher(store=JsonFileStore("state.json"))

@watcher.add_handler
def on_new_events(shipment, events):
    for e in events:
        print(f"{shipment.tracking_code}: {e.description}")

watcher.run(["JJFI12345678901234567"], interval=600)   # blocks
# or: watcher.check("CODE") -> list of new events, for your own scheduler
```

## Extending

The library has three small, replaceable pieces:

| Piece | What it does | How to replace it |
|---|---|---|
| `TrackingClient` | Talks to the API | Pass your own `requests.Session` (proxies, retries), or `query=` to request more GraphQL fields |
| `StateStore` | Remembers which events were already seen | Any object with `get_seen(code)` and `set_seen(code, keys)` |
| Event handlers | React to new events | Any callable `handler(shipment, new_events)` |

### Custom notifications

A handler is just a function. Here is one that posts to a webhook:

```python
import requests

def to_webhook(shipment, events):
    requests.post("https://example.com/hook", json={
        "code": shipment.tracking_code,
        "status": shipment.status,
        "events": [{"time": e.timestamp.isoformat(), "text": e.description} for e in events],
    })

Watcher(handlers=[to_webhook]).run(["CODE"])
```

### Custom storage

```python
class RedisStore:
    def __init__(self, redis):
        self.r = redis

    def get_seen(self, code):
        # Return None if this code was never checked, so the first check stays silent
        if not self.r.exists(f"seen:{code}"):
            return None
        return {k.decode() for k in self.r.smembers(f"seen:{code}")}

    def set_seen(self, code, keys):
        pipe = self.r.pipeline()
        pipe.delete(f"seen:{code}")
        pipe.sadd(f"seen:{code}", "__checked__", *keys)
        pipe.execute()
```

### Retries and proxies

```python
import requests
from requests.adapters import HTTPAdapter, Retry

session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2)))
client = TrackingClient(session=session)
```

### Requesting more fields

The default query asks only for status and events. To get delivery details,
pickup point, and similar data, pass your own GraphQL query that still returns
`consumerSearchShipments.hits`, then read the extra fields from `shipment.raw`.

See [`examples/`](examples/) for complete scripts, including a
[Telegram notifier](examples/telegram_notify.py) and a
[SQLite store](examples/sqlite_store.py).

## Running on a schedule

**Linux/macOS (cron), every 10 minutes:**

```cron
*/10 * * * * smartposti-track watch CODE --once --state $HOME/.smartposti_state.json >> $HOME/parcels.log
```

**Windows (Task Scheduler):**

```powershell
schtasks /Create /SC MINUTE /MO 10 /TN "Parcel tracker" `
  /TR "smartposti-track watch CODE --once --state %USERPROFILE%\smartposti_state.json"
```

## How it works

The smartposti.ee tracking page loads its data in the browser in two steps.
This library repeats those two requests:

1. `POST https://auth-service.posti.fi/api/v1/anonymous_token` returns a short-lived
   anonymous `id_token` and a `role_tokens[0].token`. No account is needed.
2. `POST https://graphql.posti.fi/graphql` runs the `consumerSearchShipments` query,
   with `authorization: <role token>` and `x-posti-token: Bearer <id_token>`.

Tokens are cached until shortly before they expire. A 401 or 403 response
causes a fresh token on the next call.

If Posti changes this flow, open the tracking page with your browser's dev tools
open (Network tab, filter `graphql`) to see the new requests, then
[open an issue](https://github.com/kuttim/smartposti-tracker/issues).

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest                                         # offline, API is mocked
SMARTPOSTI_TEST_CODE=<code> pytest -m live     # optional real-API smoke test
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
