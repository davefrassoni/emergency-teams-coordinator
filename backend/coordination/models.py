import hashlib
import secrets
import uuid

from django.db import models
from django.utils import timezone


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token():
    return secrets.token_urlsafe(32)


class Situation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active response"
        STABILIZING = "STABILIZING", "Stabilizing"
        CLOSED = "CLOSED", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.SlugField(max_length=80, unique=True, null=True, blank=True)
    name = models.CharField(max_length=160)
    location = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.ACTIVE)
    is_public = models.BooleanField(default=False)
    public_reporting_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Member(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        COORDINATOR = "COORDINATOR", "Coordinator"
        VIEWER = "VIEWER", "Viewer"

    situation = models.ForeignKey(
        Situation, related_name="members", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)
    contact = models.CharField(max_length=180, blank=True)
    role = models.CharField(max_length=20, choices=Role, default=Role.COORDINATOR)
    token_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} · {self.situation.name}"


class MemberAccessKey(models.Model):
    member = models.ForeignKey(
        Member, related_name="access_keys", on_delete=models.CASCADE
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)


class MagicLogin(models.Model):
    situation = models.ForeignKey(
        Situation, related_name="magic_logins", on_delete=models.CASCADE
    )
    member = models.ForeignKey(
        Member, related_name="magic_logins", on_delete=models.CASCADE
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Invitation(models.Model):
    situation = models.ForeignKey(
        Situation, related_name="invitations", on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        Member, related_name="created_invitations", on_delete=models.CASCADE
    )
    token_hash = models.CharField(max_length=64, unique=True)
    role = models.CharField(
        max_length=20, choices=Member.Role, default=Member.Role.COORDINATOR
    )
    intended_for = models.CharField(max_length=120, blank=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return self.accepted_at is None and self.expires_at > timezone.now()


class Team(models.Model):
    class Specialty(models.TextChoices):
        SEARCH_RESCUE = "SEARCH_RESCUE", "Search & rescue"
        MEDICAL = "MEDICAL", "Medical"
        FIRE = "FIRE", "Fire & hazmat"
        ENGINEERING = "ENGINEERING", "Structural engineering"
        LOGISTICS = "LOGISTICS", "Logistics"
        SECURITY = "SECURITY", "Security"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        DEPLOYED = "DEPLOYED", "Deployed"
        RESTING = "RESTING", "Resting"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    situation = models.ForeignKey(
        Situation, related_name="teams", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)
    organization = models.CharField(max_length=140, blank=True)
    specialty = models.CharField(
        max_length=30, choices=Specialty, default=Specialty.SEARCH_RESCUE
    )
    status = models.CharField(
        max_length=20, choices=Status, default=Status.AVAILABLE
    )
    people_count = models.PositiveSmallIntegerField(default=1)
    leader_name = models.CharField(max_length=120, blank=True)
    contact = models.CharField(max_length=180, blank=True)
    current_location = models.CharField(max_length=240, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["situation", "name"], name="unique_team_name_per_situation"
            )
        ]

    def __str__(self):
        return self.name


class Emergency(models.Model):
    class Source(models.TextChoices):
        PUBLIC = "PUBLIC", "Public report"
        COORDINATOR = "COORDINATOR", "Coordinator report"
        MISSING_PERSON = "MISSING_PERSON", "Missing person report"
        EXTERNAL_FEED = "EXTERNAL_FEED", "External feed"

    class Triage(models.TextChoices):
        RED = "RED", "Immediate"
        YELLOW = "YELLOW", "Urgent"
        GREEN = "GREEN", "Lower urgency"
        BLACK = "BLACK", "Expectant / deceased"
        UNKNOWN = "UNKNOWN", "Not assessed"

    class Status(models.TextChoices):
        REPORTED = "REPORTED", "Reported"
        VERIFIED = "VERIFIED", "Verified"
        IN_PROGRESS = "IN_PROGRESS", "Response underway"
        RESOLVED = "RESOLVED", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    situation = models.ForeignKey(
        Situation, related_name="emergencies", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=180)
    location = models.CharField(max_length=240)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    triage = models.CharField(
        max_length=10, choices=Triage, default=Triage.UNKNOWN
    )
    status = models.CharField(
        max_length=20, choices=Status, default=Status.REPORTED
    )
    source = models.CharField(
        max_length=20, choices=Source, default=Source.COORDINATOR
    )
    people_affected = models.PositiveIntegerField(default=0)
    people_trapped = models.PositiveIntegerField(default=0)
    hazards = models.CharField(max_length=300, blank=True)
    details = models.TextField(blank=True)
    reporter_name = models.CharField(max_length=120, blank=True)
    reporter_contact = models.CharField(max_length=180, blank=True)
    created_by = models.ForeignKey(
        Member,
        related_name="reported_emergencies",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["situation", "status", "triage"]),
        ]

    def __str__(self):
        return self.title


