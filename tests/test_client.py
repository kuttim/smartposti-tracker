import pytest

from smartposti_tracker import APIError, ShipmentNotFound, TrackingClient


def test_get_shipment_parses_and_sorts_events(session):
    s = TrackingClient(session=session).get_shipment("ABC")
    assert s.tracking_code == "ABC"
    assert s.status == "IN_TRANSPORT"
    assert [e.description for e in s.events] == ["Info received", "The item is in sorting"]
    assert s.latest_event.description == "The item is in sorting"
    assert s.events[0].timestamp.tzinfo is not None


def test_sends_both_tokens_and_locale(session):
    TrackingClient(session=session, locale="et").get_shipment("ABC")
    _, kwargs = session.calls[-1]
    assert kwargs["headers"]["x-posti-token"].startswith("Bearer ")
    assert kwargs["headers"]["authorization"]
    assert kwargs["json"]["variables"]["locale"] == "et"


def test_token_is_cached(session):
    c = TrackingClient(session=session)
    c.get_shipment("A")
    c.get_shipment("B")
    assert len(session.token_calls()) == 1


def test_token_reset_after_403(session):
    c = TrackingClient(session=session)
    c.get_shipment("A")
    session.gql_status = 403
    with pytest.raises(APIError) as exc:
        c.get_shipment("A")
    assert exc.value.status_code == 403
    session.gql_status = 200
    c.get_shipment("A")
    assert len(session.token_calls()) == 2


def test_not_found(session):
    with pytest.raises(ShipmentNotFound):
        TrackingClient(session=session).get_shipment("MISSING")


def test_graphql_errors_raise(session):
    session.gql_payload = {"errors": [{"message": "boom"}]}
    with pytest.raises(APIError) as exc:
        TrackingClient(session=session).get_shipment("A")
    assert exc.value.errors == [{"message": "boom"}]
