from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from config.asgi import application
from coordination.models import Member, Situation, hash_token


class RealtimeConsumerTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.situation = Situation.objects.create(
            name="Realtime response",
            location="Caracas",
            public_reporting_enabled=False,
        )
        self.token = "private-realtime-access"
        Member.objects.create(
            situation=self.situation,
            name="Dispatcher",
            role=Member.Role.COORDINATOR,
            token_hash=hash_token(self.token),
        )

    def test_private_socket_authentication_and_change_delivery(self):
        async_to_sync(self.socket_scenario)()

    async def socket_scenario(self):
        anonymous = WebsocketCommunicator(
            application,
            f"/ws/situations/{self.situation.id}/",
            subprotocols=["reliefgrid"],
        )
        connected, _ = await anonymous.connect()
        self.assertFalse(connected)

        authorized = WebsocketCommunicator(
            application,
            f"/ws/situations/{self.situation.id}/",
            subprotocols=["reliefgrid", f"access.{self.token}"],
        )
        connected, protocol = await authorized.connect()
        self.assertTrue(connected)
        self.assertEqual(protocol, "reliefgrid")
        initial = await authorized.receive_json_from()
        self.assertEqual(initial["type"], "connected")

        await get_channel_layer().group_send(
            f"situation_{self.situation.id}",
            {"type": "situation.changed", "version": 42},
        )
        change = await authorized.receive_json_from()
        self.assertEqual(change, {"type": "situation.changed", "version": 42})
        await authorized.disconnect()

