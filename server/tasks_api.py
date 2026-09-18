"""API задач для хаба Ozon (только stdlib). Слушает 127.0.0.1:8090, nginx проксирует /api/."""
import json, os, threading, uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STORE = Path(os.environ.get("TASKS_STORE", "/var/lib/ozon/tasks.json"))
SEED = Path(os.environ.get("TASKS_SEED", "/var/www/ozon/data.json"))
LOCK = threading.Lock()
FIELDS = ("title", "description", "type", "priority")


def load():
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []


def save(tasks):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp"); tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(STORE)


def merged():
    """Хранилище + новые авто-задачи из data.json (по id, статусы не затираются)."""
    tasks = load(); ids = {t["id"] for t in tasks}
    try:
        seed = json.loads(SEED.read_text(encoding="utf-8")).get("tasks_seed", [])
    except Exception:
        seed = []
    new = [t for t in seed if t["id"] not in ids]
    if new:
        tasks += new; save(tasks)
    return tasks


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

    def _body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except Exception:
            return None

    def do_GET(self):
        if self.path.rstrip("/") == "/tasks":
            with LOCK: self._send(200, merged())
        else: self._send(404, {"error": "not found"})

    def do_POST(self):
        b = self._body()
        if self.path.rstrip("/") != "/tasks" or not isinstance(b, dict) or not str(b.get("title", "")).strip():
            return self._send(400, {"error": "bad request"})
        t = {"id": "m-" + uuid.uuid4().hex[:8], "created": date.today().isoformat(), "done": False, "done_at": None, "source": "manual",
             "title": str(b["title"])[:200], "description": str(b.get("description", ""))[:1000],
             "type": str(b.get("type") or "Прочее")[:60], "priority": b.get("priority") if b.get("priority") in ("high", "medium", "low") else "medium"}
        with LOCK:
            tasks = merged(); tasks.append(t); save(tasks)
        self._send(201, t)

    def do_PATCH(self):
        b = self._body(); parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "tasks" or not isinstance(b, dict):
            return self._send(400, {"error": "bad request"})
        with LOCK:
            tasks = merged(); t = next((x for x in tasks if x["id"] == parts[1]), None)
            if not t: return self._send(404, {"error": "no task"})
            if "done" in b:
                t["done"] = bool(b["done"]); t["done_at"] = date.today().isoformat() if t["done"] else None
            for k in FIELDS:
                if k in b and isinstance(b[k], str): t[k] = b[k][:1000]
            save(tasks)
        self._send(200, t)

    def log_message(self, *a): pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", 8090))), H).serve_forever()
