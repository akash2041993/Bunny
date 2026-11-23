"""Local web server for Bunny's face.

Security:
- listens ONLY on this computer (127.0.0.1). The phone reaches it through the USB cable
  (adb reverse), so nobody on your Wi-Fi or the internet can connect;
- every API call must carry a secret token that only Bunny's own page knows;
- requests whose Host is not localhost are refused (stops websites in your browser from
  sending commands to Bunny, "DNS rebinding");
- no CORS headers: other websites can't read or call Bunny.
"""
import hmac
import json
import os
import queue
import re
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import characters, config, llm, phone, stt

_clients = []
_clients_lock = threading.Lock()
_last = {}  # last state/status events, re-sent to a page that (re)connects
_work = queue.Queue()
brain = None


def emit(ev):
    ev = dict(ev, t=time.time())
    if ev.get("type") in ("status", "devices"):
        _last[ev["type"]] = ev
    with _clients_lock:
        for q in list(_clients):
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass


def _worker():
    while True:
        kind, payload, follow = _work.get()
        try:
            if kind == "audio":
                emit({"type": "state", "state": "hearing"})
                text, lang = stt.transcribe(payload)
                if not text:
                    emit({"type": "ignored", "heard": ""})
                    continue
                print("Heard:", text)
                brain.hear(text, follow=follow, spoken=lang)
            else:
                print("Typed:", payload)
                brain.hear(payload, follow=True, source="text")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            emit({"type": "error", "text": str(e)})


_HOST_OK = re.compile(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$", re.I)


class Handler(BaseHTTPRequestHandler):
    server_version = "Bunny"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------- helpers
    def _send(self, code, body=b"", ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        return bool(_HOST_OK.match(self.headers.get("Host", "")))

    def _token_ok(self, query):
        want = config.load()["token"]
        got = self.headers.get("X-Bunny-Token") or (query.get("token") or [""])[0]
        return hmac.compare_digest(got.encode(), want.encode())

    def _guard(self, query, need_token=True):
        if not self._host_ok():
            self._send(403, {"error": "Bunny only answers on localhost"})
            return False
        if need_token and not self._token_ok(query):
            self._send(401, {"error": "wrong token"})
            return False
        return True

    # ---------------------------------------------------------- routes
    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            if not self._guard(q, need_token=False):
                return
            with open(os.path.join(config.web_dir(), "index.html"), "r", encoding="utf-8") as f:
                page = f.read()
            cfg = config.load()
            boot = {"token": cfg["token"], "version": config.VERSION, "follow": cfg.get("follow_up_seconds", 8),
                    "lang": cfg.get("reply_language", "auto"), "character": cfg.get("character", "bunny"),
                    "characters": characters.public()}
            page = page.replace("/*BOOT*/null", json.dumps(boot))
            self._send(200, page, "text/html; charset=utf-8")
            return
        if u.path == "/icon.png":
            if not self._guard(q, need_token=False):
                return
            with open(os.path.join(config.web_dir(), "icon.png"), "rb") as f:
                self._send(200, f.read(), "image/png")
            return
        if u.path == "/manifest.json":
            if not self._guard(q, need_token=False):
                return
            self._send(200, {"name": "Bunny", "short_name": "Bunny", "start_url": "/", "display": "fullscreen",
                             "orientation": "landscape", "background_color": "#0b1026", "theme_color": "#0b1026",
                             "icons": [{"src": "/icon.png", "sizes": "256x256", "type": "image/png"}]},
                       "application/manifest+json")
            return
        if u.path == "/api/events":
            if not self._guard(q):
                return
            self._events()
            return
        if u.path == "/api/status":
            if not self._guard(q):
                return
            self._send(200, status())
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 8 * 1024 * 1024:
            self._send(413, {"error": "too big"})
            return
        body = self.rfile.read(n) if n else b""
        if not self._guard(q):
            return
        follow = (q.get("follow") or ["0"])[0] == "1"
        if u.path == "/api/hear":
            if not body.startswith(b"RIFF"):
                self._send(400, {"error": "send a WAV file"})
                return
            _work.put(("audio", body, follow))
            self._send(202, {"ok": True})
            return
        if u.path == "/api/character":
            try:
                cid = (json.loads(body.decode() or "{}").get("id") or "").strip()
            except ValueError:
                cid = ""
            ok = brain.switch(cid)
            if ok:
                brain.say(brain.m("switched", name=characters.get(cid)["name"]), mood="happy")
            self._send(200 if ok else 400, {"ok": ok})
            return
        if u.path == "/api/text":
            try:
                text = (json.loads(body.decode() or "{}").get("text") or "").strip()[:500]
            except ValueError:
                text = ""
            if text:
                _work.put(("text", text, True))
            self._send(202, {"ok": bool(text)})
            return
        self._send(404, {"error": "not found"})

    def _events(self):
        q = queue.Queue(maxsize=200)
        with _clients_lock:
            _clients.append(q)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.close_connection = True
            for ev in list(_last.values()) + [{"type": "hello", "status": status()}]:
                self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                    data = f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    data = ": ping\n\n"
                self.wfile.write(data.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with _clients_lock:
                if q in _clients:
                    _clients.remove(q)


def status():
    cfg = config.load()
    return {"version": config.VERSION, "ears": stt.status, "brain": llm.status(), "model": cfg.get("llm_model"),
            "phone": phone.state.get("devices"), "adb": bool(phone.state.get("adb"))}


class _Server(ThreadingHTTPServer):
    """Only Bunny may use this port: no sharing with another program (Windows allows sharing otherwise)."""
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def server_bind(self):
        if os.name == "nt":
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def serve(port=config.PORT):
    from .brain import Brain
    global brain
    brain = Brain(emit)
    threading.Thread(target=_worker, daemon=True).start()
    return _Server(("127.0.0.1", port), Handler)
