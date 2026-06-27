import asyncio

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from .auth import raw_access_token
from .models import Activity, Member, MemberAccessKey, Situation, hash_token


def broadcast_situation_change(situation_id, version):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"situation_{situation_id}",
        {
            "type": "situation.changed",
            "version": version,
        },
    )


async def can_read_changes(request, situation):
    if situation.public_reporting_enabled:
        return True
    token = raw_access_token(request)
    if not token:
        return False
    direct_member = await Member.objects.filter(
        situation=situation,
        token_hash=hash_token(token),
        is_active=True,
    ).aexists()
    if direct_member:
        return True
    return await MemberAccessKey.objects.filter(
        member__situation=situation,
        member__is_active=True,
        token_hash=hash_token(token),
        revoked_at__isnull=True,
    ).aexists()


async def latest_version(situation):
    value = (
        await Activity.objects.filter(situation=situation)
        .order_by("-id")
        .values_list("id", flat=True)
        .afirst()
    )
    return value or 0


@never_cache
async def long_poll_changes(request, situation_id):
    situation = await Situation.objects.filter(pk=situation_id).afirst()
    if not situation:
        return JsonResponse({"error": "Operation not found."}, status=404)
    if not await can_read_changes(request, situation):
        return JsonResponse({"error": "Private access is required."}, status=401)

    try:
        since = max(0, int(request.GET.get("since", "0")))
        wait_seconds = min(25, max(1, int(request.GET.get("wait", "25"))))
    except ValueError:
        return JsonResponse({"error": "Invalid polling cursor."}, status=400)

    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_seconds
    version = await latest_version(situation)
    while version <= since and loop.time() < deadline:
        await asyncio.sleep(1)
        version = await latest_version(situation)

    return JsonResponse(
        {
            "changed": version > since,
            "version": version,
        },
        headers={"Cache-Control": "no-store"},
    )
