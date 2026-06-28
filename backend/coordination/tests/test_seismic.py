import json
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase


class SeismicEventsTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("coordination.views.urlopen")
    def test_official_usgs_events_are_sanitized_and_cached(self, urlopen):
        upstream = MagicMock()
        upstream.read.return_value = json.dumps(
            {
                "metadata": {"generated": 1782660000000},
                "features": [
                    {
                        "id": "us-test-1",
                        "properties": {
                            "mag": 4.2,
                            "place": "20 km north of Caracas",
                            "time": 1782659000000,
                            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us-test-1",
                            "status": "reviewed",
                        },
                        "geometry": {
                            "coordinates": [-66.9, 10.5, 12.3],
                        },
                    }
                ],
            }
        ).encode()
        urlopen.return_value.__enter__.return_value = upstream

        response = self.client.get("/api/seismic-events/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "USGS Earthquake Catalog")
        self.assertEqual(response.json()["events"][0]["magnitude"], 4.2)
        self.assertEqual(response.json()["events"][0]["depth_km"], 12.3)

        cached = self.client.get("/api/seismic-events/")
        self.assertEqual(cached.status_code, 200)
        self.assertEqual(urlopen.call_count, 1)
