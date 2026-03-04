import asyncio
import base64
import time
from typing import Any

from mdm_agent.asset_manager import AssetManager
from mdm_agent.command_router import CommandRouter
from mdm_agent.config import AgentConfig
from mdm_agent.hardware import CameraDiagnostic
from mdm_agent.persistence import ensure_foreground_service
from mdm_agent.security import verify_hmac
from mdm_agent.telemetry import TelemetryService
from mdm_agent.transport import CentralApiClient


class AgentService:
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.router = CommandRouter()
        self.telemetry = TelemetryService(flush_seconds=cfg.telemetry_flush_seconds)
        self.assets = AssetManager(cfg)
        self.camera = CameraDiagnostic()
        self._register_handlers()

    def _register_handlers(self):
        self.router.register("health.ping", self._cmd_ping)
        self.router.register("asset.list", self._cmd_asset_list)
        self.router.register("asset.fetch", self._cmd_asset_fetch)
        self.router.register("diag.capture_image", self._cmd_capture_image)

    async def _cmd_ping(self, _args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "ts": int(time.time())}

    async def _cmd_asset_list(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"entries": self.assets.list_dir(args["path"])}

    async def _cmd_asset_fetch(self, args: dict[str, Any]) -> dict[str, Any]:
        data = self.assets.read_bytes(args["path"])
        return {
            "path": args["path"],
            "size": len(data),
            "content_b64": base64.b64encode(data).decode("ascii"),
        }

    async def _cmd_capture_image(self, args: dict[str, Any]) -> dict[str, Any]:
        out_dir = args.get("out_dir", "/data/data/org.example.app/cache")
        image_path = await self.camera.capture_image(out_dir=out_dir)
        data = self.assets.read_bytes(image_path)
        return {
            "path": image_path,
            "size": len(data),
            "content_b64": base64.b64encode(data).decode("ascii"),
        }

    def _valid_command(self, command_record: dict[str, Any]) -> bool:
        envelope = command_record.get("envelope", {})
        payload = command_record.get("payload", {})
        sig = envelope.get("sig", "")
        ts = int(envelope.get("ts", "0"))
        now = int(time.time())
        if abs(now - ts) > 300:
            return False
        return verify_hmac(payload, sig, self.cfg.command_hmac_secret)

    async def run(self):
        ensure_foreground_service()
        async with CentralApiClient(self.cfg) as api:
            telemetry_task = asyncio.create_task(self.telemetry.run(api))
            try:
                while True:
                    commands = await api.poll_commands()
                    for command_record in commands:
                        command_id = command_record["id"]
                        try:
                            if not self._valid_command(command_record):
                                raise PermissionError("Invalid signature or timestamp")

                            payload = command_record["payload"]
                            await self.telemetry.log(
                                "command.received",
                                {"id": command_id, "name": payload.get("name", "unknown")},
                            )
                            result = await self.router.dispatch(payload)
                            await api.post_result(command_id, "success", result)
                            await self.telemetry.log("command.completed", {"id": command_id})
                        except Exception as exc:
                            await api.post_result(command_id, "error", {"error": str(exc)})
                            await self.telemetry.log(
                                "command.failed",
                                {"id": command_id, "error": str(exc)},
                            )

                    await asyncio.sleep(self.cfg.command_poll_seconds)
            finally:
                self.telemetry.stop()
                await telemetry_task
