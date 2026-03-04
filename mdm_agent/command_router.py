from typing import Any, Awaitable, Callable

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class CommandRouter:
    def __init__(self):
        self._handlers: dict[str, Handler] = {}

    def register(self, name: str, handler: Handler):
        self._handlers[name] = handler

    async def dispatch(self, command: dict[str, Any]) -> dict[str, Any]:
        name = command.get("name")
        args = command.get("args", {})
        if name not in self._handlers:
            raise KeyError(f"Unknown command: {name}")
        return await self._handlers[name](args)
