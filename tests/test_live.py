import os

import pytest

from smartposti_tracker import TrackingClient

CODE = os.environ.get("SMARTPOSTI_TEST_CODE")


@pytest.mark.live
@pytest.mark.skipif(not CODE, reason="set SMARTPOSTI_TEST_CODE to run live tests")
def test_live_lookup():
    s = TrackingClient().get_shipment(CODE)
    assert s.tracking_code
    assert s.events
