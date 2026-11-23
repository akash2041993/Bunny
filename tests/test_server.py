"""Server + brain test with a fake Ollama (no real AI, no real actions: BUNNY_DRY_RUN)."""
import json, os, sys, tempfile, threading, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["BUNNY_DRY_RUN"] = "1"
os.environ["BUNNY_HOME"] = tempfile.mkdtemp()
import fake_ollama
fo = fake_ollama.start()
from bunny import config, server, actions_pc
config.save({"ollama_url": f"http://127.0.0.1:{fo.server_address[1]}"})
httpd = server.serve(0)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
tok = config.load()["token"]
events = []

def listen():
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/events?token={tok}")
    with urllib.request.urlopen(req) as r:
        for line in r:
            line = line.decode().strip()
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
threading.Thread(target=listen, daemon=True).start()
time.sleep(0.5)

def call(path, body=None, headers=None, host=None):
    h = {"X-Bunny-Token": tok, "Content-Type": "application/json"}
    h.update(headers or {})
    if host: h["Host"] = host
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode() if body is not None else None, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def text(t, wait=1.0):
    n = len(events)
    assert call("/api/text", {"text": t})[0] == 202
    time.sleep(wait)
    return events[n:]

def says(evs): return [e["text"] for e in evs if e["type"] == "say"]

# security
assert call("/api/status", headers={"X-Bunny-Token": "wrong"})[0] == 401, "token must be required"
assert call("/api/status", host="evil.example.com")[0] == 403, "foreign Host must be refused"
st, page = call("/", host="localhost:8765")
assert st == 200 and tok in page and "/*BOOT*/null" not in page
st, page = call("/", host="evil.example.com:8765")
assert st == 403
print("security ok")

ev = text("photoshop kholo"); print(says(ev)); assert actions_pc.DONE and "Photoshop" in says(ev)[0]
ev = text("क्रोम बंद करो"); print(says(ev)); assert "बंद" in says(ev)[0]
ev = text("कंप्यूटर बंद करो"); print(says(ev)); assert "पक्का" in says(ev)[0] and not any("shutdown" in str(d) for d in actions_pc.DONE)
ev = text("हाँ", 1.5); print(says(ev)); assert any(d[0] == "shutdown" for d in actions_pc.DONE if isinstance(d, list)), actions_pc.DONE
ev = text("ye file mere dost ko whatsapp pe bhejo"); print(says(ev)); assert "शेयर" in says(ev)[0]
ev = text("downloads ki saari files delete karo"); print(says(ev)); assert "डिलीट" in says(ev)[0]
ev = text("blaik hol kya hota hai", 2); print(says(ev)); assert len(says(ev)) >= 2 and not any("*" in s or "🐰" in s for s in says(ev))
assert any(e["type"] == "say_end" for e in ev)
ev = text("kitne baje hain"); print(says(ev)); assert "बज" in says(ev)[0]
ev = text("photo wala app chalu kar do please"); print(says(ev))  # via the AI classifier
print("ALL SERVER TESTS PASSED")
