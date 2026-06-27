from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import require_member
from .models import (
    Activity,
    Assignment,
    Emergency,
    Invitation,
    Member,
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
    MemberSerializer,
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
    return get_object_or_404(Situation, pk=situation_id)


class HealthView(APIView):
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "time": timezone.now()})


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
        serializer.save()
        log(situation, member, "SITUATION_UPDATED", "Operation details were updated")
        return Response(serializer.data)


class DashboardView(APIView):
    def get(self, request, situation_id):
        situation = situation_for(situation_id)
        member = require_member(request, situation)
        teams = Team.objects.filter(situation=situation).prefetch_related(
            "assignments__emergency"
        )
        emergencies = (
            Emergency.objects.filter(situation=situation)
            .select_related("created_by", "missing_person")
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
                source=Emergency.Source.MISSING_PERSON
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

    def public_situation(self, situation_id):
        situation = situation_for(situation_id)
        if not situation.public_reporting_enabled:
            raise PermissionDenied("Public map access is disabled for this operation.")
        return situation

    def get(self, request, situation_id):
        situation = self.public_situation(situation_id)
        emergencies = (
            Emergency.objects.filter(situation=situation)
            .select_related("missing_person")
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
                        item.source == Emergency.Source.MISSING_PERSON
                        and item.status != Emergency.Status.RESOLVED
                        for item in emergencies
                    ),
                },
                "version": version,
            }
        )

    @transaction.atomic
    def post(self, request, situation_id):
        situation = self.public_situation(situation_id)
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
        if not situation.public_reporting_enabled:
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
        if not situation.public_reporting_enabled:
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
        if not situation.public_reporting_enabled:
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
