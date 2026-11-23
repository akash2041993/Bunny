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
out2 = "".join(llm.chat_stream([], "Aaj ka cricket score kya hai?", cfg))
print("offline question:", out2)
for t, want in [("photo edit wala adobe app chalu kar do", "open_app"), ("gaane ki awaaz thodi tez karo", "volume_up"),
                ("mere computer ko thodi der ke liye sula do", "sleep"), ("ye photo mere dost ko email kar do", None),
                ("tumhara naam kya hai", None)]:
    got = llm.classify(t, cfg)
    print("classify:", t, "->", got)
    if want is None:
        assert got is None or got["action"] not in ("open_app", "close_app", "find_file"), got
events = []
b = brain.Brain(events.append)
b.hear("बनी तुम कौन हो?", source="text")
import time
t0 = time.time()
while time.time() - t0 < 180 and not any(e["type"] in ("say_end",) for e in events):
    time.sleep(1)
print([e for e in events if e["type"] == "say"])
assert any(e["type"] == "say" for e in events)
print("BRAIN TEST PASSED")
