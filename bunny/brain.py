"""What Bunny does with what it hears: wake word -> safety rules -> command or AI answer."""
import random
import re
import threading
import time

from . import actions_pc as pc
from . import characters, config, intents, llm, phone

MSG = {
    "wake": (["हाँ, बोलो?", "जी, बोलिए!", "हाँ {user}, बोलो?"], ["Yes?", "Yes {user}, tell me!"],
             ["Haan, bolo?", "Ji, boliye!", "Haan {user}, bolo?"]),
    "opened": ("{app} खोल रहा हूँ।", "Opening {app}.", "{app} khol raha hoon."),
    "not_found": ("मुझे इस कंप्यूटर पर {app} नहीं मिला।", "I couldn't find {app} on this computer.",
                  "Mujhe is computer pe {app} nahi mila."),
    "closed": ("{app} बंद कर दिया।", "Closed {app}.", "{app} band kar diya."),
    "not_running": ("{app} तो खुला ही नहीं है।", "{app} isn't open.", "{app} to khula hi nahi hai."),
    "close_failed": ("{app} बंद नहीं हुआ, शायद वो सेव करने का पूछ रहा है।",
                     "{app} didn't close, maybe it is asking you to save.",
                     "{app} band nahi hua, shayad save karne ka pooch raha hai."),
    "website": ("{site} खोल रहा हूँ।", "Opening {site}.", "{site} khol raha hoon."),
    "folder": ("{folder} फ़ोल्डर खोल दिया।", "Opened your {folder} folder.", "{folder} folder khol diya."),
    "file_found": ("{name} मिल गई, खोल रहा हूँ।", "Found {name}, opening it.", "{name} mil gayi, khol raha hoon."),
    "file_many": (" ऐसी {n} फ़ाइलें मिलीं, सबसे नई खोली है।", " I found {n} matches and opened the newest.",
                  " Aisi {n} files mili, sabse nayi kholi hai."),
    "file_none": ("{query} नाम की कोई फ़ाइल नहीं मिली।", "No file named {query} found.",
                  "{query} naam ki koi file nahi mili."),
    "volume_up": ("आवाज़ बढ़ा दी।", "Volume up.", "Awaaz badha di."),
    "volume_down": ("आवाज़ कम कर दी।", "Volume down.", "Awaaz kam kar di."),
    "volume_set": ("आवाज़ {level} पर कर दी।", "Volume set to {level}.", "Awaaz {level} pe kar di."),
    "mute": ("आवाज़ बंद कर दी।", "Muted.", "Awaaz band kar di."),
    "unmute": ("आवाज़ वापस चालू।", "Sound is back on.", "Awaaz wapas chalu."),
    "media_playpause": ("ठीक है।", "Okay.", "Theek hai."),
    "media_next": ("अगला।", "Next.", "Agla."),
    "media_prev": ("पिछला।", "Previous.", "Pichla."),
    "screenshot": ("स्क्रीनशॉट ले लिया, Pictures के Screenshots फ़ोल्डर में है।",
                   "Screenshot saved in Pictures, Screenshots.", "Screenshot le liya, Pictures ke Screenshots folder mein hai."),
    "lock": ("कंप्यूटर लॉक कर दिया।", "Computer locked.", "Computer lock kar diya."),
    "show_desktop": ("डेस्कटॉप दिखा दिया।", "Here is the desktop.", "Desktop dikha diya."),
    "confirm_shutdown": ("क्या पक्का कंप्यूटर बंद करना है? हाँ या ना बोलो।",
                         "Do you really want to shut down the computer? Say yes or no.",
                         "Pakka computer band karna hai? Haan ya na bolo."),
    "confirm_restart": ("क्या पक्का कंप्यूटर रीस्टार्ट करना है? हाँ या ना बोलो।",
                        "Restart the computer? Say yes or no.", "Pakka computer restart karna hai? Haan ya na bolo."),
    "confirm_sleep": ("कंप्यूटर को सुला दूँ? हाँ या ना बोलो।", "Put the computer to sleep? Say yes or no.",
                      "Computer ko sula doon? Haan ya na bolo."),
    "confirm_phone_restart": ("फ़ोन रीस्टार्ट कर दूँ? हाँ या ना बोलो।", "Restart the phone? Say yes or no.",
                              "Phone restart kar doon? Haan ya na bolo."),
    "shutdown": ("ठीक है, तीस सेकंड में कंप्यूटर बंद हो जाएगा। रोकना हो तो बोलो, बनी कैंसल करो।",
                 "Okay, the computer shuts down in 30 seconds. Say: Bunny, cancel, to stop it.",
                 "Theek hai, tees second mein computer band ho jayega. Rokna ho to bolo, Bunny cancel karo."),
    "restart": ("ठीक है, तीस सेकंड में कंप्यूटर रीस्टार्ट होगा।", "Okay, restarting in 30 seconds.",
                "Theek hai, tees second mein restart hoga."),
    "sleep": ("कंप्यूटर को सुला रहा हूँ। गुड नाइट!", "Putting the computer to sleep. Good night!",
              "Computer ko sula raha hoon. Good night!"),
    "cancelled": ("ठीक है, नहीं करता।", "Okay, I won't.", "Theek hai, nahi karta."),
    "cancel_shutdown": ("शटडाउन रोक दिया।", "Shutdown cancelled.", "Shutdown rok diya."),
    "wake_pc": ("कंप्यूटर तो पहले से चालू है, मैं इसी पर चल रहा हूँ!", "The computer is already on, I'm running on it!",
                "Computer to pehle se chalu hai, main isi pe chal raha hoon!"),
    "phone_opened": ("फ़ोन पर {app} खोल दिया।", "Opened {app} on the phone.", "Phone pe {app} khol diya."),
    "no_phone": ("फ़ोन केबल से जुड़ा हुआ नहीं है।", "The phone isn't connected by cable.",
                 "Phone cable se juda hua nahi hai."),
    "phone_volume_up": ("फ़ोन की आवाज़ बढ़ा दी।", "Phone volume up.", "Phone ki awaaz badha di."),
    "phone_volume_down": ("फ़ोन की आवाज़ कम कर दी।", "Phone volume down.", "Phone ki awaaz kam kar di."),
    "phone_screenshot": ("फ़ोन का स्क्रीनशॉट कंप्यूटर के Pictures, Bunny फ़ोल्डर में रख दिया।",
                         "Saved the phone screenshot in Pictures, Bunny on the computer.",
                         "Phone ka screenshot computer ke Pictures, Bunny folder mein rakh diya."),
    "phone_bunny": ("मैं वापस आ गया!", "I'm back!", "Main wapas aa gaya!"),
    "switched": ("नमस्ते! मैं {name} हूँ। बोलो, क्या करूँ?", "Hi! I'm {name}. What can I do?",
                 "Namaste! Main {name} hoon. Bolo, kya karoon?"),
    "phone_restart": ("फ़ोन रीस्टार्ट हो रहा है, थोड़ी देर में वापस आता हूँ।", "Restarting the phone, back soon.",
                      "Phone restart ho raha hai, thodi der mein wapas aata hoon."),
    "go_sleep": ("ठीक है, मैं सोने जा रहा हूँ। बुलाना हो तो बनी बोलना।", "Okay, going to sleep. Say Bunny to wake me.",
                 "Theek hai, main sone ja raha hoon. Bulana ho to Bunny bolna."),
    "brain_off": ("मेरा दिमाग, यानी Ollama, अभी चालू नहीं है। कंप्यूटर पर Ollama खोल दो।",
                  "My brain, Ollama, is not running. Please start Ollama on the computer.",
                  "Mera dimaag, yaani Ollama, abhi chalu nahi hai. Computer pe Ollama khol do."),
    "brain_loading": ("मेरा दिमाग अभी डाउनलोड हो रहा है, थोड़ा इंतज़ार करो।", "My brain is still downloading, please wait.",
                      "Mera dimaag abhi download ho raha hai, thoda intezaar karo."),
    "no_share": ("मैं कोई भी फ़ाइल कहीं भेज, अपलोड या शेयर नहीं कर सकता। ये मेरी सुरक्षा का नियम है।",
                 "I can't send, upload or share files anywhere. That's my safety rule.",
                 "Main koi bhi file kahin bhej, upload ya share nahi kar sakta. Ye meri suraksha ka niyam hai."),
    "no_delete": ("मैं फ़ाइलें डिलीट नहीं करता, ताकि तुम्हारा कुछ भी गलती से न मिटे।",
                  "I don't delete files, so nothing gets lost by mistake.",
                  "Main files delete nahi karta, taaki tumhara kuch bhi galti se na mite."),
    "failed": ("माफ़ करना, ये नहीं हो पाया।", "Sorry, that didn't work.", "Sorry, ye nahi ho paya."),
    "ai_error": ("माफ़ करना, मेरे दिमाग में कुछ गड़बड़ हो गई।", "Sorry, something went wrong in my brain.",
                 "Sorry, mere dimaag mein kuch gadbad ho gayi."),
}
_LANGS = {"hindi": 0, "english": 1, "hinglish": 2}

