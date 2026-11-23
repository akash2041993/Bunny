"""Open the face in headless Chromium with a fake microphone; check mic -> voice detection -> upload,
events -> face states, and take screenshots at S10e size."""
import json, os, sys, tempfile, threading, time, wave, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["BUNNY_DRY_RUN"] = "1"; os.environ["BUNNY_HOME"] = tempfile.mkdtemp()
import fake_ollama
fo = fake_ollama.start()
from bunny import config, server
config.save({"ollama_url": f"http://127.0.0.1:{fo.server_address[1]}"})
got = []
def fake_transcribe(b):
    with wave.open(io.BytesIO(b)) as w:
        got.append((w.getframerate(), w.getnchannels(), w.getnframes() / w.getframerate()))
    return "बनी ब्लैक होल क्या होता है" if len(got) == 1 else ""
server.stt.transcribe = fake_transcribe
server.stt.status["ready"] = True
httpd = server.serve(0); port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
out = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/work/shots"
os.makedirs(out, exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                f"--use-file-for-fake-audio-capture={sys.argv[2] if len(sys.argv) > 2 else '/home/claude/work/fake_mic.wav'}",
                                "--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 760, "height": 360}, device_scale_factor=2, permissions=["microphone"])
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(f"http://localhost:{port}/")
    pg.screenshot(path=f"{out}/0_start.png")
    pg.click("#start")
    time.sleep(1.2)
    pg.screenshot(path=f"{out}/1_happy.png")
    t0 = time.time()
    while not got and time.time() - t0 < 12:
        time.sleep(0.2)
    assert got, "the page never sent any audio"
    print("audio received:", got[0])
    assert got[0][0] == 16000 and got[0][1] == 1 and 0.8 < got[0][2] < 4, got[0]
    time.sleep(0.4)
    pg.screenshot(path=f"{out}/2_thinking_or_speaking.png")
    time.sleep(2.5)
    pg.screenshot(path=f"{out}/3_answer.png")
    said = pg.inner_text("#said"); you = pg.inner_text("#you")
    print("you:", you, "| said:", said)
    assert "ब्लैक होल" in you and said
    for s in ["listening", "sleep", "confused", "thinking"]:
        pg.evaluate(f"setState('{s}')"); time.sleep(0.6)
        pg.screenshot(path=f"{out}/4_{s}.png")
    pg.evaluate("talking=true; setState('speaking')"); time.sleep(0.3); pg.screenshot(path=f"{out}/5_speaking.png")
    ctx2 = b.new_context(viewport={"width": 360, "height": 740}, device_scale_factor=2)
    p2 = ctx2.new_page(); p2.goto(f"http://localhost:{port}/"); p2.evaluate("document.getElementById('start').classList.add('gone')"); time.sleep(0.5)
    p2.screenshot(path=f"{out}/6_portrait.png")
    print("page errors:", errs)
    assert not [e for e in errs if "favicon" not in e]
    b.close()
print("FACE TEST PASSED")
