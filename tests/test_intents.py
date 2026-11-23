import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bunny import intents as I

WAKE = ["bunny", "bani", "banni", "bunni", "bonny", "buni", "bany", "baani"]
CASES = [
    ("बनी फोटोशॉप खोलो", True, {"action": "open_app", "app": "photoshop"}),
    ("Bunny, open Photoshop", True, {"action": "open_app", "app": "photoshop"}),
    ("बन्नी क्रोम बंद करो", True, {"action": "close_app", "app": "chrome"}),
    ("hey bunny close chrome", True, {"action": "close_app", "app": "chrome"}),
    ("बनी कंप्यूटर बंद कर दो", True, {"action": "shutdown"}),
    ("बनी कंप्यूटर ऑन करो", True, {"action": "wake_pc"}),
    ("Bunny computer on karo", True, {"action": "wake_pc"}),
    ("बनी आवाज़ बढ़ाओ", True, {"action": "volume_up"}),
    ("बनी आवाज़ कम करो", True, {"action": "volume_down"}),
    ("bunny volume 40 karo", True, {"action": "volume_set", "level": 40}),
    ("बनी यूट्यूब खोलो", True, {"action": "open_website", "site": "youtube", "url": "https://www.youtube.com"}),
    ("बनी फोन पे यूट्यूब खोलो", True, {"action": "phone_open_app", "app": "youtube"}),
    ("बनी प्रीमियर प्रो खोलो", True, {"action": "open_app", "app": "premiere pro"}),
    ("बनी आफ्टर इफेक्ट्स खोलो", True, {"action": "open_app", "app": "after effects"}),
    ("बनी गाना रोको", True, {"action": "media_playpause"}),
    ("बनी अगला गाना", True, {"action": "media_next"}),
    ("बनी स्क्रीनशॉट लो", True, {"action": "screenshot"}),
    ("बनी कितने बजे हैं", True, {"action": "time"}),
    ("बनी कंप्यूटर लॉक करो", True, {"action": "lock"}),
    ("बनी कंप्यूटर रीस्टार्ट करो", True, {"action": "restart"}),
    ("बनी डाउनलोड्स खोलो", True, {"action": "open_folder", "folder": "downloads"}),
    ("bunny barbarik wali file dhundo", True, {"action": "find_file", "query": "barbarik"}),
    ("बनी ब्लैक होल क्या होता है", True, None),
    ("ब्लैक होल क्या होता है", False, None),
    ("photoshop kholo bunny", True, {"action": "open_app", "app": "photoshop"}),
    ("बनी फोन रीस्टार्ट करो", True, {"action": "phone_restart"}),
    ("बनी चुप", True, {"action": "stop_talking"}),
    ("बनी वॉट्सऐप खोलो", True, {"action": "open_app", "app": "whatsapp"}),
    ("बनी ओपन फोटोशॉप", True, {"action": "open_app", "app": "photoshop"}),
    ("बनी क्लोज़ क्रोम", True, {"action": "close_app", "app": "chrome"}),
    ("बनी फोटोशॉप कैसे सीखें", True, None),
    ("बनी कंप्यूटर क्या होता है", True, None),
]
bad = 0
for text, wake, want in CASES:
    found, rest = I.find_wake(text, WAKE)
    got = I.parse(rest) if found else None
    ok = found == wake and got == want
    bad += not ok
    print("OK  " if ok else "FAIL", text, "->", rest, "->", got)
print("failures:", bad)
sys.exit(1 if bad else 0)
