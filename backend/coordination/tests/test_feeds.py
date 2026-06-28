import json
from unittest.mock import patch

from django.test import TestCase

from coordination.feed_ingestion import sync_source
from coordination.models import (
    Emergency,
    FeedRecord,
    FeedSource,
    Member,
    Situation,
    hash_token,
)


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
        self.token = "feed-admin-token"
        Member.objects.create(
            situation=self.situation,
            name="Feed administrator",
            role=Member.Role.ADMIN,
            token_hash=hash_token(self.token),
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

    def test_admin_can_import_authorized_json_export(self):
        payload = {
            "source_name": "Authorized humanitarian export",
            "source_url": "https://authorized-source.example/",
            "format": "json",
            "content": json.dumps(
                {
                    "items": [
                        {
                            "external_id": "export-1",
                            "name": "José Export",
                            "status": "sin-contacto",
                            "last_seen_location": "Petare",
                            "age": 34,
                            "clothing": "Gray shirt",
                            "contact": "must-not-be-imported",
                        }
                    ]
                }
            ),
        }
        response = self.client.post(
            f"/api/situations/{self.situation.id}/imports/missing-people/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 1)
        record = FeedRecord.objects.get(source__source_url=payload["source_url"])
        self.assertEqual(record.emergency.missing_person.person_name, "José Export")
        self.assertNotIn("contact", record.raw_payload)

        repeated = self.client.post(
            f"/api/situations/{self.situation.id}/imports/missing-people/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()["unchanged"], 1)
