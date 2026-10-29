"""Print a shipment's current status and history."""
import sys

from smartposti_tracker import TrackingClient

code = sys.argv[1]  # e.g. python examples/basic_lookup.py YOUR_TRACKING_CODE
shipment = TrackingClient(locale="en").get_shipment(code)

print(shipment.tracking_code, shipment.status)
for event in shipment.events:
    print(f"  {event.timestamp:%Y-%m-%d %H:%M}  {event.description}")
