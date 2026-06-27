from django.urls import path

from .views import (
    AssignmentView,
    DashboardView,
    EmergencyDetailView,
    EmergencyListCreateView,
    HealthView,
    InvitationAcceptView,
    InvitationCreateView,
    MemberDetailView,
    PublicSituationView,
    PublicMissingPersonCreateView,
    PublicSupplyCommitmentCreateView,
    PublicSupplyCommitmentUpdateView,
    PublicSupplyRequestCreateView,
    SituationCreateView,
    SituationDetailView,
    TeamDetailView,
    TeamListCreateView,
)
from .realtime import long_poll_changes

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("situations/", SituationCreateView.as_view()),
    path("situations/<uuid:situation_id>/", SituationDetailView.as_view()),
    path("situations/<uuid:situation_id>/dashboard/", DashboardView.as_view()),
    path(
        "situations/<uuid:situation_id>/public/",
        PublicSituationView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/public/supplies/",
        PublicSupplyRequestCreateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/public/missing-people/",
        PublicMissingPersonCreateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/public/supplies/<uuid:supply_request_id>/commitments/",
        PublicSupplyCommitmentCreateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/public/commitments/<uuid:commitment_id>/",
        PublicSupplyCommitmentUpdateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/changes/",
        long_poll_changes,
    ),
    path("situations/<uuid:situation_id>/teams/", TeamListCreateView.as_view()),
    path(
        "situations/<uuid:situation_id>/teams/<uuid:team_id>/",
        TeamDetailView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/emergencies/",
        EmergencyListCreateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/emergencies/<uuid:emergency_id>/",
        EmergencyDetailView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/emergencies/<uuid:emergency_id>/assignment/",
        AssignmentView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/invitations/",
        InvitationCreateView.as_view(),
    ),
    path(
        "situations/<uuid:situation_id>/members/<int:member_id>/",
        MemberDetailView.as_view(),
    ),
    path("invitations/<str:token>/", InvitationAcceptView.as_view()),
]
