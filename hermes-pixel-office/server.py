#!/usr/bin/env python3
"""Hermes Pixel Office - server.

Reads the live Hermes state.db (read-only) and exposes it as JSON so the
pixel-art office UI can render one character per real agent session.

Run:  python server.py            (then open http://localhost:8770)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PIXEL_OFFICE_PORT", "8770"))

# Kantor Berita Finance menulis statusnya ke file ini; kita sajikan apa adanya.
KANTOR_STATUS = Path(os.environ.get(
    "KANTOR_STATUS_FILE", r"E:\Projects\kantor-finance\status.json"))

# Windows default, then the generic ~/.hermes location.
_CANDIDATES = [
    Path(os.environ.get("HERMES_HOME", "")) / "state.db" if os.environ.get("HERMES_HOME") else None,
    Path.home() / "AppData" / "Local" / "hermes" / "state.db",
    Path.home() / ".hermes" / "state.db",
]


def find_state_db() -> Path | None:
    for c in _CANDIDATES:
        if c and c.is_file():
            return c
    return None


# Recency windows that decide the character's behaviour.
WORKING_WINDOW_S = 90    # touched this recently -> mid-turn, sits at a desk
ACTIVE_WINDOW_S = 240    # touched recently -> still warm, hangs out in the lounge


def _tool_label(desc: str) -> str:
    """Turn 'tool running: execute_code' into 'execute_code'."""
    if not desc:
        return ""
    if ":" in desc:
        return desc.split(":", 1)[1].strip()
    return desc.strip()


def collect() -> dict:
    db = find_state_db()
    if db is None:
        return {"ok": False, "error": "state.db not found", "agents": [], "server_time": time.time()}

    agents: list[dict] = []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, source, display_name, model, message_count, tool_call_count,
                   input_tokens, output_tokens, started_at, ended_at, last_activity_at,
                   last_activity_description, title, estimated_cost_usd, profile_name
            FROM sessions
            ORDER BY COALESCE(last_activity_at, started_at) DESC
            """
        ).fetchall()

        for r in rows:
            last = r["last_activity_at"] or r["started_at"] or 0
            desc = r["last_activity_description"] or ""
            ended = r["ended_at"] is not None
            age = time.time() - last if last else 1e9

            # A session mid-turn right now is "working" even if the last write was a
            # minute ago (long tool calls). Otherwise fall back to recency windows.
            mid_turn = desc.startswith("tool running")
            if ended:
                status = "idle"
            elif mid_turn or age < WORKING_WINDOW_S:
                status = "working"
            elif age < ACTIVE_WINDOW_S:
                status = "active"
            else:
                status = "idle"

            # Last real tool used, for the desk label.
            tool = ""
            try:
                m = con.execute(
                    """SELECT tool_name FROM messages
                       WHERE session_id=? AND tool_name IS NOT NULL
                       ORDER BY COALESCE(timestamp,0) DESC LIMIT 1""",
                    (r["id"],),
                ).fetchone()
                if m:
                    tool = m["tool_name"] or ""
            except sqlite3.Error:
                pass

            name = r["display_name"] or r["title"] or r["id"][-6:]
            agents.append({
                "id": r["id"],
                "name": str(name)[:28],
                "source": r["source"] or "?",
                "model": r["model"] or "?",
                "status": status,
                "tool": tool or _tool_label(desc),
                "last_activity": last,
                "age_s": round(age, 1),
                "messages": r["message_count"] or 0,
                "tool_calls": r["tool_call_count"] or 0,
                "tokens_in": r["input_tokens"] or 0,
                "tokens_out": r["output_tokens"] or 0,
                "cost_usd": r["estimated_cost_usd"] or 0.0,
                "ended": ended,
            })
        con.close()
    except sqlite3.Error as e:
        return {"ok": False, "error": f"sqlite: {e}", "agents": [], "server_time": time.time()}

    return {
        "ok": True,
        "agents": agents,
        "count": len(agents),
        "working": sum(1 for a in agents if a["status"] == "working"),
        "db": str(db),
        "server_time": time.time(),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            f = HERE / "index.html"
            if not f.is_file():
                self._send(500, b"index.html missing", "text/plain; charset=utf-8")
                return
            self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        elif path in ("/kantor", "/kantor.html"):
            f = HERE / "kantor.html"
            if not f.is_file():
                self._send(404, b"kantor.html missing", "text/plain; charset=utf-8")
                return
            self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/state":
            self._send(200, json.dumps(collect()).encode("utf-8"), "application/json; charset=utf-8")
        elif path == "/api/kantor":
            self._send(200, self._kantor(), "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def _kantor(self) -> bytes:
        """Status kantor berita finance; kalau file belum ada, kirim kerangka kosong."""
        try:
            raw = KANTOR_STATUS.read_text(encoding="utf-8")
            data = json.loads(raw)
        except FileNotFoundError:
            data = {"ok": False, "error": "status.json kantor belum ada",
                    "pekerja": [], "tahap": None, "selesai": False}
        except (OSError, json.JSONDecodeError) as e:
            data = {"ok": False, "error": f"gagal baca status: {e}",
                    "pekerja": [], "tahap": None, "selesai": False}
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def log_message(self, fmt, *args):  # keep the console quiet
        pass


def main() -> None:
    db = find_state_db()
    print("Hermes Pixel Office")
    print(f"  state.db : {db if db else 'NOT FOUND'}")
    print(f"  serving  : http://localhost:{PORT}")
    print("  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nbye")
        sys.exit(0)
