from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    agent_id: str = os.getenv("MDM_AGENT_ID", "android-agent-001")
    api_base_url: str = os.getenv("MDM_API_BASE_URL", "https://mdm.example.com/api/v1")
    api_token: str = os.getenv("MDM_API_TOKEN", "")
    command_poll_seconds: int = int(os.getenv("MDM_POLL_SECONDS", "5"))
    max_file_bytes: int = int(os.getenv("MDM_MAX_FILE_BYTES", str(8 * 1024 * 1024)))
    telemetry_flush_seconds: int = int(os.getenv("MDM_TELEMETRY_FLUSH_SECONDS", "10"))
    command_hmac_secret: str = os.getenv("MDM_COMMAND_HMAC_SECRET", "")
    tls_cert_sha256: str = os.getenv("MDM_TLS_CERT_SHA256", "")
    storage_roots: tuple[Path, ...] = (
        Path("/storage/emulated/0/Documents"),
        Path("/storage/emulated/0/DCIM"),
        Path("/storage/emulated/0/Download"),
    )
