# Lawful MDM Skeleton

## Components
- `mdm_agent/`: modular Android agent backend skeleton.
- `server.py`: FastAPI control-plane stub with SQLite persistence.
- `postman/mdm-control-plane.postman_collection.json`: API test collection.
- `Dockerfile` + `docker-compose.yml`: local API containerization.
- `buildozer.spec`: Android packaging/service config.
- `app.py`: Kivy app entry point that starts the service.
- `service.py`: foreground service bootstrap sample.

## Run API locally
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Run API with Docker
```bash
docker compose up --build
```

## API Endpoints
- `GET /health`
- `POST /agents/{agent_id}/commands:enqueue`
- `GET /agents/{agent_id}/commands:pull`
- `POST /agents/{agent_id}/commands/{command_id}:complete`
- `POST /agents/{agent_id}/telemetry:ingest`

## Security notes
- Replace static bearer tokens with OIDC/JWT.
- Enforce signed command envelopes and nonce replay checks in production.
- Keep least-privilege Android permissions and explicit consent flows.

## Android service behavior
- Foreground services require a visible ongoing notification by Android design.
- This project keeps the service compliant with platform policy.

## Desktop UI (.exe)
- Built executable: `dist/MDMControlDesktop.exe`
- Launch it and click `Start Server` to run local API.
- Use buttons to test `Health`, `Enqueue`, `Pull`, `Complete`, and `Telemetry`.
- Default token is `dev-token-1` and default agent is `android-agent-001`.
