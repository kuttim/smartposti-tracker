import base64
import json
import time

import pytest


def make_jwt(exp):
    def enc(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f'{enc({"alg": "none"})}.{enc({"exp": exp})}.sig'


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        import requests
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Minimal stand-in for requests.Session that serves canned responses."""

    def __init__(self, events=None, gql_status=200, gql_payload=None):
        self.events = events if events is not None else []
        self.gql_status = gql_status
        self.gql_payload = gql_payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if "anonymous_token" in url:
            exp = time.time() + 3600
            return FakeResponse(payload={
                "id_token": make_jwt(exp),
                "role_tokens": [{"type": "anonymous", "token": make_jwt(exp)}],
            })
        if self.gql_payload is not None:
            return FakeResponse(self.gql_status, self.gql_payload)
        code = kwargs["json"]["variables"]["searchTerms"]
        hits = [] if code == "MISSING" else [{
            "shipmentId": "123",
            "displayId": code,
            "status": {"main": "IN_TRANSPORT"},
            "events": list(self.events),
        }]
        return FakeResponse(self.gql_status, {"data": {"consumerSearchShipments": {"hits": hits}}})

    def token_calls(self):
        return [c for c in self.calls if "anonymous_token" in c[0]]


@pytest.fixture
def session():
    return FakeSession(events=[
        {"timestamp": "2026-10-28T16:13:19.000Z", "eventDescription": "The item is in sorting"},
        {"timestamp": "2026-10-28T13:24:30.000Z", "eventDescription": "Info received"},
    ])
