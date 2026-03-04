import aiohttp
import ssl
from typing import Any

from mdm_agent.config import AgentConfig


class CentralApiClient:
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self._session: aiohttp.ClientSession | None = None
        self._fingerprint: aiohttp.Fingerprint | None = None

    async def __aenter__(self):
        ssl_ctx = ssl.create_default_context()
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        self._session = aiohttp.ClientSession(
            connector=connector,
            headers={
                "Authorization": f"Bearer {self.cfg.api_token}",
                "Content-Type": "application/json",
                "X-Agent-ID": self.cfg.agent_id,
            },
            raise_for_status=True,
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if self.cfg.tls_cert_sha256:
            self._fingerprint = aiohttp.Fingerprint(bytes.fromhex(self.cfg.tls_cert_sha256))
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()

    async def poll_commands(self) -> list[dict[str, Any]]:
        assert self._session is not None
        url = f"{self.cfg.api_base_url}/agents/{self.cfg.agent_id}/commands:pull"
        async with self._session.get(url, ssl=self._fingerprint) as response:
            body = await response.json()
            return body.get("commands", [])

    async def post_result(self, command_id: str, status: str, result: dict[str, Any]):
        assert self._session is not None
        url = f"{self.cfg.api_base_url}/agents/{self.cfg.agent_id}/commands/{command_id}:complete"
        payload = {"status": status, "result": result}
        async with self._session.post(url, json=payload, ssl=self._fingerprint):
            return

    async def post_telemetry_batch(self, events: list[dict[str, Any]]):
        if not events:
            return
        assert self._session is not None
        url = f"{self.cfg.api_base_url}/agents/{self.cfg.agent_id}/telemetry:ingest"
        async with self._session.post(url, json={"events": events}, ssl=self._fingerprint):
            return
