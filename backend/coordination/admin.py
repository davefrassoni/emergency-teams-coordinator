from django.contrib import admin

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
        SupplyRequest,
        SupplyItem,
        SupplyCommitment,
        SupplyCommitmentItem,
    ]
)
