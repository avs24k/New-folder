from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="MDM Control Plane Stub", version="0.2.0")

API_TOKENS = {"dev-token-1", "dev-token-2"}
DB_PATH = os.getenv("MDM_DB_PATH", "./data/mdm.db")
_DB_LOCK = threading.Lock()


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    _ensure_parent_dir(DB_PATH)
    with _DB_LOCK, _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                dispatched_at INTEGER,
                completed_at INTEGER,
                payload_json TEXT NOT NULL,
                envelope_json TEXT NOT NULL,
                result_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                received_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_agent_status ON commands(agent_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_agent_ts ON telemetry(agent_id, ts)")
        conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class CommandPayload(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class CommandEnvelope(BaseModel):
    ts: int
    sig: str


class CommandRecord(BaseModel):
    id: str
    status: Literal["queued", "dispatched", "success", "error"] = "queued"
    created_at: int
    dispatched_at: int | None = None
    completed_at: int | None = None
    payload: CommandPayload
    envelope: CommandEnvelope
    result: dict[str, Any] | None = None


class EnqueueCommandRequest(BaseModel):
    payload: CommandPayload
    envelope: CommandEnvelope


class PullResponse(BaseModel):
    commands: list[CommandRecord]


class CompleteCommandRequest(BaseModel):
    status: Literal["success", "error"]
    result: dict[str, Any] = Field(default_factory=dict)


class TelemetryEvent(BaseModel):
    ts: int
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class TelemetryIngestRequest(BaseModel):
    events: list[TelemetryEvent] = Field(default_factory=list)


class TelemetryIngestResponse(BaseModel):
    ok: bool
    ingested: int


class HealthResponse(BaseModel):
    ok: bool
    ts: int
    db_path: str


def require_auth(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token not in API_TOKENS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token


def _row_to_command(row: sqlite3.Row) -> CommandRecord:
    payload = json.loads(row["payload_json"])
    envelope = json.loads(row["envelope_json"])
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return CommandRecord(
        id=row["id"],
        status=row["status"],
        created_at=row["created_at"],
        dispatched_at=row["dispatched_at"],
        completed_at=row["completed_at"],
        payload=CommandPayload(**payload),
        envelope=CommandEnvelope(**envelope),
        result=result,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, ts=int(time.time()), db_path=DB_PATH)


@app.post("/agents/{agent_id}/commands:enqueue", response_model=CommandRecord)
def enqueue_command(agent_id: str, req: EnqueueCommandRequest, _auth: str = Depends(require_auth)) -> CommandRecord:
    now = int(time.time())
    command_id = str(uuid.uuid4())
    payload_json = json.dumps(req.payload.model_dump(), separators=(",", ":"), sort_keys=True)
    envelope_json = json.dumps(req.envelope.model_dump(), separators=(",", ":"), sort_keys=True)

    with _DB_LOCK, _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO commands (id, agent_id, status, created_at, payload_json, envelope_json)
            VALUES (?, ?, 'queued', ?, ?, ?)
            """,
            (command_id, agent_id, now, payload_json, envelope_json),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM commands WHERE id = ?", (command_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to persist command")
        return _row_to_command(row)


@app.get("/agents/{agent_id}/commands:pull", response_model=PullResponse)
def pull_commands(agent_id: str, _auth: str = Depends(require_auth)) -> PullResponse:
    now = int(time.time())
    pulled: list[CommandRecord] = []

    with _DB_LOCK, _get_conn() as conn:
        queued_rows = conn.execute(
            "SELECT * FROM commands WHERE agent_id = ? AND status = 'queued' ORDER BY created_at ASC",
            (agent_id,),
        ).fetchall()

        for row in queued_rows:
            conn.execute(
                "UPDATE commands SET status = 'dispatched', dispatched_at = ? WHERE id = ?",
                (now, row["id"]),
            )

        conn.commit()

        dispatched_rows = conn.execute(
            "SELECT * FROM commands WHERE agent_id = ? AND dispatched_at = ? ORDER BY created_at ASC",
            (agent_id, now),
        ).fetchall()

        pulled = [_row_to_command(row) for row in dispatched_rows]

    return PullResponse(commands=pulled)


@app.post("/agents/{agent_id}/commands/{command_id}:complete")
def complete_command(
    agent_id: str,
    command_id: str,
    req: CompleteCommandRequest,
    _auth: str = Depends(require_auth),
) -> dict[str, bool]:
    now = int(time.time())
    result_json = json.dumps(req.result, separators=(",", ":"), sort_keys=True)

    with _DB_LOCK, _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM commands WHERE id = ? AND agent_id = ?",
            (command_id, agent_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Command not found")

        conn.execute(
            """
            UPDATE commands
            SET status = ?, completed_at = ?, result_json = ?
            WHERE id = ? AND agent_id = ?
            """,
            (req.status, now, result_json, command_id, agent_id),
        )
        conn.commit()

    return {"ok": True}


@app.post("/agents/{agent_id}/telemetry:ingest", response_model=TelemetryIngestResponse)
def ingest_telemetry(
    agent_id: str,
    req: TelemetryIngestRequest,
    _auth: str = Depends(require_auth),
) -> TelemetryIngestResponse:
    received_at = int(time.time())

    with _DB_LOCK, _get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO telemetry (agent_id, ts, event_type, data_json, received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    agent_id,
                    event.ts,
                    event.event_type,
                    json.dumps(event.data, separators=(",", ":"), sort_keys=True),
                    received_at,
                )
                for event in req.events
            ],
        )
        conn.commit()

    return TelemetryIngestResponse(ok=True, ingested=len(req.events))
