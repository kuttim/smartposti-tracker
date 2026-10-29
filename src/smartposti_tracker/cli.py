"""Command-line interface: ``smartposti-track``."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .client import TrackingClient
from .exceptions import TrackingError
from .models import Event, Shipment
from .store import JsonFileStore
from .watcher import Watcher


def _print_events(shipment: Shipment, events: List[Event], prefix: str = "") -> None:
    for e in events:
        print(f"{prefix}{shipment.tracking_code}  "
              f"{e.timestamp.astimezone():%Y-%m-%d %H:%M}  {e.description}", flush=True)


def _cmd_status(args: argparse.Namespace) -> int:
    client = TrackingClient(locale=args.locale)
    rc = 0
    for code in args.codes:
        try:
            s = client.get_shipment(code)
        except TrackingError as exc:
            print(f"{code}: {exc}", file=sys.stderr)
            rc = 1
            continue
        if args.json:
            print(json.dumps(s.raw, ensure_ascii=False, indent=1))
        else:
            print(f"{s.tracking_code}  status: {s.status}")
            _print_events(s, s.events, prefix="  ")
    return rc


def _cmd_watch(args: argparse.Namespace) -> int:
    def on_new(shipment: Shipment, events: List[Event]) -> None:
        _print_events(shipment, events, prefix="NEW  ")
        if args.bell:
            print("\a", end="", flush=True)

    watcher = Watcher(
        client=TrackingClient(locale=args.locale),
        store=JsonFileStore(args.state),
        handlers=[on_new],
        notify_on_first_check=args.notify_existing,
    )
    if args.once:
        watcher.check_all(args.codes)
    else:
        try:
            watcher.run(args.codes, interval=args.interval)
        except KeyboardInterrupt:
            pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartposti-track",
                                description="Track SmartPosti / Posti parcels.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--locale", default="en", help="event language: en, et, fi, lv, lt (default: en)")
    p.add_argument("-v", "--verbose", action="store_true", help="log warnings and debug info")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("status", help="show current status and all events")
    s.add_argument("codes", nargs="+", metavar="CODE")
    s.add_argument("--json", action="store_true", help="print the raw API response")
    s.set_defaults(func=_cmd_status)

    w = sub.add_parser("watch", help="poll and print only new events")
    w.add_argument("codes", nargs="+", metavar="CODE")
    w.add_argument("--interval", type=float, default=600, help="seconds between checks (default: 600)")
    w.add_argument("--once", action="store_true", help="check once and exit (for cron / Task Scheduler)")
    w.add_argument("--state", type=Path, default=Path("smartposti_state.json"),
                   help="file that remembers seen events (default: ./smartposti_state.json)")
    w.add_argument("--notify-existing", action="store_true",
                   help="also report events that already exist on the first check")
    w.add_argument("--bell", action="store_true", help="ring the terminal bell on new events")
    w.set_defaults(func=_cmd_watch)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
