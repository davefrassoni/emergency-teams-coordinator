from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied

from .models import Member, hash_token


class AccessRequired(APIException):
    status_code = 401
    default_detail = "This operation requires its private access link."
    default_code = "not_authenticated"


def raw_access_token(request):
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.headers.get("X-Access-Token", "").strip()


def require_member(request, situation, write=False, admin=False):
    token = raw_access_token(request)
    if not token:
        raise AccessRequired("This operation requires its private access link.")
    try:
        member = Member.objects.get(
            situation=situation,
            token_hash=hash_token(token),
            is_active=True,
        )
    except Member.DoesNotExist as exc:
        raise AccessRequired("This access link is invalid or has been revoked.") from exc

    if admin and member.role != Member.Role.ADMIN:
        raise PermissionDenied("Only operation administrators can do that.")
    if write and member.role == Member.Role.VIEWER:
        raise PermissionDenied("This access link is view-only.")

    Member.objects.filter(pk=member.pk).update(last_seen_at=timezone.now())
    request.operation_member = member
    return member
