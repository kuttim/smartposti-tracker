"""HTTP client for the public Posti / SmartPosti tracking API."""
from __future__ import annotations

import base64
import json
import time
from typing import Optional, Tuple

import requests

from .exceptions import APIError, AuthError, ShipmentNotFound
from .models import Shipment

AUTH_URL = "https://auth-service.posti.fi/api/v1/anonymous_token"
GRAPHQL_URL = "https://graphql.posti.fi/graphql"
DEFAULT_ORIGIN = "https://www.smartposti.ee"
DEFAULT_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")

SHIPMENT_QUERY = """
query SearchShipments($page: Int!, $pageSize: Int!, $type: ConsumerSearchTypeFilter!,
                      $searchTerms: [String!]!, $role: ConsumerUserRoleFilter, $locale: String) {
  consumerSearchShipments(page: $page, pageSize: $pageSize, type: $type,
                          searchTerms: $searchTerms, role: $role, locale: $locale) {
    hits {
      shipmentId
      displayId
      status { main }
      events { eventDescription timestamp }
    }
  }
}
"""


def _jwt_exp(token: str) -> float:
    """Return the ``exp`` claim of a JWT without verifying it (0 if unreadable)."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return float(claims.get("exp", 0))
    except (IndexError, ValueError):
        return 0.0


class TrackingClient:
    """Fetch shipment tracking data.

    Anonymous tokens are cached and refreshed shortly before they expire.

    :param session: optional ``requests.Session`` (for proxies, retries, testing).
    :param locale: default language for event descriptions (``et``, ``en``, ``fi``, ``lv``, ``lt``).
    :param timeout: per-request timeout in seconds.
    :param query: GraphQL query to send; override to request more fields
        (the full response is always available as ``Shipment.raw``).
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        locale: str = "en",
        timeout: float = 20,
        origin: str = DEFAULT_ORIGIN,
        user_agent: str = DEFAULT_USER_AGENT,
        query: str = SHIPMENT_QUERY,
    ):
        self.session = session or requests.Session()
        self.locale = locale
        self.timeout = timeout
        self.query = query
        self._headers = {"Origin": origin, "Referer": origin + "/", "User-Agent": user_agent}
        self._tokens: Optional[Tuple[str, str]] = None
        self._tokens_exp = 0.0

    def _get_tokens(self) -> Tuple[str, str]:
        if self._tokens and time.time() < self._tokens_exp - 60:
            return self._tokens
        try:
            r = self.session.post(AUTH_URL, headers=self._headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            role_token = data["role_tokens"][0]["token"]
            id_token = data["id_token"]
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            raise AuthError(f"could not obtain anonymous token: {exc}") from exc
        self._tokens = (role_token, id_token)
        self._tokens_exp = _jwt_exp(id_token)
        return self._tokens

    def get_shipment(self, tracking_code: str, locale: Optional[str] = None) -> Shipment:
        """Return the shipment for ``tracking_code``.

        :raises ShipmentNotFound: if the code matches no shipment.
        :raises AuthError: if no token could be obtained.
        :raises APIError: on HTTP or GraphQL errors.
        """
        role_token, id_token = self._get_tokens()
        payload = {
            "operationName": "SearchShipments",
            "query": self.query,
            "variables": {
                "page": 1,
                "pageSize": 20,
                "searchTerms": tracking_code,
                "type": "PUBLIC_SHIPMENTS",
                "role": None,
                "locale": locale or self.locale,
            },
        }
        headers = {**self._headers, "authorization": role_token,
                   "x-posti-token": "Bearer " + id_token}
        try:
            r = self.session.post(GRAPHQL_URL, json=payload, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise APIError(f"request failed: {exc}") from exc
        if r.status_code in (401, 403):
            self._tokens = None  # force a fresh token next time
        if not r.ok:
            raise APIError(f"HTTP {r.status_code}", status_code=r.status_code)
        try:
            body = r.json()
        except ValueError as exc:
            raise APIError("response was not JSON", status_code=r.status_code) from exc
        if body.get("errors"):
            raise APIError("GraphQL error", status_code=r.status_code, errors=body["errors"])
        hits = (body.get("data") or {}).get("consumerSearchShipments", {}).get("hits") or []
        if not hits:
            raise ShipmentNotFound(tracking_code)
        return Shipment.from_api(hits[0])
