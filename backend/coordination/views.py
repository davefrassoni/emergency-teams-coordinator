import csv
from datetime import timedelta
from io import StringIO
import json
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import require_member
from .mailer import send_feature_request, send_magic_login
from .feed_ingestion import upsert_missing_person
from .models import (
    Activity,
    Assignment,
    Emergency,
    FeatureRequest,
    FeedSource,
    Invitation,
    MagicLogin,
    Member,
    MemberAccessKey,
    MissingPersonReport,
    Situation,
    SupplyCommitment,
    SupplyCommitmentItem,
    SupplyItem,
    SupplyRequest,
    Team,
    hash_token,
    new_token,
)
from .serializers import (
    ActivitySerializer,
    CoordinationSupplyRequestSerializer,
    EmergencySerializer,
    FeatureRequestInputSerializer,
    MagicLoginRequestSerializer,
    MemberSerializer,
    MissingPeopleImportSerializer,
    PublicEmergencyCreateSerializer,
    PublicEmergencySerializer,
    PublicMissingPersonCreateSerializer,
    PublicSupplyCommitmentSerializer,
    PublicSupplyRequestSerializer,
    SituationCreateSerializer,
    SituationSerializer,
    TeamSerializer,
    SupplyCommitmentCreateSerializer,
    SupplyCommitmentUpdateSerializer,
    SupplyRequestCreateSerializer,
)
from .realtime import broadcast_situation_change


def log(situation, actor, action, message):
    activity = Activity.objects.create(
        situation=situation, actor=actor, action=action, message=message[:300]
    )
    transaction.on_commit(
        lambda: broadcast_situation_change(situation.pk, activity.pk)
    )
    return activity


def situation_for(situation_id):
    try:
        parsed_id = uuid.UUID(str(situation_id))
    except (ValueError, TypeError, AttributeError):
        return get_object_or_404(Situation, codename=str(situation_id).lower())
    return get_object_or_404(Situation, pk=parsed_id)


class HealthView(APIView):
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "time": timezone.now()})


class PasswordlessLoginThrottle(AnonRateThrottle):
    scope = "passwordless_login"


class FeatureRequestThrottle(AnonRateThrottle):
    scope = "feature_requests"


