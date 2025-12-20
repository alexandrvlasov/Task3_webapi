import asyncio
import json
from ws_manager import ConnectionManager
from nats_manager import nats_manager


async def start_nats_listener(manager: ConnectionManager):
    await nats_manager.connect()
    print("NATS listener started")

    async def on_msg(msg):
        try:
            raw = msg.data.decode("utf-8")
            event = json.loads(raw)

            payload = {
                "type": msg.subject,
                "data": event,
                "timestamp": event.get("timestamp")
            }

            await manager.broadcast(payload)
            print(f"Received from NATS and broadcasted: {msg.subject}")
        except Exception as e:
            print(f"Error processing NATS message: {e}")

    await nats_manager.subscribe("currency.*", cb=on_msg)

    while True:
        await asyncio.sleep(1)