YES = {"haan", "han", "ha", "haa", "hanji", "haanji", "yes", "yeah", "ok", "okay", "theek", "thik", "bilkul", "pakka",
       "sure", "ji", "karo", "kar", "yep", "yup", "ahead", "confirm"}
NO = {"nahi", "nahin", "nai", "na", "no", "mat", "cancel", "rehne", "rahne", "ruko", "nope"}
SHARE = re.compile(r"\b(send|bhejo|bhej|bhejna|bhejdo|share|shayar|sheyar|upload|aplod|email|mail|forward|"
                   r"post karo|whatsapp pe bhej|telegram pe bhej|leak|transfer)\b")
DELETE = re.compile(r"\b(delete|dilit|dileet|mitao|mita do|remove file|format|erase)\b")
_SENT = re.compile(r"(.+?[।.!?\n])(\s+|$)", re.S)


class Brain:
    def __init__(self, emit):
        self.emit = emit
        self.history = []
        self.pending = None  # an action waiting for "yes"
        self.gen = 0
        self.lock = threading.Lock()
        self.brain_note = None  # "loading" while the AI model downloads

    # ------------------------------------------------------------ talking
    def lang(self):
        fixed = config.load().get("reply_language", "auto")
        if fixed in _LANGS:
            return fixed
        return getattr(self, "turn_lang", "hindi")

    def m(self, key, **kw):
        v = MSG[key][_LANGS.get(self.lang(), 0)]
        if isinstance(v, list):
            v = random.choice(v)
        kw.setdefault("user", config.load().get("user_name", ""))
        return v.format(**kw)

    def say(self, text, mood=None, final=True):
        self.emit({"type": "say", "text": text, "lang": self.lang(), "mood": mood, "final": final})

    # ------------------------------------------------------------ main entry
    def hear(self, text, follow=False, source="voice", spoken=None):
        """text: what speech-to-text heard. follow: the face says we are inside the 'talk again' window.
        spoken: 'en' / 'hi' from speech-to-text, so Bunny answers in the language you used."""
        cfg = config.load()
        self.turn_lang = reply_language(text, spoken)
        current = cfg.get("character", "bunny")
        found, rest, who = False, intents.to_roman(text), None
        # the current character first, then the others (calling another name switches to it)
        order = [current] + [c for c in characters.ORDER if c != current]
        for cid in order:
            words = characters.get(cid)["wake"] + (cfg.get("wake_words") or [])
            f, r = intents.find_wake(text, words)
            if f:
                found, rest, who = True, r, cid
                break
        if not (found or follow or source != "voice"):
            self.emit({"type": "ignored", "heard": text})
            return None
        self.emit({"type": "heard", "text": text})
        if who and who != current:
            self.switch(who)
            if not rest:
                self.say(self.m("switched", name=characters.get(who)["name"]), mood="happy")
                return {"switched": who}
        if not rest:
            self.say(self.m("wake"), mood="listening")
            return {"wake": True}
        return self.handle(rest)

    def switch(self, cid):
        if cid not in characters.CHARACTERS:
            return False
        config.save({"character": cid})
        self.history = []  # a new friend starts a new conversation
        self.emit({"type": "character", "id": cid, "name": characters.get(cid)["name"]})
        return True

    def handle(self, rest):
        words = set(rest.split())
        if self.pending:
            act, self.pending = self.pending, None
            if words & YES and not words & NO:
                return self.run(act, confirmed=True)
            if words & NO or len(words) <= 2:
                self.say(self.m("cancelled"), mood="happy")
                return {"cancelled": act}
        if SHARE.search(rest):
            self.say(self.m("no_share"), mood="confused")
            return {"refused": "share"}
        if DELETE.search(rest):
            self.say(self.m("no_delete"), mood="confused")
            return {"refused": "delete"}
        cfg = config.load()
        apps = list(pc.installed_apps().keys()) + list(cfg.get("custom_apps", {}).keys())
        act = intents.parse(rest, installed_apps=apps)
        if act is None and (words & (intents.OPEN | intents.CLOSE)) and llm.status()["running"]:
            act = llm.classify(rest, cfg)
            if act and act["action"] in ("open_app", "close_app"):
                key, _ = intents._best_name(act.get("app", "").lower().split(), intents.PC_APPS, extra=apps)
                act = {"action": act["action"], "app": key} if key else None
        if act:
            return self.run(act)
        self.chat(rest)
        return {"chat": rest}

    # ------------------------------------------------------------ commands
    def run(self, act, confirmed=False):
        a = act["action"]
        if a in intents.CONFIRM and not confirmed:
            self.pending = act
            self.say(self.m("confirm_" + a), mood="listening")
            self.emit({"type": "listen"})  # keep listening for the answer
            return {"confirm": a}
        self.emit({"type": "action", "action": act})
        cfg = config.load()
        try:
            ok, text = self._do(act, cfg)
        except Exception as e:  # noqa: BLE001 - never crash Bunny
            print("Action failed:", act, e)
            ok, text = False, self.m("failed")
        if text:
            self.say(text, mood="happy" if ok else "confused")
        return {"action": act, "ok": ok}

    def _do(self, act, cfg):
        a = act["action"]
        app = act.get("app", "")
        nice = app.title() if app and app.islower() else app
        if a == "open_app":
            ok, _ = pc.open_app(app, cfg.get("custom_apps"))
            return ok, self.m("opened" if ok else "not_found", app=nice)
        if a == "close_app":
            ok, _ = pc.close_app(app)
            return bool(ok), self.m("closed" if ok else "not_running" if ok is None else "close_failed", app=nice)
        if a == "open_website":
            return pc.open_website(act["url"]), self.m("website", site=act["site"].title())
        if a == "open_folder":
            return pc.open_folder(act["folder"]), self.m("folder", folder=act["folder"].title())
        if a == "find_file":
            path, n = pc.find_file(act["query"])
            if not path:
                return False, self.m("file_none", query=act["query"])
            import os
            t = self.m("file_found", name=os.path.splitext(os.path.basename(path))[0])
            return True, t + (self.m("file_many", n=n) if n > 1 else "")
        simple = {"volume_up": pc.volume_up, "volume_down": pc.volume_down, "mute": pc.mute, "unmute": pc.unmute,
                  "screenshot": pc.screenshot, "lock": pc.lock, "show_desktop": pc.show_desktop}
        if a in simple:
            return simple[a](), self.m(a)
        if a == "volume_set":
            return pc.volume_set(act["level"]), self.m("volume_set", level=act["level"])
        if a.startswith("media_"):
            return pc.media(a[6:]), self.m(a)
        if a in ("time", "date"):
            return True, pc.now_text(a, self.lang())
        if a in ("shutdown", "restart", "sleep"):
            # say it first: the PC may go away
            self.say(self.m(a), mood="happy")
            time.sleep(0.5)
            return pc.shutdown(a), None
        if a == "cancel_shutdown":
            return pc.cancel_shutdown(), self.m("cancel_shutdown")
        if a == "wake_pc":
            return True, self.m("wake_pc")
        if a.startswith("phone_"):
            if not phone.connected():
                return False, self.m("no_phone")
            if a == "phone_open_app":
                ok = phone.open_app(app)
                return ok, self.m("phone_opened" if ok else "failed", app=nice)
            if a in ("phone_volume_up", "phone_volume_down"):
                return phone.volume(a.endswith("up")), self.m(a)
            if a == "phone_screenshot":
                return bool(phone.screenshot()), self.m(a)
            if a == "phone_home":
                return phone.key(3), None
            if a == "phone_back":
                return phone.key(4), None
            if a == "phone_bunny":
                return phone.open_face(), self.m("phone_bunny")
            if a == "phone_restart":
                self.say(self.m("phone_restart"), mood="happy")
                time.sleep(3)
                return phone.restart(), None
        if a == "stop_talking":
            self.gen += 1
            self.emit({"type": "stop"})
            return True, None
        if a == "go_sleep":
            self.say(self.m("go_sleep"), mood="happy")
            self.emit({"type": "state", "state": "sleep"})
            return True, None
        return False, self.m("failed")

    # ------------------------------------------------------------ AI answers
    def chat(self, text):
        st = llm.status()
        cfg = config.load()
        if not st["running"]:
            self.say(self.m("brain_off"), mood="confused")
            return
        if not llm.has_model(cfg.get("llm_model", ""), st["models"]):
            self.say(self.m("brain_loading"), mood="confused")
            return
        self.gen += 1
        my = self.gen
        self.emit({"type": "state", "state": "thinking"})
        threading.Thread(target=self._chat_thread, args=(text, my, cfg), daemon=True).start()

    def _chat_thread(self, text, my, cfg):
        buf, full = "", ""
        try:
            for piece in llm.chat_stream(self.history, text, cfg, self.lang()):
                if my != self.gen:
                    return  # interrupted ("Bunny chup")
                buf += piece
                full += piece
                while True:
                    m = _SENT.match(buf)
                    if not m:
                        break
                    sentence = clean(m.group(1))
                    buf = buf[m.end():]
                    if sentence:
                        self.say(sentence, final=False)
            if my == self.gen and clean(buf):
                self.say(clean(buf), final=False)
        except Exception as e:  # noqa: BLE001
            print("AI error:", e)
            if my == self.gen:
                self.say(self.m("ai_error"), mood="confused")
            return
        if my == self.gen:
            self.emit({"type": "say_end"})
            self.history += [{"role": "user", "content": text}, {"role": "assistant", "content": clean(full)}]
            self.history = self.history[-12:]


HINDI_WORDS = {"hai", "hain", "kya", "kaise", "kaisa", "karo", "kar", "mein", "mujhe", "tum", "tera", "mera", "kyun",
               "kyu", "kab", "kahan", "kaha", "nahi", "nahin", "aur", "bhi", "ye", "yeh", "wo", "woh", "kuch", "batao",
               "hota", "hoti", "ka", "ki", "ke", "ko", "se", "kholo", "band", "chalao", "accha", "acha", "theek",
               "haan", "bolo", "kaun", "kitna", "kitne", "samjhao", "bata", "tumhara", "aap", "apna", "hum"}


def reply_language(text, spoken=None):
    """Answer in the language that was used: Devanagari or Hinglish words -> Hindi, otherwise English."""
    if re.search(r"[\u0900-\u097F]", text or ""):
        return "hindi"
    words = set(re.sub(r"[^a-z ]", " ", (text or "").lower()).split())
    if words & HINDI_WORDS:
        return "hindi"
    if spoken == "hi" and not words:
        return "hindi"
    return "english"


def clean(t):
    """Remove markdown / emoji so it sounds right."""
    t = re.sub(r"[*_#`>|~]+", "", t or "")
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", t)
    return " ".join(t.split()).strip()