class PasswordlessLoginRequestView(APIView):
    authentication_classes = []
    throttle_classes = [PasswordlessLoginThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = MagicLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codename = serializer.validated_data["codename"].lower()
        email = serializer.validated_data["email"].lower()
        member = (
            Member.objects.select_related("situation")
            .filter(
                situation__codename=codename,
                contact__iexact=email,
                role=Member.Role.ADMIN,
                is_active=True,
            )
            .first()
        )
        if member:
            raw_token = new_token()
            login = MagicLogin.objects.create(
                situation=member.situation,
                member=member,
                token_hash=hash_token(raw_token),
                expires_at=timezone.now() + timedelta(minutes=20),
            )
            login_url = f"{settings.FRONTEND_URL}/login/{raw_token}"
            try:
                send_magic_login(
                    email,
                    member.situation.name,
                    member.situation.codename,
                    login_url,
                )
            except Exception as exc:
                login.delete()
                raise ValidationError(
                    "Email delivery is temporarily unavailable. Please try again."
                ) from exc
        return Response(
            {
                "message": (
                    "If that email administers this operation, a sign-in link "
                    "will arrive shortly."
                )
            }
        )


class PasswordlessLoginConfirmView(APIView):
    authentication_classes = []

    @transaction.atomic
    def post(self, request, token):
        login = get_object_or_404(
            MagicLogin.objects.select_for_update()
            .select_related("member", "situation"),
            token_hash=hash_token(token),
        )
        if (
            login.used_at is not None
            or login.expires_at <= timezone.now()
            or not login.member.is_active
            or login.member.role != Member.Role.ADMIN
        ):
            return Response(
                {"error": "This sign-in link has expired or was already used."},
                status=status.HTTP_410_GONE,
            )
        access_token = new_token()
        MemberAccessKey.objects.create(
            member=login.member,
            token_hash=hash_token(access_token),
        )
        login.used_at = timezone.now()
        login.save(update_fields=["used_at"])
        log(
            login.situation,
            login.member,
            "PASSWORDLESS_LOGIN",
            f"{login.member.name} signed in on a new device",
        )
        return Response(
            {
                "situation": SituationSerializer(login.situation).data,
                "member": MemberSerializer(login.member).data,
                "access_token": access_token,
            }
        )


class FeatureRequestView(APIView):
    authentication_classes = []
    throttle_classes = [FeatureRequestThrottle]

    def post(self, request):
        serializer = FeatureRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feature = FeatureRequest.objects.create(**serializer.validated_data)
        try:
            send_feature_request(
                feature.contact_email,
                feature.message,
                feature.page_url,
                feature.locale,
            )
        except Exception as exc:
            raise ValidationError(
                "The request was saved, but email delivery failed. Please try again later."
            ) from exc
        feature.emailed_at = timezone.now()
        feature.save(update_fields=["emailed_at"])
        return Response(
            {"message": "Your feature request was sent. Thank you."},
            status=status.HTTP_201_CREATED,
        )


class SituationCreateView(APIView):
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = SituationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        creator_name = data.pop("creator_name")
        creator_contact = data.pop("creator_contact", "")
        situation = Situation.objects.create(**data)
        access_token = new_token()
        member = Member.objects.create(
            situation=situation,
            name=creator_name,
            contact=creator_contact,
            role=Member.Role.ADMIN,
            token_hash=hash_token(access_token),
        )
        log(situation, member, "SITUATION_CREATED", f"{creator_name} opened the operation")
        return Response(
            {
                "situation": SituationSerializer(situation).data,
                "member": MemberSerializer(member).data,
                "access_token": access_token,
            },
            status=status.HTTP_201_CREATED,
        )


class SituationDetailView(APIView):
    def get(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation)
        return Response(
            {
                "situation": SituationSerializer(situation).data,
                "member": MemberSerializer(member).data,
            }
        )

    def patch(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, admin=True)
        serializer = SituationSerializer(situation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        if not updated.is_public and updated.public_reporting_enabled:
            updated.public_reporting_enabled = False
            updated.save(update_fields=["public_reporting_enabled", "updated_at"])
        log(situation, member, "SITUATION_UPDATED", "Operation details were updated")
        return Response(SituationSerializer(updated).data)


class PopularSituationListView(APIView):
    authentication_classes = []

    def get(self, request):
        situations = (
            Situation.objects.filter(is_public=True)
            .exclude(status=Situation.Status.CLOSED)
            .annotate(activity_count=Count("activities"))
            .order_by("-activity_count", "-updated_at")[:12]
        )
        return Response(SituationSerializer(situations, many=True).data)


class MissingPeopleImportView(APIView):
    @staticmethod
    def parse_records(content, requested_format):
        selected_format = requested_format
        if selected_format == "auto":
            selected_format = "json" if content.lstrip().startswith(("[", "{")) else "csv"
        if selected_format == "json":
            try:
                payload = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Invalid JSON: {exc.msg}.") from exc
            if isinstance(payload, dict):
                for key in ["items", "records", "data", "results"]:
                    if isinstance(payload.get(key), list):
                        payload = payload[key]
                        break
            records = payload
        else:
            records = list(csv.DictReader(StringIO(content)))
        if not isinstance(records, list) or not records:
            raise ValidationError("The import must contain at least one record.")
        if len(records) > 2000:
            raise ValidationError("Import at most 2,000 records at a time.")
        if not all(isinstance(item, dict) for item in records):
            raise ValidationError("Every imported record must be an object or CSV row.")
        return records

    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, admin=True)
        serializer = MissingPeopleImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        records = self.parse_records(data["content"], data["format"])
        source, _ = FeedSource.objects.get_or_create(
            situation=situation,
            source_url=data["source_url"],
            defaults={
                "name": data["source_name"],
                "adapter": FeedSource.Adapter.GENERIC_JSON,
                "enabled": False,
            },
        )
        if source.name != data["source_name"]:
            source.name = data["source_name"]
            source.save(update_fields=["name", "updated_at"])
        totals = {"created": 0, "updated": 0, "unchanged": 0}
        for record in records:
            totals[upsert_missing_person(source, record)] += 1
        changed = totals["created"] + totals["updated"]
        if changed:
            log(
                situation,
                member,
                "MISSING_PEOPLE_IMPORTED",
                f"{source.name}: {changed} missing-person records imported or updated",
            )
        return Response(
            {
                **totals,
                "total": len(records),
                "source": source.name,
                "message": (
                    f"Imported {totals['created']} new and updated "
                    f"{totals['updated']} missing-person records."
                ),
            }
        )


class DashboardView(APIView):
    def get(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation)
        teams = Team.objects.filter(situation=situation).prefetch_related(
            "assignments__emergency"
        )
        emergencies = (
            Emergency.objects.filter(situation=situation)
            .select_related("created_by", "missing_person", "feed_record__source")
            .prefetch_related("assignments__team")
        )
        activities = (
            Activity.objects.filter(situation=situation)
            .exclude(action="SUPPLY_LOCATION_UPDATED")
            .select_related("actor")[:30]
        )
        supply_requests = public_supply_requests(situation)
        open_emergencies = emergencies.exclude(status=Emergency.Status.RESOLVED)
        summary = {
            "open_emergencies": open_emergencies.count(),
            "immediate_emergencies": open_emergencies.filter(
                triage=Emergency.Triage.RED
            ).count(),
            "people_trapped": sum(item.people_trapped for item in open_emergencies),
            "available_teams": teams.filter(status=Team.Status.AVAILABLE).count(),
            "total_responders": sum(item.people_count for item in teams),
            "open_supply_requests": supply_requests.exclude(
                status=SupplyRequest.Status.CLOSED
            ).count(),
            "missing_people": open_emergencies.filter(
                missing_person__isnull=False
            ).count(),
        }
        version = (
            Activity.objects.filter(situation=situation)
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
            or 0
        )
        return Response(
            {
                "situation": SituationSerializer(situation).data,
                "member": MemberSerializer(member).data,
                "summary": summary,
                "emergencies": EmergencySerializer(emergencies, many=True).data,
                "teams": TeamSerializer(teams, many=True).data,
                "members": MemberSerializer(
                    situation.members.filter(is_active=True), many=True
                ).data,
                "activity": ActivitySerializer(activities, many=True).data,
                "supply_requests": CoordinationSupplyRequestSerializer(
                    supply_requests, many=True
                ).data,
                "version": version,
            }
        )


class PublicReportThrottle(AnonRateThrottle):
    scope = "public_reports"


class SupplyTrackingThrottle(AnonRateThrottle):
    scope = "supply_tracking"


def public_supply_requests(situation):
    return (
        SupplyRequest.objects.filter(situation=situation)
        .prefetch_related(
            Prefetch(
                "items__commitment_items",
                queryset=SupplyCommitmentItem.objects.select_related("commitment"),
            ),
            Prefetch(
                "commitments",
                queryset=SupplyCommitment.objects.prefetch_related(
                    "items__supply_item"
                ),
            ),
        )
        .order_by("-updated_at")
    )


def update_supply_request_status(supply_request):
    items = list(supply_request.items.all())
    promised_any = False
    fully_covered = bool(items)
    for item in items:
        promised = (
            SupplyCommitmentItem.objects.filter(supply_item=item)
            .exclude(commitment__status=SupplyCommitment.Status.CANCELLED)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )
        promised_any = promised_any or promised > 0
        fully_covered = fully_covered and promised >= item.quantity
    new_status = (
        SupplyRequest.Status.COVERED
        if fully_covered
        else SupplyRequest.Status.PARTIAL
        if promised_any
        else SupplyRequest.Status.OPEN
    )
    if supply_request.status != SupplyRequest.Status.CLOSED:
        SupplyRequest.objects.filter(pk=supply_request.pk).update(status=new_status)
        supply_request.status = new_status


class PublicSituationView(APIView):
    authentication_classes = []

    def get_throttles(self):
        return [PublicReportThrottle()] if self.request.method == "POST" else []

    def public_situation(self, request, situation_id, reporting=False):
        situation = situation_for(situation_id)
        if reporting:
            if not situation.is_public or not situation.public_reporting_enabled:
                raise PermissionDenied("Public reporting is disabled for this operation.")
        elif not situation.is_public:
            require_member(request, situation)
        return situation

    def get(self, request, situation_id):
        situation = self.public_situation(request, situation_id)
        emergencies = (
            Emergency.objects.filter(situation=situation)
            .select_related("missing_person", "feed_record__source")
            .order_by("-updated_at")[:500]
        )
        supply_requests = public_supply_requests(situation)[:200]
        version = (
            Activity.objects.filter(situation=situation)
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
            or 0
        )
        return Response(
            {
                "situation": SituationSerializer(situation).data,
                "emergencies": PublicEmergencySerializer(
                    emergencies, many=True
                ).data,
                "supply_requests": PublicSupplyRequestSerializer(
                    supply_requests, many=True
                ).data,
                "summary": {
                    "open_emergencies": sum(
                        item.status != Emergency.Status.RESOLVED
                        for item in emergencies
                    ),
                    "verified_emergencies": sum(
                        item.status
                        in [
                            Emergency.Status.VERIFIED,
                            Emergency.Status.IN_PROGRESS,
                        ]
                        for item in emergencies
                    ),
                    "missing_people": sum(
                        hasattr(item, "missing_person")
                        and item.status != Emergency.Status.RESOLVED
                        for item in emergencies
                    ),
                },
                "version": version,
            }
        )

    @transaction.atomic
    def post(self, request, situation_id):
        situation = self.public_situation(request, situation_id, reporting=True)
        serializer = PublicEmergencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emergency = serializer.save(
            situation=situation,
            created_by=None,
            source=Emergency.Source.PUBLIC,
            triage=Emergency.Triage.UNKNOWN,
            status=Emergency.Status.REPORTED,
        )
        log(
            situation,
            None,
            "PUBLIC_REPORT_RECEIVED",
            f"Public report received at {emergency.location}",
        )
        return Response(
            {
                "emergency": PublicEmergencySerializer(emergency).data,
                "message": "Report received. A coordinator must verify it before dispatch.",
            },
            status=status.HTTP_201_CREATED,
        )


class PublicMissingPersonCreateView(APIView):
    authentication_classes = []
    throttle_classes = [PublicReportThrottle]

    @transaction.atomic
    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        if not situation.is_public or not situation.public_reporting_enabled:
            raise PermissionDenied("Public reporting is disabled for this operation.")
        serializer = PublicMissingPersonCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        person_name = data.pop("person_name")
        location = data.pop("last_seen_location")
        latitude = data.pop("latitude")
        longitude = data.pop("longitude")
        reporter_name = data.pop("reporter_name", "")
        reporter_contact = data.pop("reporter_contact", "")
        detail_parts = [
            data.get("physical_description", ""),
            f"Clothing: {data['clothing']}" if data.get("clothing") else "",
            data.get("circumstances", ""),
        ]
        emergency = Emergency.objects.create(
            situation=situation,
            title=f"Missing person: {person_name}",
            location=location,
            latitude=latitude,
            longitude=longitude,
            triage=Emergency.Triage.UNKNOWN,
            status=Emergency.Status.REPORTED,
            source=Emergency.Source.MISSING_PERSON,
            people_affected=1,
            details="\n".join(part for part in detail_parts if part),
            reporter_name=reporter_name,
            reporter_contact=reporter_contact,
            created_by=None,
        )
        MissingPersonReport.objects.create(
            emergency=emergency,
            person_name=person_name,
            **data,
        )
        log(
            situation,
            None,
            "MISSING_PERSON_REPORTED",
            f"Missing person reported near {location}",
        )
        emergency = Emergency.objects.select_related("missing_person").get(
            pk=emergency.pk
        )
        return Response(
            {
                "emergency": PublicEmergencySerializer(emergency).data,
                "message": (
                    "Missing-person report received. Authorities can verify it "
                    "and assign a search team."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class PublicSupplyRequestCreateView(APIView):
    authentication_classes = []
    throttle_classes = [PublicReportThrottle]

    @transaction.atomic
    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        if not situation.is_public or not situation.public_reporting_enabled:
            raise PermissionDenied("Public reporting is disabled for this operation.")
        serializer = SupplyRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supply_request = serializer.save(situation=situation)
        log(
            situation,
            None,
            "SUPPLY_REQUEST_CREATED",
            f"Public supply request posted at {supply_request.delivery_location}",
        )
        hydrated = public_supply_requests(situation).get(pk=supply_request.pk)
        return Response(
            {
                "supply_request": PublicSupplyRequestSerializer(hydrated).data,
                "message": "Supply request posted to the public map.",
            },
            status=status.HTTP_201_CREATED,
        )


class PublicSupplyCommitmentCreateView(APIView):
    authentication_classes = []
    throttle_classes = [PublicReportThrottle]

    @transaction.atomic
    def post(self, request, situation_id, supply_request_id):
        situation = situation_for(situation_id)
        if not situation.is_public or not situation.public_reporting_enabled:
            raise PermissionDenied("Public reporting is disabled for this operation.")
        supply_request = get_object_or_404(
            SupplyRequest.objects.select_for_update(),
            pk=supply_request_id,
            situation=situation,
        )
        if supply_request.status == SupplyRequest.Status.CLOSED:
            raise ValidationError("This supply request is closed.")

        serializer = SupplyCommitmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        contributions = data.pop("items")
        requested_items = {
            str(item.id): item
            for item in SupplyItem.objects.select_for_update().filter(
                request=supply_request
            )
        }
        for contribution in contributions:
            item = requested_items.get(str(contribution["item_id"]))
            if not item:
                raise ValidationError("One of the selected items is not in this request.")
            promised = (
                SupplyCommitmentItem.objects.filter(supply_item=item)
                .exclude(commitment__status=SupplyCommitment.Status.CANCELLED)
                .aggregate(total=Sum("quantity"))["total"]
                or 0
            )
            remaining = item.quantity - promised
            if contribution["quantity"] > remaining:
                raise ValidationError(
                    {
                        "items": (
                            f"Only {remaining:g} {item.get_unit_display()} of "
                            f"{item.name} remain unclaimed."
                        )
                    }
                )

        tracking_token = new_token()
        commitment = SupplyCommitment.objects.create(
            request=supply_request,
            tracking_token_hash=hash_token(tracking_token),
            **data,
        )
        SupplyCommitmentItem.objects.bulk_create(
            [
                SupplyCommitmentItem(
                    commitment=commitment,
                    supply_item=requested_items[str(item["item_id"])],
                    quantity=item["quantity"],
                )
                for item in contributions
            ]
        )
        update_supply_request_status(supply_request)
        log(
            situation,
            None,
            "SUPPLY_COMMITTED",
            f"Supplies pledged for {supply_request.delivery_location}",
        )
        commitment = SupplyCommitment.objects.prefetch_related(
            "items__supply_item"
        ).get(pk=commitment.pk)
        return Response(
            {
                "commitment": PublicSupplyCommitmentSerializer(commitment).data,
                "tracking_token": tracking_token,
                "tracking_url": (
                    f"{settings.FRONTEND_URL}/public/{situation.pk}"
                    f"?delivery={commitment.pk}#tracking={tracking_token}"
                ),
                "message": "Your contribution is reserved. Save the tracking link.",
            },
            status=status.HTTP_201_CREATED,
        )


class PublicSupplyCommitmentUpdateView(APIView):
    authentication_classes = []
    throttle_classes = [SupplyTrackingThrottle]

    @transaction.atomic
    def patch(self, request, situation_id, commitment_id):
        situation = situation_for(situation_id)
        token = request.headers.get("X-Supply-Token", "").strip()
        if not token:
            raise PermissionDenied("This delivery needs its private tracking key.")
        commitment = get_object_or_404(
            SupplyCommitment.objects.select_for_update()
            .select_related("request")
            .prefetch_related("items__supply_item"),
            pk=commitment_id,
            request__situation=situation,
            tracking_token_hash=hash_token(token),
        )
        if commitment.status == SupplyCommitment.Status.CANCELLED:
            raise ValidationError("This delivery was cancelled and can no longer be updated.")
        serializer = SupplyCommitmentUpdateSerializer(
            commitment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        location_changed = any(
            field in serializer.validated_data
            for field in [
                "current_location",
                "current_latitude",
                "current_longitude",
            ]
        )
        commitment = serializer.save(
            last_location_at=timezone.now()
            if location_changed
            else commitment.last_location_at
        )
        if commitment.status == SupplyCommitment.Status.CANCELLED:
            update_supply_request_status(commitment.request)
        action = (
            "SUPPLY_LOCATION_UPDATED"
            if location_changed
            else "SUPPLY_DELIVERY_UPDATED"
        )
        message = (
            "A supply delivery shared a new location"
            if location_changed
            else f"Supply delivery marked {commitment.get_status_display()}"
        )
        log(situation, None, action, message)
        return Response(
            {
                "commitment": PublicSupplyCommitmentSerializer(commitment).data,
                "message": "Delivery tracking updated.",
            }
        )

class TeamListCreateView(APIView):
    def get(self, request, situation_id):
        situation = situation_for(situation_id)
        require_member(request, situation)
        teams = Team.objects.filter(situation=situation).prefetch_related(
            "assignments__emergency"
        )
        return Response(TeamSerializer(teams, many=True).data)

    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        serializer = TeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            team = serializer.save(situation=situation)
        except IntegrityError as exc:
            raise ValidationError({"name": "A team with this name already exists."}) from exc
        log(situation, member, "TEAM_CREATED", f"{team.name} joined the operation")
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    def patch(self, request, situation_id, team_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        team = get_object_or_404(Team, situation=situation, pk=team_id)
        serializer = TeamSerializer(team, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        team = serializer.save()
        log(situation, member, "TEAM_UPDATED", f"{team.name} was updated")
        return Response(TeamSerializer(team).data)

    def delete(self, request, situation_id, team_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, admin=True)
        team = get_object_or_404(Team, situation=situation, pk=team_id)
        if team.assignments.filter(released_at__isnull=True).exists():
            raise ValidationError("Release this team from its emergency first.")
        name = team.name
        team.delete()
        log(situation, member, "TEAM_REMOVED", f"{name} was removed")
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmergencyListCreateView(APIView):
    def get(self, request, situation_id):
        situation = situation_for(situation_id)
        require_member(request, situation)
        emergencies = (
            Emergency.objects.filter(situation=situation)
            .select_related("created_by")
            .prefetch_related("assignments__team")
        )
        return Response(EmergencySerializer(emergencies, many=True).data)

    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        serializer = EmergencySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emergency = serializer.save(situation=situation, created_by=member)
        log(
            situation,
            member,
            "EMERGENCY_REPORTED",
            f"{emergency.title} reported at {emergency.location}",
        )
        return Response(
            EmergencySerializer(emergency).data, status=status.HTTP_201_CREATED
        )


class EmergencyDetailView(APIView):
    def patch(self, request, situation_id, emergency_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        emergency = get_object_or_404(
            Emergency, situation=situation, pk=emergency_id
        )
        old_status = emergency.status
        serializer = EmergencySerializer(emergency, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        emergency = serializer.save()
        message = f"{emergency.title} was updated"
        if old_status != emergency.status:
            message = f"{emergency.title} marked {emergency.get_status_display()}"
        log(situation, member, "EMERGENCY_UPDATED", message)
        return Response(EmergencySerializer(emergency).data)


class AssignmentView(APIView):
    @transaction.atomic
    def post(self, request, situation_id, emergency_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        emergency = get_object_or_404(
            Emergency, situation=situation, pk=emergency_id
        )
        team = get_object_or_404(Team, situation=situation, pk=request.data.get("team_id"))
        if team.status != Team.Status.AVAILABLE:
            raise ValidationError(f"{team.name} is not currently available.")
        if Assignment.objects.filter(team=team, released_at__isnull=True).exists():
            raise ValidationError(f"{team.name} already has an active assignment.")
        Assignment.objects.create(
            emergency=emergency, team=team, assigned_by=member
        )
        team.status = Team.Status.DEPLOYED
        team.current_location = emergency.location
        team.save(update_fields=["status", "current_location", "updated_at"])
        if emergency.status in [
            Emergency.Status.REPORTED,
            Emergency.Status.VERIFIED,
        ]:
            emergency.status = Emergency.Status.IN_PROGRESS
            emergency.save(update_fields=["status", "updated_at"])
        log(
            situation,
            member,
            "TEAM_ASSIGNED",
            f"{team.name} assigned to {emergency.title}",
        )
        emergency.refresh_from_db()
        return Response(EmergencySerializer(emergency).data)

    @transaction.atomic
    def delete(self, request, situation_id, emergency_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, write=True)
        emergency = get_object_or_404(
            Emergency, situation=situation, pk=emergency_id
        )
        team = get_object_or_404(Team, situation=situation, pk=request.data.get("team_id"))
        assignment = get_object_or_404(
            Assignment, emergency=emergency, team=team, released_at__isnull=True
        )
        assignment.released_at = timezone.now()
        assignment.save(update_fields=["released_at"])
        team.status = Team.Status.AVAILABLE
        team.current_location = emergency.location
        team.save(update_fields=["status", "current_location", "updated_at"])
        log(
            situation,
            member,
            "TEAM_RELEASED",
            f"{team.name} released from {emergency.title}",
        )
        return Response(EmergencySerializer(emergency).data)


class InvitationCreateView(APIView):
    def post(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation, admin=True)
        role = request.data.get("role", Member.Role.COORDINATOR)
        if role not in Member.Role.values:
            raise ValidationError({"role": "Choose a valid access role."})
        raw_token = new_token()
        invitation = Invitation.objects.create(
            situation=situation,
            created_by=member,
            token_hash=hash_token(raw_token),
            role=role,
            intended_for=str(request.data.get("intended_for", ""))[:120],
            expires_at=timezone.now() + timedelta(hours=72),
        )
        link = f"{settings.FRONTEND_URL}/join/{raw_token}"
        log(situation, member, "INVITE_CREATED", f"A {invitation.get_role_display()} invite was created")
        return Response(
            {
                "invite_url": link,
                "expires_at": invitation.expires_at,
                "role": invitation.role,
                "intended_for": invitation.intended_for,
            },
            status=status.HTTP_201_CREATED,
        )


class InvitationAcceptView(APIView):
    authentication_classes = []

    def invitation(self, token):
        return get_object_or_404(
            Invitation.objects.select_related("situation"),
            token_hash=hash_token(token),
        )

    def get(self, request, token):
        invitation = self.invitation(token)
        if not invitation.is_valid:
            return Response(
                {"error": "This invitation has expired or was already used."},
                status=status.HTTP_410_GONE,
            )
        return Response(
            {
                "situation": SituationSerializer(invitation.situation).data,
                "role": invitation.role,
                "role_label": invitation.get_role_display(),
                "intended_for": invitation.intended_for,
                "expires_at": invitation.expires_at,
            }
        )

    @transaction.atomic
    def post(self, request, token):
        invitation = get_object_or_404(
            Invitation.objects.select_for_update().select_related("situation"),
            token_hash=hash_token(token),
        )
        if not invitation.is_valid:
            return Response(
                {"error": "This invitation has expired or was already used."},
                status=status.HTTP_410_GONE,
            )
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "Your name is required."})
        access_token = new_token()
        member = Member.objects.create(
            situation=invitation.situation,
            name=name[:120],
            contact=str(request.data.get("contact", ""))[:180],
            role=invitation.role,
            token_hash=hash_token(access_token),
        )
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        log(
            invitation.situation,
            member,
            "MEMBER_JOINED",
            f"{member.name} joined as {member.get_role_display()}",
        )
        return Response(
            {
                "situation": SituationSerializer(invitation.situation).data,
                "member": MemberSerializer(member).data,
                "access_token": access_token,
            },
            status=status.HTTP_201_CREATED,
        )


class MemberDetailView(APIView):
    def patch(self, request, situation_id, member_id):
        situation = situation_for(situation_id)
        actor = require_member(request, situation, admin=True)
        member = get_object_or_404(Member, situation=situation, pk=member_id)
        if member.pk == actor.pk and request.data.get("is_active") is False:
            raise ValidationError("You cannot revoke your own active access.")
        allowed = {
            key: value
            for key, value in request.data.items()
            if key in {"role", "is_active"}
        }
        serializer = MemberSerializer(member, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        log(situation, actor, "MEMBER_UPDATED", f"{updated.name}'s access was updated")
        return Response(MemberSerializer(updated).data)
