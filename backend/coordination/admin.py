from django.contrib import admin

from .models import (
    Activity,
    Assignment,
    Emergency,
    FeatureRequest,
    FeedRecord,
    FeedSource,
    Invitation,
    Member,
    MemberAccessKey,
    MagicLogin,
    MissingPersonReport,
    Situation,
    SupplyCommitment,
    SupplyCommitmentItem,
    SupplyItem,
    SupplyRequest,
    Team,
    WorldEvent,
)

admin.site.register(
    [
        Situation,
        Member,
        Invitation,
        Team,
        Emergency,
        Assignment,
        Activity,
        MissingPersonReport,
        MemberAccessKey,
        MagicLogin,
        FeatureRequest,
        FeedSource,
        FeedRecord,
        SupplyRequest,
        SupplyItem,
        SupplyCommitment,
        SupplyCommitmentItem,
    ]
)


@admin.register(WorldEvent)
class WorldEventAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "event_type",
        "alert_level",
        "title",
        "country",
        "published_at",
    )
    list_filter = ("source", "event_type", "alert_level", "is_active")
    search_fields = ("title", "country", "external_id")
