from decimal import Decimal

from rest_framework import serializers

from .models import (
    Activity,
    Assignment,
    Emergency,
    FeedRecord,
    Member,
    MissingPersonReport,
    Situation,
    SupplyCommitment,
    SupplyItem,
    SupplyRequest,
    Team,
)


class MemberSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Member
        fields = [
            "id",
            "name",
            "contact",
            "role",
            "role_label",
            "is_active",
            "joined_at",
            "last_seen_at",
        ]
        read_only_fields = ["id", "joined_at", "last_seen_at"]


class SituationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Situation
        fields = [
            "id",
            "codename",
            "name",
            "location",
            "description",
            "status",
            "public_reporting_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SituationCreateSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(max_length=120, write_only=True)
    creator_contact = serializers.EmailField(max_length=180, write_only=True)

    class Meta:
        model = Situation
        fields = [
            "name",
            "codename",
            "location",
            "description",
            "creator_name",
            "creator_contact",
        ]
        extra_kwargs = {"codename": {"required": True, "allow_null": False}}

    def validate_codename(self, value):
        value = value.strip().lower()
        reserved = {
            "api",
            "admin",
            "public",
            "operations",
            "join",
            "login",
            "static",
            "assets",
            "request-feature",
        }
        if value in reserved:
            raise serializers.ValidationError("Choose a different operation codename.")
        return value


class TeamSerializer(serializers.ModelSerializer):
    specialty_label = serializers.CharField(
        source="get_specialty_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    active_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "organization",
            "specialty",
            "specialty_label",
            "status",
            "status_label",
            "people_count",
            "leader_name",
            "contact",
            "current_location",
            "notes",
            "active_assignment",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at", "active_assignment"]

    def get_active_assignment(self, obj):
        assignment = next(
            (item for item in obj.assignments.all() if item.released_at is None), None
        )
        if not assignment:
            return None
        return {
            "emergency_id": assignment.emergency_id,
            "emergency_title": assignment.emergency.title,
            "assigned_at": assignment.assigned_at,
        }


class AssignmentSerializer(serializers.ModelSerializer):
    team_id = serializers.UUIDField(source="team.id", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    specialty = serializers.CharField(source="team.specialty", read_only=True)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "team_id",
            "team_name",
            "specialty",
            "assigned_at",
            "released_at",
        ]


class EmergencySerializer(serializers.ModelSerializer):
    triage_label = serializers.CharField(source="get_triage_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    assignments = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    missing_person = serializers.SerializerMethodField()
    external_source = serializers.SerializerMethodField()

    class Meta:
        model = Emergency
        fields = [
            "id",
            "title",
            "location",
            "latitude",
            "longitude",
            "triage",
            "triage_label",
            "status",
            "status_label",
            "source",
            "people_affected",
            "people_trapped",
            "hazards",
            "details",
            "reporter_name",
            "reporter_contact",
            "assignments",
            "created_by_name",
            "missing_person",
            "external_source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "assignments",
            "created_by_name",
            "created_at",
            "updated_at",
            "source",
            "missing_person",
            "external_source",
        ]

    def get_assignments(self, obj):
        active = [item for item in obj.assignments.all() if item.released_at is None]
        return AssignmentSerializer(active, many=True).data

    def get_missing_person(self, obj):
        try:
            report = obj.missing_person
        except MissingPersonReport.DoesNotExist:
            return None
        return MissingPersonReportSerializer(report).data

    def get_external_source(self, obj):
        try:
            record = obj.feed_record
        except (FeedRecord.DoesNotExist, AttributeError):
            return None
        return {
            "name": record.source.name,
            "source_url": record.source_url or record.source.source_url,
            "last_seen_at": record.last_seen_at,
        }


class MissingPersonReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingPersonReport
        fields = [
            "person_name",
            "approximate_age",
            "physical_description",
            "clothing",
            "circumstances",
            "last_seen_at",
        ]
        read_only_fields = fields


class PublicMissingPersonCreateSerializer(serializers.Serializer):
    person_name = serializers.CharField(max_length=160)
    approximate_age = serializers.IntegerField(
        min_value=0, max_value=130, required=False, allow_null=True
    )
    physical_description = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    clothing = serializers.CharField(
        required=False, allow_blank=True, max_length=300
    )
    circumstances = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    last_seen_at = serializers.DateTimeField(required=False, allow_null=True)
    last_seen_location = serializers.CharField(max_length=240)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    reporter_name = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    reporter_contact = serializers.CharField(
        required=False, allow_blank=True, max_length=180
    )

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class PublicEmergencySerializer(serializers.ModelSerializer):
    triage_label = serializers.CharField(source="get_triage_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    missing_person = serializers.SerializerMethodField()
    external_source = serializers.SerializerMethodField()

    class Meta:
        model = Emergency
        fields = [
            "id",
            "title",
            "location",
            "latitude",
            "longitude",
            "triage",
            "triage_label",
            "status",
            "status_label",
            "source",
            "source_label",
            "people_affected",
            "people_trapped",
            "hazards",
            "created_at",
            "updated_at",
            "missing_person",
            "external_source",
        ]
        read_only_fields = fields

    def get_missing_person(self, obj):
        try:
            report = obj.missing_person
        except MissingPersonReport.DoesNotExist:
            return None
        return MissingPersonReportSerializer(report).data

    def get_external_source(self, obj):
        try:
            record = obj.feed_record
        except (FeedRecord.DoesNotExist, AttributeError):
            return None
        return {
            "name": record.source.name,
            "source_url": record.source_url or record.source.source_url,
            "last_seen_at": record.last_seen_at,
        }


class PublicEmergencyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emergency
        fields = [
            "title",
            "location",
            "latitude",
            "longitude",
            "people_affected",
            "people_trapped",
            "hazards",
            "details",
            "reporter_name",
            "reporter_contact",
        ]

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.name", read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "action", "message", "actor_name", "created_at"]


class MagicLoginRequestSerializer(serializers.Serializer):
    codename = serializers.SlugField(max_length=80)
    email = serializers.EmailField(max_length=180)


class FeatureRequestInputSerializer(serializers.Serializer):
    contact_email = serializers.EmailField(max_length=254)
    message = serializers.CharField(min_length=10, max_length=5000)
    page_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    locale = serializers.CharField(max_length=12, required=False, allow_blank=True)


class SupplyItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    unit = serializers.ChoiceField(choices=SupplyItem.Unit)


class SupplyRequestCreateSerializer(serializers.ModelSerializer):
    items = SupplyItemInputSerializer(many=True)

    class Meta:
        model = SupplyRequest
        fields = [
            "title",
            "delivery_location",
            "latitude",
            "longitude",
            "details",
            "requester_name",
            "requester_contact",
            "items",
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one needed item.")
        if len(value) > 20:
            raise serializers.ValidationError("A request can contain up to 20 items.")
        return value

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        items = validated_data.pop("items")
        request = SupplyRequest.objects.create(**validated_data)
        SupplyItem.objects.bulk_create(
            [SupplyItem(request=request, **item) for item in items]
        )
        return request


class SupplyCommitmentItemSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )


class SupplyCommitmentCreateSerializer(serializers.ModelSerializer):
    items = SupplyCommitmentItemSerializer(many=True, write_only=True)

    class Meta:
        model = SupplyCommitment
        fields = [
            "contributor_name",
            "contributor_contact",
            "origin_location",
            "origin_latitude",
            "origin_longitude",
            "estimated_arrival",
            "message",
            "items",
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Choose at least one item to provide.")
        item_ids = [str(item["item_id"]) for item in value]
        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError("Each supply item may appear only once.")
        return value


class SupplyCommitmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyCommitment
        fields = [
            "origin_location",
            "origin_latitude",
            "origin_longitude",
            "current_location",
            "current_latitude",
            "current_longitude",
            "estimated_arrival",
            "status",
            "message",
            "share_live_location",
        ]

    def validate(self, attrs):
        for field, minimum, maximum in [
            ("origin_latitude", -90, 90),
            ("current_latitude", -90, 90),
            ("origin_longitude", -180, 180),
            ("current_longitude", -180, 180),
        ]:
            value = attrs.get(field)
            if value is not None and not minimum <= value <= maximum:
                raise serializers.ValidationError(
                    {field: f"Value must be between {minimum} and {maximum}."}
                )
        return attrs


class PublicSupplyCommitmentSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    current_latitude = serializers.SerializerMethodField()
    current_longitude = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()

    class Meta:
        model = SupplyCommitment
        fields = [
            "id",
            "contributor_name",
            "origin_location",
            "origin_latitude",
            "origin_longitude",
            "current_location",
            "current_latitude",
            "current_longitude",
            "estimated_arrival",
            "status",
            "status_label",
            "message",
            "share_live_location",
            "last_location_at",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_current_latitude(self, obj):
        return obj.current_latitude if obj.share_live_location else None

    def get_current_longitude(self, obj):
        return obj.current_longitude if obj.share_live_location else None

    def get_current_location(self, obj):
        return obj.current_location if obj.share_live_location else ""

    def get_items(self, obj):
        return [
            {
                "item_id": item.supply_item_id,
                "name": item.supply_item.name,
                "quantity": item.quantity,
                "unit": item.supply_item.unit,
                "unit_label": item.supply_item.get_unit_display(),
            }
            for item in obj.items.all()
        ]


class PublicSupplyRequestSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    commitments = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SupplyRequest
        fields = [
            "id",
            "title",
            "delivery_location",
            "latitude",
            "longitude",
            "details",
            "status",
            "status_label",
            "items",
            "commitments",
            "created_at",
            "updated_at",
        ]

    def get_items(self, obj):
        result = []
        for item in obj.items.all():
            promised = sum(
                commitment_item.quantity
                for commitment_item in item.commitment_items.all()
                if commitment_item.commitment.status
                != SupplyCommitment.Status.CANCELLED
            )
            result.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_label": item.get_unit_display(),
                    "promised_quantity": promised,
                    "remaining_quantity": max(item.quantity - promised, 0),
                }
            )
        return result

    def get_commitments(self, obj):
        active = [
            commitment
            for commitment in obj.commitments.all()
            if commitment.status != SupplyCommitment.Status.CANCELLED
        ]
        return PublicSupplyCommitmentSerializer(active, many=True).data


class CoordinationSupplyCommitmentSerializer(PublicSupplyCommitmentSerializer):
    class Meta(PublicSupplyCommitmentSerializer.Meta):
        fields = PublicSupplyCommitmentSerializer.Meta.fields + [
            "contributor_contact"
        ]


class CoordinationSupplyRequestSerializer(PublicSupplyRequestSerializer):
    commitments = serializers.SerializerMethodField()

    class Meta(PublicSupplyRequestSerializer.Meta):
        fields = PublicSupplyRequestSerializer.Meta.fields + [
            "requester_name",
            "requester_contact",
        ]

    def get_commitments(self, obj):
        active = [
            commitment
            for commitment in obj.commitments.all()
            if commitment.status != SupplyCommitment.Status.CANCELLED
        ]
        return CoordinationSupplyCommitmentSerializer(active, many=True).data
