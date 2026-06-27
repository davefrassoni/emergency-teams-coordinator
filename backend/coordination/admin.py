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
