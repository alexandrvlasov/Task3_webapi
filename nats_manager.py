import json
import nats
from typing import Awaitable, Callable, Optional
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg


NATS_URL = "nats://127.0.0.1:4222"


class NATSManager:
    def __init__(self, url: str = NATS_URL):
        self.url = url
        self.nc: Optional[NATSClient] = None

    async def connect(self) -> NATSClient:
        if self.nc and self.nc.is_connected:
            return self.nc

        self.nc = await nats.connect(self.url)
        print(f"Connected to NATS at {self.url}")
        return self.nc

    async def close(self):
        if self.nc and self.nc.is_connected:
            await self.nc.drain()
            await self.nc.close()
            print("NATS connection closed")

    async def publish_json(self, subject: str, data: dict):
        nc = await self.connect()
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        await nc.publish(subject, payload)
        print(f"Published to NATS subject '{subject}': {data}")

    async def subscribe(self, subject: str, cb: Callable[[Msg], Awaitable[None]]):
        nc = await self.connect()
        await nc.subscribe(subject, cb=cb)
        print(f"Subscribed to NATS subject: {subject}")


nats_manager = NATSManager()