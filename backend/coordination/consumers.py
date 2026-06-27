from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Activity, Member, Situation, hash_token


class SituationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.situation_id = str(self.scope["url_route"]["kwargs"]["situation_id"])
        self.group_name = f"situation_{self.situation_id}"
        token = self.access_token()
        allowed = await self.authorized(token)
        if not allowed:
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        protocols = self.scope.get("subprotocols", [])
        await self.accept("reliefgrid" if "reliefgrid" in protocols else None)
        version = await self.current_version()
        await self.send_json(
            {"type": "connected", "version": version, "transport": "websocket"}
        )

    def access_token(self):
        for protocol in self.scope.get("subprotocols", []):
            if protocol.startswith("access."):
                return protocol.removeprefix("access.")
        query = parse_qs(self.scope.get("query_string", b"").decode())
        return query.get("access_token", [""])[0]

    @database_sync_to_async
    def authorized(self, token):
        try:
            situation = Situation.objects.get(pk=self.situation_id)
        except Situation.DoesNotExist:
            return False
        if situation.public_reporting_enabled:
            return True
        if not token:
            return False
        return Member.objects.filter(
            situation=situation,
            token_hash=hash_token(token),
            is_active=True,
        ).exists()

    @database_sync_to_async
    def current_version(self):
        return (
            Activity.objects.filter(situation_id=self.situation_id)
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
            or 0
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def situation_changed(self, event):
        await self.send_json(
            {
                "type": "situation.changed",
                "version": event["version"],
            }
        )

