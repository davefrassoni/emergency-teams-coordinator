from unittest.mock import patch

from django.test import TestCase

from coordination.feed_ingestion import sync_source
from coordination.models import Emergency, FeedRecord, FeedSource, Situation


class FeedIngestionTests(TestCase):
    def setUp(self):
        self.situation = Situation.objects.create(
            name="Venezuela Response",
            codename="venezuela",
            location="Venezuela",
        )
        self.source = FeedSource.objects.create(
            situation=self.situation,
            name="Authorized missing people feed",
            source_url="https://source.example/",
            api_url="https://api.source.example/api",
            adapter=FeedSource.Adapter.VENEZUELA_MISSING,
            enabled=True,
        )

    @patch("coordination.feed_ingestion._json_request")
    def test_feed_is_deduplicated_sanitized_and_provenance_linked(self, request):
        request.return_value = {
            "items": [
                {
                    "id": "person-1",
                    "nombre": "María Feed",
                    "estado": "sin-contacto",
                    "ubicacion": "Chacao",
                    "descripcion": "Dark hair",
                    "vestimenta": "Blue coat",
                    "contacto": "must-not-be-copied",
                    "cedula": "private-id",
                    "latitud": 10.49,
                    "longitud": -66.85,
                }
            ],
            "totalPages": 1,
        }
        first = sync_source(self.source)
        self.assertEqual(first["created"], 1)
        emergency = Emergency.objects.get()
        self.assertEqual(emergency.source, Emergency.Source.EXTERNAL_FEED)
        self.assertEqual(emergency.missing_person.person_name, "María Feed")
        record = FeedRecord.objects.get()
        self.assertNotIn("contacto", record.raw_payload)
        self.assertNotIn("cedula", record.raw_payload)
        self.assertEqual(record.emergency, emergency)

        second = sync_source(self.source)
        self.assertEqual(second["unchanged"], 1)
        self.assertEqual(Emergency.objects.count(), 1)

        request.return_value["items"][0]["estado"] = "localizado"
        updated = sync_source(self.source)
        self.assertEqual(updated["updated"], 1)
        emergency.refresh_from_db()
        self.assertEqual(emergency.status, Emergency.Status.RESOLVED)

