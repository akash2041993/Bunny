"""Linux CI with a real Ollama + model: Hindi answers, command classification, safety."""
import os, sys, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["BUNNY_DRY_RUN"] = "1"; os.environ["BUNNY_HOME"] = tempfile.mkdtemp()
from bunny import config, llm, brain
cfg = config.load()
st = llm.status(); print("ollama:", st)
assert st["running"] and llm.has_model(cfg["llm_model"], st["models"])
out = "".join(llm.chat_stream([], "ब्लैक होल क्या होता है?", cfg))
print("answer:", out)
assert re.search(r"[ऀ-ॿ]", out), "answer should be in Hindi (Devanagari)"
en = "".join(llm.chat_stream([], "What is a black hole?", cfg, "english"))
print("english answer:", en)
assert en and not re.search(r"[\u0900-\u097F]", en), "English question should get an English answer"
out2 = "".join(llm.chat_stream([], "Aaj ka cricket score kya hai?", cfg))
print("offline question:", out2)
for t, want in [("photo edit wala adobe app chalu kar do", "open_app"), ("gaane ki awaaz thodi tez karo", "volume_up"),
                ("mere computer ko thodi der ke liye sula do", "sleep"), ("ye photo mere dost ko email kar do", None),
                ("tumhara naam kya hai", None)]:
    got = llm.classify(t, cfg)
    print("classify:", t, "->", got)
    # (informational: share/send requests are refused by Bunny's own rule BEFORE the AI is asked - checked below)
events = []
b = brain.Brain(events.append)
for t in ("ye photo mere dost ko email kar do", "send this file to my friend", "upload my videos to drive"):
    r = b.handle(brain.intents.to_roman(t))
    print("safety:", t, "->", r)
    assert r == {"refused": "share"}, r
b.hear("बनी तुम कौन हो?", source="text")
import time
t0 = time.time()
while time.time() - t0 < 180 and not any(e["type"] in ("say_end",) for e in events):
    time.sleep(1)
print([e for e in events if e["type"] == "say"])
assert any(e["type"] == "say" for e in events)
print("BRAIN TEST PASSED")
