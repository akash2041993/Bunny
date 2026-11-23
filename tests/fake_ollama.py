"""A tiny stand-in for Ollama, for tests."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            out = json.dumps({"models": [{"name": "gemma3:4b"}]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        H.last = body
        if body.get("format") == "json":
            text = body["messages"][-1]["content"]
            ans = {"action": "open_app", "app": "photoshop"} if "photo" in text else {"action": "none"}
            out = json.dumps({"message": {"content": json.dumps(ans)}, "done": True}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
            return
        self.send_response(200); self.end_headers()
        for piece in ["ब्लैक होल ", "अंतरिक्ष की वो जगह है **जहाँ** ", "से रोशनी भी नहीं निकल सकती। ", "बहुत मज़ेदार है ना? 🐰"]:
            self.wfile.write((json.dumps({"message": {"content": piece}, "done": False}) + "\n").encode())
        self.wfile.write((json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode())


def start(port=0):
    s = ThreadingHTTPServer(("127.0.0.1", port), H)
    import threading
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s
