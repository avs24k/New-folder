import asyncio
import time
from typing import Any

from mdm_agent.transport import CentralApiClient


class TelemetryService:
    def __init__(self, flush_seconds: int = 10):
        self.flush_seconds = flush_seconds
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._stop_event = asyncio.Event()

    async def log(self, event_type: str, data: dict[str, Any]):
        await self.queue.put(
            {
                "ts": int(time.time()),
                "event_type": event_type,
                "data": data,
            }
        )

    async def run(self, api: CentralApiClient):
        while not self._stop_event.is_set():
            batch: list[dict[str, Any]] = []
            try:
                first = await asyncio.wait_for(self.queue.get(), timeout=self.flush_seconds)
                batch.append(first)
            except asyncio.TimeoutError:
                pass

            while len(batch) < 200 and not self.queue.empty():
                batch.append(self.queue.get_nowait())

            if batch:
                await api.post_telemetry_batch(batch)

    def stop(self):
        self._stop_event.set()
