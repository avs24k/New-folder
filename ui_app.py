import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_AGENT_ID = "android-agent-001"
DEFAULT_TOKEN = "dev-token-1"


class MDMDesktopUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MDM Control Desktop")
        self.geometry("980x680")
        self.minsize(940, 620)

        self.server_proc = None
        self.last_command_id = ""

        self.base_url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        self.agent_id_var = tk.StringVar(value=DEFAULT_AGENT_ID)
        self.token_var = tk.StringVar(value=DEFAULT_TOKEN)
        self.cmd_name_var = tk.StringVar(value="health.ping")
        self.cmd_args_var = tk.StringVar(value="{}")
        self.complete_status_var = tk.StringVar(value="success")
        self.complete_result_var = tk.StringVar(value='{"ok": true}')
        self.telemetry_type_var = tk.StringVar(value="agent.heartbeat")
        self.telemetry_data_var = tk.StringVar(value='{"status": "ok"}')

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        cfg = ttk.LabelFrame(root, text="Connection", padding=10)
        cfg.pack(fill="x")

        ttk.Label(cfg, text="Base URL").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(cfg, textvariable=self.base_url_var, width=40).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(cfg, text="Agent ID").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        ttk.Entry(cfg, textvariable=self.agent_id_var, width=24).grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(cfg, text="Token").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(cfg, textvariable=self.token_var, width=40, show="*").grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Button(cfg, text="Start Server", command=self.start_server).grid(row=1, column=2, sticky="ew", padx=(16, 8), pady=4)
        ttk.Button(cfg, text="Stop Server", command=self.stop_server).grid(row=1, column=3, sticky="ew", pady=4)

        cfg.columnconfigure(1, weight=1)
        cfg.columnconfigure(3, weight=1)

        actions = ttk.LabelFrame(root, text="Actions", padding=10)
        actions.pack(fill="x", pady=(10, 0))

        top_btns = ttk.Frame(actions)
        top_btns.pack(fill="x", pady=(0, 8))
        ttk.Button(top_btns, text="Health", command=self.health).pack(side="left", padx=(0, 8))
        ttk.Button(top_btns, text="Pull Commands", command=self.pull_commands).pack(side="left", padx=(0, 8))
        ttk.Button(top_btns, text="Ingest Telemetry", command=self.ingest_telemetry).pack(side="left", padx=(0, 8))

        cmdf = ttk.LabelFrame(actions, text="Command", padding=10)
        cmdf.pack(fill="x", pady=(0, 8))
        ttk.Label(cmdf, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(cmdf, textvariable=self.cmd_name_var, width=24).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(cmdf, text="Args JSON").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        ttk.Entry(cmdf, textvariable=self.cmd_args_var).grid(row=0, column=3, sticky="ew", pady=4)
        ttk.Button(cmdf, text="Enqueue", command=self.enqueue_command).grid(row=0, column=4, padx=(16, 0), pady=4)
        cmdf.columnconfigure(1, weight=1)
        cmdf.columnconfigure(3, weight=2)

        compf = ttk.LabelFrame(actions, text="Complete", padding=10)
        compf.pack(fill="x", pady=(0, 8))
        ttk.Label(compf, text="Command ID").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.cmd_id_entry = ttk.Entry(compf, width=44)
        self.cmd_id_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(compf, text="Status").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        ttk.Combobox(compf, textvariable=self.complete_status_var, values=["success", "error"], width=10, state="readonly").grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(compf, text="Result JSON").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(compf, textvariable=self.complete_result_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        ttk.Button(compf, text="Complete", command=self.complete_command).grid(row=1, column=4, padx=(16, 0), pady=4)
        compf.columnconfigure(1, weight=1)

        telf = ttk.LabelFrame(actions, text="Telemetry", padding=10)
        telf.pack(fill="x")
        ttk.Label(telf, text="Event Type").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(telf, textvariable=self.telemetry_type_var, width=24).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(telf, text="Data JSON").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        ttk.Entry(telf, textvariable=self.telemetry_data_var).grid(row=0, column=3, sticky="ew", pady=4)
        telf.columnconfigure(1, weight=1)
        telf.columnconfigure(3, weight=2)

        logsf = ttk.LabelFrame(root, text="Logs", padding=10)
        logsf.pack(fill="both", expand=True, pady=(10, 0))
        self.log_widget = tk.Text(logsf, wrap="word", height=16)
        self.log_widget.pack(fill="both", expand=True)

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_widget.insert("end", f"[{ts}] {msg}\n")
        self.log_widget.see("end")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token_var.get().strip()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, payload=None):
        url = self.base_url_var.get().rstrip("/") + path
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url=url, data=body, method=method, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as ex:
            content = ex.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {ex.code}: {content}") from ex
        except Exception as ex:
            raise RuntimeError(str(ex)) from ex

    def _run_action(self, fn):
        def worker():
            try:
                result = fn()
                self.after(0, lambda: self.log(f"OK: {json.dumps(result, indent=2)}"))
            except Exception as ex:
                self.after(0, lambda: self.log(f"ERROR: {ex}"))

        threading.Thread(target=worker, daemon=True).start()

    def health(self):
        self._run_action(lambda: self._request("GET", "/health"))

    def enqueue_command(self):
        def action():
            args = json.loads(self.cmd_args_var.get().strip() or "{}")
            payload = {
                "payload": {
                    "name": self.cmd_name_var.get().strip(),
                    "args": args,
                },
                "envelope": {
                    "ts": int(time.time()),
                    "sig": "replace-with-real-signature",
                },
            }
            out = self._request("POST", f"/agents/{self.agent_id_var.get().strip()}/commands:enqueue", payload)
            cmd_id = out.get("id", "")
            if cmd_id:
                self.last_command_id = cmd_id
                self.after(0, lambda: self._set_command_id(cmd_id))
            return out

        self._run_action(action)

    def pull_commands(self):
        def action():
            out = self._request("GET", f"/agents/{self.agent_id_var.get().strip()}/commands:pull")
            cmds = out.get("commands", [])
            if cmds:
                cmd_id = cmds[0].get("id", "")
                if cmd_id:
                    self.last_command_id = cmd_id
                    self.after(0, lambda: self._set_command_id(cmd_id))
            return out

        self._run_action(action)

    def complete_command(self):
        def action():
            command_id = self.cmd_id_entry.get().strip() or self.last_command_id
            if not command_id:
                raise RuntimeError("Command ID is required")
            result = json.loads(self.complete_result_var.get().strip() or "{}")
            payload = {
                "status": self.complete_status_var.get().strip(),
                "result": result,
            }
            return self._request(
                "POST",
                f"/agents/{self.agent_id_var.get().strip()}/commands/{command_id}:complete",
                payload,
            )

        self._run_action(action)

    def ingest_telemetry(self):
        def action():
            data = json.loads(self.telemetry_data_var.get().strip() or "{}")
            payload = {
                "events": [
                    {
                        "ts": int(time.time()),
                        "event_type": self.telemetry_type_var.get().strip(),
                        "data": data,
                    }
                ]
            }
            return self._request("POST", f"/agents/{self.agent_id_var.get().strip()}/telemetry:ingest", payload)

        self._run_action(action)

    def _set_command_id(self, command_id: str):
        self.cmd_id_entry.delete(0, "end")
        self.cmd_id_entry.insert(0, command_id)

    def start_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self.log("Server already running.")
            return

        env = os.environ.copy()
        env.setdefault("MDM_DB_PATH", str(BASE_DIR / "data" / "mdm.db"))

        cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"]
        self.server_proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.log("Server start requested.")
        threading.Thread(target=self._read_server_logs, daemon=True).start()

    def _read_server_logs(self):
        if not self.server_proc or not self.server_proc.stdout:
            return
        for line in self.server_proc.stdout:
            text = line.rstrip()
            if text:
                self.after(0, lambda t=text: self.log(f"SERVER: {t}"))

    def stop_server(self):
        if not self.server_proc or self.server_proc.poll() is not None:
            self.log("Server is not running.")
            return
        self.server_proc.terminate()
        try:
            self.server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.server_proc.kill()
        self.log("Server stopped.")

    def on_close(self):
        if self.server_proc and self.server_proc.poll() is None:
            if messagebox.askyesno("Exit", "Server is running. Stop server and exit?"):
                self.stop_server()
            else:
                return
        self.destroy()


if __name__ == "__main__":
    app = MDMDesktopUI()
    app.mainloop()