class Assignment(models.Model):
    emergency = models.ForeignKey(
        Emergency, related_name="assignments", on_delete=models.CASCADE
    )
    team = models.ForeignKey(Team, related_name="assignments", on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(Member, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(released_at__isnull=True),
                name="one_active_assignment_per_team",
            )
        ]


class Activity(models.Model):
    situation = models.ForeignKey(
        Situation, related_name="activities", on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        Member, related_name="activities", null=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=80)
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class MissingPersonReport(models.Model):
    emergency = models.OneToOneField(
        Emergency, related_name="missing_person", on_delete=models.CASCADE
    )
    person_name = models.CharField(max_length=160)
    approximate_age = models.PositiveSmallIntegerField(null=True, blank=True)
    physical_description = models.TextField(blank=True)
    clothing = models.CharField(max_length=300, blank=True)
    circumstances = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FeatureRequest(models.Model):
    contact_email = models.EmailField()
    message = models.TextField()
    page_url = models.URLField(max_length=500, blank=True)
    locale = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    emailed_at = models.DateTimeField(null=True, blank=True)


class FeedSource(models.Model):
    class Adapter(models.TextChoices):
        VENEZUELA_MISSING = "VENEZUELA_MISSING", "Venezuela missing people"
        GENERIC_JSON = "GENERIC_JSON", "Generic JSON"

    situation = models.ForeignKey(
        Situation, related_name="feed_sources", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=160)
    source_url = models.URLField(max_length=500)
    api_url = models.URLField(max_length=500, blank=True)
    adapter = models.CharField(max_length=40, choices=Adapter)
    enabled = models.BooleanField(default=False)
    authorization_header = models.CharField(max_length=300, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["situation", "source_url"],
                name="unique_feed_source_per_situation",
            )
        ]


class FeedRecord(models.Model):
    source = models.ForeignKey(
        FeedSource, related_name="records", on_delete=models.CASCADE
    )
    external_id = models.CharField(max_length=180)
    content_hash = models.CharField(max_length=64)
    source_url = models.URLField(max_length=500, blank=True)
    raw_payload = models.JSONField(default=dict)
    emergency = models.OneToOneField(
        Emergency,
        related_name="feed_record",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="unique_external_feed_record",
            )
        ]


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIAL = "PARTIAL", "Partially covered"
        COVERED = "COVERED", "Fully covered"
        CLOSED = "CLOSED", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    situation = models.ForeignKey(
        Situation, related_name="supply_requests", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=180, default="Supplies needed")
    delivery_location = models.CharField(max_length=240)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    details = models.TextField(blank=True)
    requester_name = models.CharField(max_length=120, blank=True)
    requester_contact = models.CharField(max_length=180, blank=True)
    status = models.CharField(
        max_length=20, choices=Status, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SupplyItem(models.Model):
    class Unit(models.TextChoices):
        UNIT = "UNIT", "units"
        KG = "KG", "kg"
        LITER = "LITER", "liters"
        BOX = "BOX", "boxes"
        PACK = "PACK", "packs"
        PALLET = "PALLET", "pallets"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        SupplyRequest, related_name="items", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, choices=Unit, default=Unit.UNIT)

    class Meta:
        ordering = ["id"]


class SupplyCommitment(models.Model):
    class Status(models.TextChoices):
        PLEDGED = "PLEDGED", "Preparing"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        ARRIVED = "ARRIVED", "Arrived"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        SupplyRequest, related_name="commitments", on_delete=models.CASCADE
    )
    contributor_name = models.CharField(max_length=120)
    contributor_contact = models.CharField(max_length=180, blank=True)
    origin_location = models.CharField(max_length=240, blank=True)
    origin_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    origin_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_location = models.CharField(max_length=240, blank=True)
    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status, default=Status.PLEDGED
    )
    message = models.CharField(max_length=300, blank=True)
    share_live_location = models.BooleanField(default=False)
    tracking_token_hash = models.CharField(max_length=64, unique=True)
    last_location_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SupplyCommitmentItem(models.Model):
    commitment = models.ForeignKey(
        SupplyCommitment, related_name="items", on_delete=models.CASCADE
    )
    supply_item = models.ForeignKey(
        SupplyItem, related_name="commitment_items", on_delete=models.CASCADE
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["commitment", "supply_item"],
                name="unique_item_per_supply_commitment",
            )
        ]
