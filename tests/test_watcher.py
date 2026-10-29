from smartposti_tracker import JsonFileStore, TrackingClient, Watcher


def _watcher(session, store=None, **kw):
    received = []
    w = Watcher(client=TrackingClient(session=session), store=store,
                handlers=[lambda s, ev: received.append(ev)], **kw)
    return w, received


def test_first_check_is_silent_by_default(session):
    w, received = _watcher(session)
    assert len(w.check("A")) == 2
    assert received == []


def test_notify_on_first_check(session):
    w, received = _watcher(session, notify_on_first_check=True)
    w.check("A")
    assert len(received[0]) == 2


def test_only_new_events_reported(session):
    w, received = _watcher(session)
    w.check("A")
    session.events.append({"timestamp": "2026-10-29T04:46:01.000Z", "eventDescription": "Arrived"})
    w.check("A")
    assert [e.description for e in received[0]] == ["Arrived"]
    assert w.check("A") == []


def test_locale_change_does_not_duplicate(session):
    w, received = _watcher(session)
    w.check("A")
    for e in session.events:
        e["eventDescription"] = "translated"
    w.check("A")
    assert received == []


def test_json_store_persists(tmp_path, session):
    path = tmp_path / "state.json"
    w1, _ = _watcher(session, store=JsonFileStore(path))
    w1.check("A")
    session.events.append({"timestamp": "2026-10-29T04:46:01.000Z", "eventDescription": "Arrived"})
    w2, received = _watcher(session, store=JsonFileStore(path))
    w2.check("A")
    assert [e.description for e in received[0]] == ["Arrived"]


def test_check_all_survives_errors(session):
    w, _ = _watcher(session)
    w.check_all(["MISSING", "A"])
    assert w.store.get_seen("A")


def test_add_handler_decorator(session):
    w = Watcher(client=TrackingClient(session=session), notify_on_first_check=True)
    got = []

    @w.add_handler
    def handler(shipment, events):
        got.extend(events)

    w.check("A")
    assert len(got) == 2
