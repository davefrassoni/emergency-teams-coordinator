from unittest.mock import patch

from django.test import TestCase

from coordination.models import WorldEvent
from coordination.world_events import (
    sync_eonet,
    sync_gdacs,
    sync_usgs_global,
    sync_world_events,
)


GDACS_PAYLOAD = {
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-76.2422, 4.8436]},
            "properties": {
                "eventtype": "EQ",
                "eventid": 1557236,
                "name": "Earthquake in Colombia",
                "description": "Earthquake in Colombia",
                "alertlevel": "Orange",
                "country": "Colombia",
                "fromdate": "2026-08-10T12:34:28",
                "todate": "2026-08-10T12:34:28",
                "severitydata": {
                    "severity": 7.4,
                    "severitytext": "Magnitude 7.4M, Depth:110.285km",
                    "severityunit": "M",
                },
                "url": {
                    "report": "https://www.gdacs.org/report.aspx?eventid=1557236"
                },
            },
        }
    ]
}

USGS_PAYLOAD = {
    "features": [
        {
            "id": "us7000abcd",
            "properties": {
                "mag": 6.8,
                "place": "120 km SW of Ferndale, CA",
                "title": "M 6.8 - 120 km SW of Ferndale, CA",
                "time": 1782659000000,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd",
            },
            "geometry": {"coordinates": [-125.9, 40.2, 10.0]},
        }
    ]
}

EONET_PAYLOAD = {
    "events": [
        {
            "id": "EONET_22430",
            "title": "Wildfire Harris, Rosebud, Montana",
            "description": "30 Miles SW from Ashland, MT",
            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_22430",
            "closed": None,
            "categories": [{"id": "wildfires", "title": "Wildfires"}],
            "sources": [{"id": "IRWIN", "url": "https://irwin.doi.gov/x"}],
            "geometry": [
                {
                    "magnitudeValue": 924.30,
                    "magnitudeUnit": "acres",
                    "date": "2026-08-09T16:55:00Z",
                    "type": "Point",
                    "coordinates": [-106.634317, 45.195183],
                }
            ],
        }
    ]
}


class WorldEventsSyncTests(TestCase):
    @patch("coordination.world_events._json_request", return_value=GDACS_PAYLOAD)
    def test_sync_gdacs_creates_and_updates(self, _request):
        totals = sync_gdacs()
        self.assertEqual(totals, {"created": 1, "updated": 0})
        event = WorldEvent.objects.get(source=WorldEvent.Source.GDACS)
        self.assertEqual(event.event_type, WorldEvent.EventType.EARTHQUAKE)
        self.assertEqual(event.alert_level, WorldEvent.AlertLevel.ORANGE)
        self.assertEqual(event.country, "Colombia")
        self.assertAlmostEqual(float(event.latitude), 4.8436)
        self.assertAlmostEqual(float(event.longitude), -76.2422)
        self.assertEqual(event.severity_value, 7.4)

        totals_again = sync_gdacs()
        self.assertEqual(totals_again, {"created": 0, "updated": 1})
        self.assertEqual(WorldEvent.objects.count(), 1)

    @patch("coordination.world_events._json_request", return_value=USGS_PAYLOAD)
    def test_sync_usgs_global_assigns_alert_level_by_magnitude(self, _request):
        totals = sync_usgs_global()
        self.assertEqual(totals, {"created": 1, "updated": 0})
        event = WorldEvent.objects.get(source=WorldEvent.Source.USGS)
        self.assertEqual(event.event_type, WorldEvent.EventType.EARTHQUAKE)
        self.assertEqual(event.alert_level, WorldEvent.AlertLevel.RED)
        self.assertEqual(event.severity_value, 6.8)

    @patch("coordination.world_events._json_request", return_value=EONET_PAYLOAD)
    def test_sync_eonet_maps_category_and_point_geometry(self, _request):
        totals = sync_eonet()
        self.assertEqual(totals, {"created": 1, "updated": 0})
        event = WorldEvent.objects.get(source=WorldEvent.Source.EONET)
        self.assertEqual(event.event_type, WorldEvent.EventType.WILDFIRE)
        self.assertTrue(event.is_active)
        self.assertAlmostEqual(float(event.longitude), -106.634317)
        self.assertAlmostEqual(float(event.latitude), 45.195183)
        self.assertEqual(event.severity_unit, "acres")

    def test_sync_world_events_isolates_per_source_failures(self):
        with patch(
            "coordination.world_events.sync_gdacs", return_value={"created": 1, "updated": 0}
        ), patch(
            "coordination.world_events.sync_usgs_global", side_effect=RuntimeError("boom")
        ), patch(
            "coordination.world_events.sync_eonet", return_value={"created": 2, "updated": 0}
        ):
            results = sync_world_events()
        self.assertTrue(results["gdacs"]["ok"])
        self.assertFalse(results["usgs"]["ok"])
        self.assertIn("boom", results["usgs"]["error"])
        self.assertTrue(results["eonet"]["ok"])

    @patch("coordination.world_events._json_request", return_value=GDACS_PAYLOAD)
    def test_world_events_endpoint_returns_active_events(self, _request):
        sync_gdacs()
        response = self.client.get("/api/world/events/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["source"], "GDACS")
        self.assertEqual(body[0]["event_type"], "EARTHQUAKE")
