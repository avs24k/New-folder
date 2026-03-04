from pathlib import Path

from mdm_agent.config import AgentConfig
from mdm_agent.security import sha256_hex


class AssetManager:
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.roots = tuple(path.resolve() for path in cfg.storage_roots)

    def _resolve_safe(self, path_value: str) -> Path:
        path_obj = Path(path_value).resolve()
        if any(str(path_obj).startswith(str(root)) for root in self.roots):
            return path_obj
        raise PermissionError("Requested path is outside allowed roots")

    def list_dir(self, target: str) -> list[dict]:
        path_obj = self._resolve_safe(target)
        if not path_obj.is_dir():
            raise NotADirectoryError(str(path_obj))

        entries = []
        for child in path_obj.iterdir():
            stat = child.stat()
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "is_dir": child.is_dir(),
                    "size": stat.st_size,
                    "mtime": int(stat.st_mtime),
                }
            )
        return entries

    def read_bytes(self, target: str) -> bytes:
        path_obj = self._resolve_safe(target)
        if not path_obj.is_file():
            raise FileNotFoundError(str(path_obj))
        data = path_obj.read_bytes()
        if len(data) > self.cfg.max_file_bytes:
            raise ValueError("File exceeds max_file_bytes")
        return data

    def stat_file(self, target: str) -> dict:
        data = self.read_bytes(target)
        return {
            "path": target,
            "size": len(data),
            "sha256": sha256_hex(data),
        }
