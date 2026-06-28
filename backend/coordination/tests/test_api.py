import re

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from coordination.models import Assignment, Emergency, Member, Team, hash_token


@override_settings(FRONTEND_URL="http://testserver")
class CoordinationApiTests(APITestCase):
    def create_situation(self, public=True):
        response = self.client.post(
            "/api/situations/",
            {
                "name": "Central District Response",
                "codename": "central-response",
                "location": "Caracas",
                "description": "Major earthquake response",
                "creator_name": "Ana Coordinator",
                "creator_contact": "ana@example.org",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertFalse(created["situation"]["is_public"])
        self.assertFalse(created["situation"]["public_reporting_enabled"])
        if public:
            published = self.client.patch(
                f"/api/situations/{created['situation']['id']}/",
                {"is_public": True, "public_reporting_enabled": True},
                format="json",
                **self.auth(created["access_token"]),
            )
            self.assertEqual(published.status_code, 200)
            created["situation"] = published.json()
        return created

    def auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_creation_is_private_and_admin_can_publish_it(self):
        created = self.create_situation(public=False)
        situation_id = created["situation"]["id"]

        denied = self.client.get(f"/api/situations/{situation_id}/dashboard/")
        self.assertEqual(denied.status_code, 401)

        dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/",
            **self.auth(created["access_token"]),
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["member"]["role"], "ADMIN")
        self.assertNotIn("token", str(dashboard.json()).lower())

        alias = self.client.get("/api/situations/central-response/public/")
        self.assertEqual(alias.status_code, 401)
        private_alias = self.client.get(
            "/api/situations/central-response/public/",
            **self.auth(created["access_token"]),
        )
        self.assertEqual(private_alias.status_code, 200)

        published = self.client.patch(
            f"/api/situations/{situation_id}/",
            {"is_public": True},
            format="json",
            **self.auth(created["access_token"]),
        )
        self.assertEqual(published.status_code, 200)
        self.assertTrue(published.json()["is_public"])
        alias = self.client.get("/api/situations/central-response/public/")
        self.assertEqual(alias.status_code, 200)
        self.assertEqual(alias.json()["situation"]["id"], situation_id)
        denied_report = self.client.post(
            f"/api/situations/{situation_id}/public/",
            {
                "title": "Unverified event",
                "location": "Public square",
                "latitude": 10.5,
                "longitude": -66.9,
            },
            format="json",
        )
        self.assertEqual(denied_report.status_code, 403)
        popular = self.client.get("/api/situations/public/")
        self.assertEqual(popular.status_code, 200)
        self.assertEqual(popular.json()[0]["id"], situation_id)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_passwordless_admin_login_creates_second_device_access(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        requested = self.client.post(
            "/api/auth/request-link/",
            {"codename": "central-response", "email": "ana@example.org"},
            format="json",
        )
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"/login/([A-Za-z0-9_-]+)", mail.outbox[0].body)
        self.assertIsNotNone(match)

        confirmed = self.client.post(
            f"/api/auth/confirm/{match.group(1)}/",
            {},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        second_token = confirmed.json()["access_token"]
        dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/",
            **self.auth(second_token),
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["member"]["role"], "ADMIN")

        reused = self.client.post(
            f"/api/auth/confirm/{match.group(1)}/",
            {},
            format="json",
        )
        self.assertEqual(reused.status_code, 410)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FEATURE_REQUEST_EMAIL="david.frassoni@gmail.com",
    )
    def test_feature_request_requires_email_and_sends_internal_message(self):
        invalid = self.client.post(
            "/api/feature-requests/",
            {"contact_email": "not-an-email", "message": "Please add offline mode"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        sent = self.client.post(
            "/api/feature-requests/",
            {
                "contact_email": "responder@example.org",
                "message": "Please add offline mode for disconnected field teams.",
                "page_url": "https://example.org/venezuela",
                "locale": "es",
            },
            format="json",
        )
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(mail.outbox[-1].to, ["david.frassoni@gmail.com"])
        self.assertEqual(mail.outbox[-1].reply_to, ["responder@example.org"])

    def test_one_time_invite_and_viewer_permissions(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        admin_token = created["access_token"]

        invited = self.client.post(
            f"/api/situations/{situation_id}/invitations/",
            {"role": "VIEWER", "intended_for": "Observer"},
            format="json",
            **self.auth(admin_token),
        )
        self.assertEqual(invited.status_code, 201)
        invite_token = invited.json()["invite_url"].rsplit("/", 1)[-1]

        accepted = self.client.post(
            f"/api/invitations/{invite_token}/",
            {"name": "Observer", "contact": "radio 2"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 201)
        viewer_token = accepted.json()["access_token"]

        reused = self.client.post(
            f"/api/invitations/{invite_token}/",
            {"name": "Another person"},
            format="json",
        )
        self.assertEqual(reused.status_code, 410)

        forbidden = self.client.post(
            f"/api/situations/{situation_id}/teams/",
            {
                "name": "Unauthorized team",
                "specialty": "MEDICAL",
                "people_count": 2,
            },
            format="json",
            **self.auth(viewer_token),
        )
        self.assertEqual(forbidden.status_code, 403)

        readable = self.client.get(
            f"/api/situations/{situation_id}/dashboard/",
            **self.auth(viewer_token),
        )
        self.assertEqual(readable.status_code, 200)

    def test_dispatch_lifecycle_and_double_deployment_protection(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        token = created["access_token"]
        auth = self.auth(token)

        team_response = self.client.post(
            f"/api/situations/{situation_id}/teams/",
            {
                "name": "Rescue Alpha",
                "organization": "International USAR",
                "specialty": "SEARCH_RESCUE",
                "people_count": 8,
            },
            format="json",
            **auth,
        )
        self.assertEqual(team_response.status_code, 201)
        team_id = team_response.json()["id"]

        emergency_payload = {
            "title": "Collapsed apartment block",
            "location": "Av. Libertador",
            "triage": "RED",
            "people_affected": 20,
            "people_trapped": 7,
            "hazards": "Unstable concrete",
        }
        first = self.client.post(
            f"/api/situations/{situation_id}/emergencies/",
            emergency_payload,
            format="json",
            **auth,
        )
        self.assertEqual(first.status_code, 201)
        first_id = first.json()["id"]

        second = self.client.post(
            f"/api/situations/{situation_id}/emergencies/",
            {**emergency_payload, "title": "Collapsed school", "location": "La Pastora"},
            format="json",
            **auth,
        )
        second_id = second.json()["id"]

        assigned = self.client.post(
            f"/api/situations/{situation_id}/emergencies/{first_id}/assignment/",
            {"team_id": team_id},
            format="json",
            **auth,
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["status"], Emergency.Status.IN_PROGRESS)
        self.assertEqual(len(assigned.json()["assignments"]), 1)
        self.assertEqual(Team.objects.get(pk=team_id).status, Team.Status.DEPLOYED)

        duplicate = self.client.post(
            f"/api/situations/{situation_id}/emergencies/{second_id}/assignment/",
            {"team_id": team_id},
            format="json",
            **auth,
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Assignment.objects.filter(released_at__isnull=True).count(), 1)

        released = self.client.delete(
            f"/api/situations/{situation_id}/emergencies/{first_id}/assignment/",
            {"team_id": team_id},
            format="json",
            **auth,
        )
        self.assertEqual(released.status_code, 200)
        self.assertEqual(Team.objects.get(pk=team_id).status, Team.Status.AVAILABLE)

        reassigned = self.client.post(
            f"/api/situations/{situation_id}/emergencies/{second_id}/assignment/",
            {"team_id": team_id},
            format="json",
            **auth,
        )
        self.assertEqual(reassigned.status_code, 200)

        dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/", **auth
        ).json()
        self.assertEqual(dashboard["summary"]["open_emergencies"], 2)
        self.assertEqual(dashboard["summary"]["immediate_emergencies"], 2)
        self.assertEqual(dashboard["summary"]["people_trapped"], 14)
        self.assertGreaterEqual(len(dashboard["activity"]), 7)

    def test_non_admin_cannot_create_invitations(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        coordinator_token = "coordinator-access-token"
        member = Member.objects.create(
            situation_id=situation_id,
            name="Field coordinator",
            role=Member.Role.COORDINATOR,
            token_hash=hash_token(coordinator_token),
        )
        self.assertIsNotNone(member.pk)

        response = self.client.post(
            f"/api/situations/{situation_id}/invitations/",
            {"role": "COORDINATOR"},
            format="json",
            **self.auth(coordinator_token),
        )
        self.assertEqual(response.status_code, 403)

    def test_public_can_report_but_cannot_triage_or_see_private_data(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]

        report = self.client.post(
            f"/api/situations/{situation_id}/public/",
            {
                "title": "Damaged building",
                "location": "Plaza Venezuela",
                "latitude": 10.499,
                "longitude": -66.89,
                "triage": "RED",
                "people_trapped": 3,
                "incident_type": "STRUCTURAL",
                "damage_level": "COLLAPSE",
                "construction_type": "Residential tower",
                "evidence_url": "https://evidence.example/collapse-photo",
                "details": "Caller is sheltering nearby",
                "reporter_name": "Public caller",
                "reporter_contact": "+58 private",
            },
            format="json",
        )
        self.assertEqual(report.status_code, 201)
        emergency = Emergency.objects.get(pk=report.json()["emergency"]["id"])
        self.assertEqual(emergency.source, Emergency.Source.PUBLIC)
        self.assertEqual(emergency.triage, Emergency.Triage.UNKNOWN)
        self.assertEqual(emergency.status, Emergency.Status.REPORTED)
        self.assertEqual(emergency.incident_type, Emergency.IncidentType.STRUCTURAL)
        self.assertEqual(emergency.damage_level, Emergency.DamageLevel.COLLAPSE)
        self.assertIsNone(emergency.created_by)

        public_map = self.client.get(
            f"/api/situations/{situation_id}/public/"
        )
        self.assertEqual(public_map.status_code, 200)
        public_item = public_map.json()["emergencies"][0]
        self.assertNotIn("details", public_item)
        self.assertNotIn("reporter_name", public_item)
        self.assertNotIn("reporter_contact", public_item)
        self.assertNotIn("assignments", public_item)
        self.assertNotIn("evidence_url", public_item)
        self.assertEqual(public_item["damage_level"], "COLLAPSE")
        self.assertNotIn("teams", public_map.json())

        private_dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/",
            **self.auth(created["access_token"]),
        )
        self.assertEqual(private_dashboard.status_code, 200)
        self.assertEqual(
            private_dashboard.json()["emergencies"][0]["source"],
            Emergency.Source.PUBLIC,
        )
        self.assertEqual(
            private_dashboard.json()["emergencies"][0]["evidence_url"],
            "https://evidence.example/collapse-photo",
        )

        changes = self.client.get(
            f"/api/situations/{situation_id}/changes/?since=0&wait=1"
        )
        self.assertEqual(changes.status_code, 200)
        self.assertTrue(changes.json()["changed"])

    def test_admin_manages_verified_public_emergency_contacts(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        token = created["access_token"]
        public_contact = self.client.post(
            f"/api/situations/{situation_id}/contacts/",
            {
                "label": "Municipal fire department",
                "phone": "171",
                "category": "FIRE",
                "notes": "Central district",
                "is_public": True,
                "priority": 1,
            },
            format="json",
            **self.auth(token),
        )
        self.assertEqual(public_contact.status_code, 201)
        private_contact = self.client.post(
            f"/api/situations/{situation_id}/contacts/",
            {
                "label": "Coordinator radio",
                "phone": "555-0100",
                "category": "OTHER",
                "is_public": False,
            },
            format="json",
            **self.auth(token),
        )
        self.assertEqual(private_contact.status_code, 201)

        public_map = self.client.get(f"/api/situations/{situation_id}/public/")
        self.assertEqual(public_map.status_code, 200)
        self.assertEqual(
            [item["label"] for item in public_map.json()["emergency_contacts"]],
            ["Municipal fire department"],
        )
        dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/",
            **self.auth(token),
        )
        self.assertEqual(len(dashboard.json()["emergency_contacts"]), 2)

        deleted = self.client.delete(
            f"/api/situations/{situation_id}/contacts/{public_contact.json()['id']}/",
            **self.auth(token),
        )
        self.assertEqual(deleted.status_code, 204)

    def test_trapped_people_report_requires_private_contact(self):
        created = self.create_situation()
        denied = self.client.post(
            f"/api/situations/{created['situation']['id']}/public/",
            {
                "title": "People may be trapped",
                "location": "Damaged building",
                "latitude": 10.5,
                "longitude": -66.9,
                "people_trapped": 2,
            },
            format="json",
        )
        self.assertEqual(denied.status_code, 400)

    def test_admin_can_make_operation_private(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        token = created["access_token"]
        closed = self.client.patch(
            f"/api/situations/{situation_id}/",
            {"is_public": False},
            format="json",
            **self.auth(token),
        )
        self.assertEqual(closed.status_code, 200)
        self.assertFalse(closed.json()["is_public"])
        self.assertFalse(closed.json()["public_reporting_enabled"])

        public_map = self.client.get(
            f"/api/situations/{situation_id}/public/"
        )
        self.assertEqual(public_map.status_code, 401)
        popular = self.client.get("/api/situations/public/")
        self.assertEqual(popular.status_code, 200)
        self.assertEqual(popular.json(), [])
        anonymous_poll = self.client.get(
            f"/api/situations/{situation_id}/changes/?since=0&wait=1"
        )
        self.assertEqual(anonymous_poll.status_code, 401)
        member_poll = self.client.get(
            f"/api/situations/{situation_id}/changes/?since=0&wait=1",
            **self.auth(token),
        )
        self.assertEqual(member_poll.status_code, 200)

    def test_public_supply_request_partial_fulfillment_and_private_tracking(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        supply = self.client.post(
            f"/api/situations/{situation_id}/public/supplies/",
            {
                "title": "Shelter supplies",
                "delivery_location": "Community Center, Chacao",
                "latitude": 10.495,
                "longitude": -66.853,
                "details": "For displaced families",
                "requester_name": "Shelter lead",
                "requester_contact": "+58 private",
                "items": [
                    {"name": "Mattresses", "quantity": 5, "unit": "UNIT"},
                    {"name": "Drinking water", "quantity": 20, "unit": "LITER"},
                ],
            },
            format="json",
        )
        self.assertEqual(supply.status_code, 201)
        supply_request = supply.json()["supply_request"]
        supply_id = supply_request["id"]
        mattress = next(item for item in supply_request["items"] if item["name"] == "Mattresses")
        water = next(item for item in supply_request["items"] if item["name"] == "Drinking water")

        contribution = self.client.post(
            f"/api/situations/{situation_id}/public/supplies/{supply_id}/commitments/",
            {
                "contributor_name": "Neighbors Network",
                "contributor_contact": "private@example.org",
                "origin_location": "La Castellana warehouse",
                "estimated_arrival": "2026-06-27T18:30:00Z",
                "items": [
                    {"item_id": mattress["id"], "quantity": 2},
                    {"item_id": water["id"], "quantity": 10},
                ],
            },
            format="json",
        )
        self.assertEqual(contribution.status_code, 201)
        tracker = contribution.json()
        commitment_id = tracker["commitment"]["id"]
        self.assertTrue(tracker["tracking_token"])

        overcommit = self.client.post(
            f"/api/situations/{situation_id}/public/supplies/{supply_id}/commitments/",
            {
                "contributor_name": "Too much",
                "items": [{"item_id": water["id"], "quantity": 11}],
            },
            format="json",
        )
        self.assertEqual(overcommit.status_code, 400)

        public_map = self.client.get(
            f"/api/situations/{situation_id}/public/"
        ).json()
        request_data = public_map["supply_requests"][0]
        self.assertEqual(request_data["status"], "PARTIAL")
        water_data = next(item for item in request_data["items"] if item["name"] == "Drinking water")
        self.assertEqual(water_data["remaining_quantity"], 10.0)
        self.assertNotIn("requester_contact", request_data)
        self.assertNotIn("contributor_contact", request_data["commitments"][0])

        denied = self.client.patch(
            f"/api/situations/{situation_id}/public/commitments/{commitment_id}/",
            {"status": "IN_TRANSIT"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        tracked = self.client.patch(
            f"/api/situations/{situation_id}/public/commitments/{commitment_id}/",
            {
                "status": "IN_TRANSIT",
                "current_location": "Av. Francisco de Miranda",
                "current_latitude": 10.49,
                "current_longitude": -66.86,
                "share_live_location": True,
            },
            format="json",
            HTTP_X_SUPPLY_TOKEN=tracker["tracking_token"],
        )
        self.assertEqual(tracked.status_code, 200)
        self.assertEqual(tracked.json()["commitment"]["status"], "IN_TRANSIT")
        self.assertEqual(
            tracked.json()["commitment"]["current_location"],
            "Av. Francisco de Miranda",
        )

        updated_public = self.client.get(
            f"/api/situations/{situation_id}/public/"
        ).json()
        public_commitment = updated_public["supply_requests"][0]["commitments"][0]
        self.assertEqual(public_commitment["current_latitude"], 10.49)
        self.assertNotIn("tracking_token", str(updated_public))

        completes_request = self.client.post(
            f"/api/situations/{situation_id}/public/supplies/{supply_id}/commitments/",
            {
                "contributor_name": "Second delivery",
                "items": [
                    {"item_id": mattress["id"], "quantity": 3},
                    {"item_id": water["id"], "quantity": 10},
                ],
            },
            format="json",
        )
        self.assertEqual(completes_request.status_code, 201)
        complete_tracker = completes_request.json()
        covered = self.client.get(
            f"/api/situations/{situation_id}/public/"
        ).json()["supply_requests"][0]
        self.assertEqual(covered["status"], "COVERED")

        cancelled = self.client.patch(
            (
                f"/api/situations/{situation_id}/public/commitments/"
                f"{complete_tracker['commitment']['id']}/"
            ),
            {"status": "CANCELLED"},
            format="json",
            HTTP_X_SUPPLY_TOKEN=complete_tracker["tracking_token"],
        )
        self.assertEqual(cancelled.status_code, 200)
        reopened = self.client.get(
            f"/api/situations/{situation_id}/public/"
        ).json()["supply_requests"][0]
        self.assertEqual(reopened["status"], "PARTIAL")

    def test_public_missing_person_report_can_be_assigned_to_rescue_team(self):
        created = self.create_situation()
        situation_id = created["situation"]["id"]
        token = created["access_token"]
        auth = self.auth(token)

        reported = self.client.post(
            f"/api/situations/{situation_id}/public/missing-people/",
            {
                "person_name": "María Example",
                "approximate_age": 34,
                "physical_description": "Medium height, dark hair",
                "clothing": "Blue jacket and black trousers",
                "circumstances": "Separated from family after evacuation",
                "last_seen_at": "2026-06-27T14:15:00Z",
                "last_seen_location": "Los Palos Grandes station",
                "latitude": 10.5001,
                "longitude": -66.8432,
                "reporter_name": "Family member",
                "reporter_contact": "+58 private",
                "triage": "RED",
            },
            format="json",
        )
        self.assertEqual(reported.status_code, 201)
        emergency_id = reported.json()["emergency"]["id"]
        emergency = Emergency.objects.get(pk=emergency_id)
        self.assertEqual(emergency.source, Emergency.Source.MISSING_PERSON)
        self.assertEqual(emergency.triage, Emergency.Triage.UNKNOWN)

        public_map = self.client.get(
            f"/api/situations/{situation_id}/public/"
        ).json()
        public_report = next(
            item for item in public_map["emergencies"] if item["id"] == emergency_id
        )
        self.assertEqual(
            public_report["missing_person"]["person_name"], "María Example"
        )
        self.assertNotIn("reporter_contact", public_report)
        self.assertEqual(public_map["summary"]["missing_people"], 1)

        dashboard = self.client.get(
            f"/api/situations/{situation_id}/dashboard/", **auth
        ).json()
        authority_report = next(
            item for item in dashboard["emergencies"] if item["id"] == emergency_id
        )
        self.assertEqual(authority_report["reporter_contact"], "+58 private")
        self.assertEqual(
            authority_report["missing_person"]["clothing"],
            "Blue jacket and black trousers",
        )

        team = self.client.post(
            f"/api/situations/{situation_id}/teams/",
            {
                "name": "Search Team One",
                "specialty": "SEARCH_RESCUE",
                "people_count": 6,
            },
            format="json",
            **auth,
        ).json()
        assigned = self.client.post(
            f"/api/situations/{situation_id}/emergencies/{emergency_id}/assignment/",
            {"team_id": team["id"]},
            format="json",
            **auth,
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["status"], Emergency.Status.IN_PROGRESS)
        self.assertEqual(
            assigned.json()["assignments"][0]["team_name"], "Search Team One"
        )
