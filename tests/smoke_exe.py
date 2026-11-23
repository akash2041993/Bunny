"""Windows CI: start the built Bunny.exe (dry run: no real actions), send it a spoken WAV,
and check it hears and understands it. Usage: python tests/smoke_exe.py dist/Bunny/Bunny.exe speech.wav"""
import json, os, subprocess, sys, tempfile, threading, time, urllib.request
exe, wav = sys.argv[1], sys.argv[2]
home = tempfile.mkdtemp()
env = dict(os.environ, BUNNY_DRY_RUN="1", BUNNY_HOME=home, PYTHONIOENCODING="utf-8")
proc = subprocess.Popen([exe], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
lines = []
threading.Thread(target=lambda: [lines.append(l.decode("utf-8", "replace").rstrip()) for l in proc.stdout], daemon=True).start()
base = "http://127.0.0.1:8765"
try:
    tok = None
    for _ in range(120):
        time.sleep(1)
        try:
            tok = json.load(open(os.path.join(home, "settings.json"), encoding="utf-8"))["token"]
            st = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/api/status", headers={"X-Bunny-Token": tok}), timeout=5).read())
            if st["ears"]["ready"]:
                break
            if st["ears"].get("error"):
                raise SystemExit("ears error: " + st["ears"]["error"])
        except (OSError, ValueError, KeyError):
            continue
    print("status:", st)
    assert st["ears"]["ready"], "speech-to-text did not load"
    events = []
    def listen():
        with urllib.request.urlopen(base + "/api/events?token=" + tok) as r:
            for line in r:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
    threading.Thread(target=listen, daemon=True).start()
    time.sleep(1)
    req = urllib.request.Request(base + "/api/hear?follow=1", data=open(wav, "rb").read(), method="POST",
                                 headers={"X-Bunny-Token": tok, "Content-Type": "audio/wav"})
    assert urllib.request.urlopen(req).status == 202
    t0 = time.time()
    while time.time() - t0 < 120 and not any(e["type"] == "say" for e in events):
        time.sleep(0.5)
    for e in events:
        print("event:", json.dumps(e, ensure_ascii=False))
    heard = [e["text"] for e in events if e["type"] == "heard"]
    said = [e["text"] for e in events if e["type"] == "say"]
    assert heard, "nothing heard"
    assert any("Photoshop" in s for s in said), f"did not understand: heard={heard} said={said}"
    print("EXE SMOKE TEST PASSED")
finally:
    proc.kill()
    time.sleep(1)
    print("\n".join(lines[-40:]))
