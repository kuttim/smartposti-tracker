"""A custom StateStore backed by SQLite: implement get_seen / set_seen."""
import sqlite3
import sys

from smartposti_tracker import Watcher


class SQLiteStore:
    def __init__(self, path="smartposti.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (code TEXT, event_key TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS checked (code TEXT PRIMARY KEY)")

    def get_seen(self, code):
        if not self.db.execute("SELECT 1 FROM checked WHERE code = ?", (code,)).fetchone():
            return None
        return {row[0] for row in self.db.execute("SELECT event_key FROM seen WHERE code = ?", (code,))}

    def set_seen(self, code, keys):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO checked VALUES (?)", (code,))
            self.db.execute("DELETE FROM seen WHERE code = ?", (code,))
            self.db.executemany("INSERT INTO seen VALUES (?, ?)", [(code, k) for k in keys])


watcher = Watcher(store=SQLiteStore(), handlers=[
    lambda shipment, events: [print("NEW", shipment.tracking_code, e.description) for e in events]
])
watcher.check_all(sys.argv[1:])
