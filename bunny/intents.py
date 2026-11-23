"""Understand what was said: wake word, and commands in Hindi / English / Hinglish.

Speech-to-text may give Devanagari ("फोटोशॉप खोलो") or Roman ("photoshop kholo"); everything is
turned into lowercase Roman first, then matched with small word lists and fuzzy matching.
The result is always one action from a FIXED list (see ACTIONS) - nothing else can be run.
"""
import difflib
import re

from . import translit

# every action Bunny can do. Nothing outside this list is ever executed.
ACTIONS = {
    "open_app", "close_app", "open_website", "open_folder", "find_file",
    "volume_up", "volume_down", "volume_set", "mute", "unmute",
    "media_playpause", "media_next", "media_prev",
    "screenshot", "lock", "show_desktop", "time", "date",
    "shutdown", "restart", "sleep", "cancel_shutdown", "wake_pc",
    "phone_open_app", "phone_volume_up", "phone_volume_down", "phone_screenshot",
    "phone_home", "phone_back", "phone_bunny", "phone_restart",
    "stop_talking", "go_sleep",
}
# actions that need a "haan / yes" first
CONFIRM = {"shutdown", "restart", "sleep", "phone_restart"}

FILLER = {"hey", "hi", "hello", "ok", "okay", "oye", "oy", "arre", "are", "o", "please", "plz", "zara",
          "jara", "jra", "bhai", "yaar", "yar", "na", "ji", "to", "toh", "jaldi", "abhi", "ab", "ek", "mera",
          "meri", "mere", "my", "the", "a", "ko", "do", "de", "dena", "karo", "kar", "kardo", "kr", "krdo",
          "karde", "kariye", "karna", "kijiye", "tum", "tu", "aap", "please", "jo", "wo", "vo", "wala", "wali",
          "app", "application", "software", "program", "par", "pe", "me", "mein", "main", "se", "ka", "ki", "ke"}

OPEN = {"open", "kholo", "khol", "kholna", "kholdo", "kholde", "kholiye", "khulo", "chalu", "chalao", "chala",
        "chalaao", "chalado", "start", "launch", "shuru", "run", "laga", "lagao", "dikhao", "dikha", "on",
        "opan", "opn", "oupan", "apan", "apn", "staart", "lonch", "laanch"}
CLOSE = {"close", "band", "bandh", "bnd", "bando", "hatao", "hata", "exit", "quit", "kill", "khatam", "off",
         "nikal", "nikalo", "kloz", "kloj", "klos", "klose", "egzit", "kvit"}
DEVICE_PC = {"computer", "kampyutar", "kampyutr", "kompyutar", "compyutar", "pc", "laptop", "system",
             "sistam", "desktop", "kompyutr"}
DEVICE_PHONE = {"phone", "fon", "mobile", "mobail", "phon", "fone"}

VOL = {"volume", "valyum", "volyum", "awaaz", "aawaaz", "aavaaz", "awaz", "aawaz", "avaaz", "sound", "saund",
       "aavaz", "aawaj", "awaj"}
UP = {"up", "louder", "raise", "badhao", "badha", "badhaao", "badhaa", "increase", "tez", "jyada", "zyada", "jada", "full", "max",
      "upar", "loud", "high", "badao"}
DOWN = {"down", "lower", "quieter", "softer", "kam", "decrease", "dheere", "dhire", "dheema", "low", "neeche", "niche", "halki", "halka",
        "dheemi"}
MEDIA = {"gaana", "gana", "song", "music", "myujik", "video", "vidio", "gaane", "audio"}
PAUSE = {"roko", "ruko", "rok", "pause", "stop", "ruk", "rukao", "thamo", "band"}
PLAY = {"play", "chalao", "chala", "chalu", "bajao", "baja", "resume", "start"}
NEXT = {"next", "agla", "agle", "aage", "skip", "doosra", "dusra"}
RESTART = {"restart", "reboot", "ristart", "restaart", "reestaart", "rebut"}
SHUTDOWN = {"shutdown", "shatdaun", "shutdaun"}
PREV = {"previous", "pichla", "pichhla", "pichle", "peeche", "back"}

FOLDERS = {
    "downloads": ["download", "downloads", "daunlod", "daunlods", "downlod"],
    "documents": ["documents", "document", "dokyument", "dokyuments", "docs"],
    "desktop": ["desktop folder"],
    "pictures": ["pictures", "picture", "photos folder", "pikchar", "pikchars"],
    "videos": ["videos folder", "vidios"],
    "music": ["music folder"],
}
WEBSITES = {
    "youtube": ["youtube", "yutyub", "yootyoob", "you tube", "yu tub", "utube"],
    "google": ["google", "gugal", "gugl"],
    "gmail": ["gmail", "jimel", "g mail", "jimail"],
    "instagram": ["instagram", "insta", "instaagram", "instagraam"],
    "facebook": ["facebook", "fesbuk", "feesbuk"],
    "whatsapp web": ["whatsapp web"],
    "chatgpt": ["chatgpt", "chat gpt", "chaat jeepeetee"],
    "claude": ["claude", "klod", "cloud ai"],
    "netflix": ["netflix", "netaflix", "netflics"],
    "github": ["github", "git hub", "githab"],
}
WEBSITE_URLS = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com", "gmail": "https://mail.google.com",
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "whatsapp web": "https://web.whatsapp.com", "chatgpt": "https://chatgpt.com", "claude": "https://claude.ai",
    "netflix": "https://www.netflix.com", "github": "https://github.com",
}

# PC apps: spoken names -> how to open / close them (Windows process names)
PC_APPS = {
    "photoshop": {"say": ["photoshop", "fotoshop", "photo shop", "foto shop"], "exe": ["Photoshop.exe"],
                  "start": ["Adobe Photoshop"]},
    "premiere pro": {"say": ["premiere", "premiere pro", "premier", "premiyar", "preemiyar", "primiyar",
                             "premier pro", "preemiyar pro"], "exe": ["Adobe Premiere Pro.exe"],
                     "start": ["Adobe Premiere Pro"]},
    "after effects": {"say": ["after effects", "aftereffects", "aftar ifekts", "after effect", "aftar efekt"],
                      "exe": ["AfterFX.exe"], "start": ["Adobe After Effects"]},
    "illustrator": {"say": ["illustrator", "ilastretar", "ilustretar"], "exe": ["Illustrator.exe"],
                    "start": ["Adobe Illustrator"]},
    "lightroom": {"say": ["lightroom", "laitrum", "light room"], "exe": ["Lightroom.exe", "lightroom.exe"],
                  "start": ["Adobe Lightroom", "Adobe Lightroom Classic"]},
    "audition": {"say": ["audition", "odishan", "adobe audition"], "exe": ["Adobe Audition.exe"],
                 "start": ["Adobe Audition"]},
    "media encoder": {"say": ["media encoder", "midiya enkodar"], "exe": ["Adobe Media Encoder.exe"],
                      "start": ["Adobe Media Encoder"]},
    "chrome": {"say": ["chrome", "krom", "crome", "google chrome", "kroom"], "exe": ["chrome.exe"],
               "start": ["Google Chrome"]},
    "edge": {"say": ["edge", "ej", "microsoft edge"], "exe": ["msedge.exe"], "start": ["Microsoft Edge"]},
    "firefox": {"say": ["firefox", "fayarfoks"], "exe": ["firefox.exe"], "start": ["Firefox"]},
    "notepad": {"say": ["notepad", "notpad", "note pad"], "exe": ["notepad.exe", "Notepad.exe"],
                "cmd": "notepad.exe"},
    "calculator": {"say": ["calculator", "kailkuletar", "calc", "kelkuletar"], "exe": ["CalculatorApp.exe"],
                   "cmd": "calc.exe"},
    "file explorer": {"say": ["file explorer", "explorer", "my computer", "this pc", "fail eksplorar"],
                      "exe": [], "cmd": "explorer.exe"},
    "word": {"say": ["word", "ms word", "microsoft word", "vard"], "exe": ["WINWORD.EXE"], "start": ["Word"]},
    "excel": {"say": ["excel", "eksel", "ms excel"], "exe": ["EXCEL.EXE"], "start": ["Excel"]},
    "powerpoint": {"say": ["powerpoint", "power point", "paavar point"], "exe": ["POWERPNT.EXE"],
                   "start": ["PowerPoint"]},
    "vlc": {"say": ["vlc", "vlc player", "vee el see"], "exe": ["vlc.exe"], "start": ["VLC media player"]},
    "spotify": {"say": ["spotify", "spotifai", "spotifaai"], "exe": ["Spotify.exe"], "start": ["Spotify"]},
    "whatsapp": {"say": ["whatsapp", "whats app", "watsap", "vhaatsep", "whatsaap"], "exe": ["WhatsApp.exe"],
                 "start": ["WhatsApp"]},
    "telegram": {"say": ["telegram", "teligram"], "exe": ["Telegram.exe"], "start": ["Telegram"]},
    "discord": {"say": ["discord", "diskord"], "exe": ["Discord.exe"], "start": ["Discord"]},
    "obs": {"say": ["obs", "obs studio", "o b s"], "exe": ["obs64.exe"], "start": ["OBS Studio"]},
    "steam": {"say": ["steam", "steem"], "exe": ["steam.exe"], "start": ["Steam"]},
    "davinci resolve": {"say": ["davinci", "davinci resolve", "resolve", "daavinchi"], "exe": ["Resolve.exe"],
                        "start": ["DaVinci Resolve"]},
    "capcut": {"say": ["capcut", "cap cut", "kepkat", "kaipkat"], "exe": ["CapCut.exe"], "start": ["CapCut"]},
    "vs code": {"say": ["vs code", "vscode", "visual studio code"], "exe": ["Code.exe"],
                "start": ["Visual Studio Code"]},
    "task manager": {"say": ["task manager", "taask manager", "task menejar"], "exe": ["Taskmgr.exe"],
                     "cmd": "taskmgr.exe"},
    "settings": {"say": ["settings", "setting", "setings"], "exe": ["SystemSettings.exe"], "cmd": "ms-settings:"},
    "paint": {"say": ["paint", "ms paint", "pent"], "exe": ["mspaint.exe"], "cmd": "mspaint.exe"},
    "camera": {"say": ["camera", "kaimra", "kemra", "kaimara"], "exe": ["WindowsCamera.exe"],
               "cmd": "microsoft.windows.camera:"},
    "claude": {"say": ["claude app", "claude"], "exe": ["claude.exe", "Claude.exe"], "start": ["Claude"]},
}

PHONE_APPS = {
    "youtube": {"say": ["youtube", "yutyub", "you tube", "utube"], "pkg": "com.google.android.youtube"},
    "camera": {"say": ["camera", "kaimra", "kemra"], "intent": "android.media.action.STILL_IMAGE_CAMERA"},
    "whatsapp": {"say": ["whatsapp", "watsap", "whats app"], "pkg": "com.whatsapp"},
    "instagram": {"say": ["instagram", "insta"], "pkg": "com.instagram.android"},
    "chrome": {"say": ["chrome", "krom"], "pkg": "com.android.chrome"},
    "gallery": {"say": ["gallery", "gailri", "galari", "photos", "photo"], "pkg": "com.sec.android.gallery3d"},
    "settings": {"say": ["settings", "setting"], "intent": "android.settings.SETTINGS"},
    "maps": {"say": ["maps", "map", "google maps", "naksha"], "pkg": "com.google.android.apps.maps"},
    "spotify": {"say": ["spotify"], "pkg": "com.spotify.music"},
    "play store": {"say": ["play store", "playstore", "ple stor"], "pkg": "com.android.vending"},
    "calculator": {"say": ["calculator", "calc"], "pkg": "com.sec.android.app.popupcalculator"},
    "clock": {"say": ["clock", "ghadi", "alarm", "timer"], "pkg": "com.sec.android.app.clockpackage"},
    "music": {"say": ["music", "gaana"], "pkg": "com.google.android.apps.youtube.music"},
}

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def to_roman(text):
    """Any mix of Devanagari / Roman -> lowercase Roman words."""
    text = (text or "").replace("।", " ").replace("॥", " ")
    if translit.is_devanagari(text):
        text = " ".join(translit.words_to_roman(text.split()))
    text = _PUNCT.sub(" ", text.lower())
    return " ".join(text.split())


_PHON = [("ph", "f"), ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("w", "v"), ("z", "j"), ("q", "k"),
         ("ck", "k"), ("c", "k"), ("x", "ks"), ("th", "t"), ("dh", "d"), ("kh", "k"), ("gh", "g"), ("bh", "b"),
         ("sh", "s"), ("ai", "e"), ("au", "o"), ("ou", "o"), ("ey", "e"), ("y", "i")]


def _phon(s):
    """Rough sound-alike form, so 'aaphtar iphekts' ~ 'after effects', 'wotsaaip' ~ 'whatsapp'."""
    s = s.lower().replace(" ", "")
    for a, b in _PHON:
        s = s.replace(a, b)
    s = re.sub(r"h(?=[^aeiou]|$)", "", s)       # silent h: "whatsapp" -> "watsapp"
    s = re.sub(r"(.)\1+", r"\1", s)            # double letters
    return s


def _sim(a, b):
    r = difflib.SequenceMatcher(None, a, b).ratio()
    pa, pb = _phon(a), _phon(b)
    if pa == pb:
        return max(r, 0.97)
    r = max(r, difflib.SequenceMatcher(None, pa, pb).ratio())
    # same consonants ("votsep" ~ "vatsap"): speech-to-text mostly gets vowels wrong
    ka, kb = re.sub(r"[aeiou]", "", pa), re.sub(r"[aeiou]", "", pb)
    if len(ka) >= 4 and ka == kb:
        r = max(r, 0.88)
    return r


def _like(word, options, cutoff=0.86):
    """Is `word` one of `options` (allowing small speech-to-text spelling differences)?"""
    if word in options:
        return True
    if len(word) < 4:
        return False
    return any(len(o) >= 4 and _sim(word, o) >= cutoff for o in options)


def find_wake(text, wake_words):
    """Returns (found, rest_text). Wake word may be at the start ("Bunny, chrome kholo") or the end."""
    words = to_roman(text).split()
    wake = [w.lower() for w in wake_words]

    def is_wake(w):
        return w in wake or (len(w) >= 4 and any(_sim(w, x) >= 0.8 for x in wake))

    for i, w in enumerate(words[:4]):
        if is_wake(w) and all(x in FILLER for x in words[:i]):
            return True, " ".join(words[i + 1:])
    if words and is_wake(words[-1]):
        return True, " ".join(words[:-1])
    return False, " ".join(words)


def _grams(words, n=3):
    out = []
    for size in range(n, 0, -1):
        for i in range(len(words) - size + 1):
            g = words[i:i + size]
            out.append((" ".join(g), i, size))
            if size > 1:
                out.append(("".join(g), i, size))
    return out


def _best_name(words, table, extra=None, cutoff=0.82):
    """Find which name from `table` ({key: {"say": [...]}}) is mentioned. Returns (key, score)."""
    best, best_score = None, 0.0
    names = [(k, s) for k, v in table.items() for s in (v["say"] if isinstance(v, dict) else v)]
    for k in (extra or []):
        names.append((k, k.lower()))
    for gram, _i, _n in _grams(words):
        if gram in FILLER or gram in OPEN or gram in CLOSE:
            continue
        for key, say in names:
            if gram == say:
                score = 1.0 + len(say) / 100
            elif len(gram) >= 4 and len(say) >= 4:
                score = _sim(gram, say)
            else:
                continue
            if score > best_score:
                best, best_score = key, score
    return (best, best_score) if best_score >= cutoff else (None, best_score)


def _has(words, group):
    return any(_like(w, group) for w in words)


def _number(words):
    for w in words:
        if w.isdigit():
            return int(w)
    return None


def parse(text, installed_apps=None, running=None):
    """Spoken command -> action dict, or None (then it is a question for the AI).
    installed_apps: extra app names found on this PC (Start Menu) for fuzzy matching."""
    words = to_roman(text).split()
    if not words:
        return None
    joined = " ".join(words)
    phone = _has(words, DEVICE_PHONE)
    pc = _has(words, DEVICE_PC)
    opening = _has(words, OPEN)
    closing = _has(words, CLOSE)

    # stop / sleep / cancel
    if joined in ("chup", "chup ho jao", "chup raho", "stop", "bas", "bas karo", "ruk jao", "shut up", "quiet",
                  "be quiet", "stop talking", "keep quiet"):
        return {"action": "stop_talking"}
    if re.search(r"\b(so jao|so ja|sleep mode|good night|goodnight|aaram karo|go to sleep)\b", joined) and not pc:
        return {"action": "go_sleep"}
    if re.search(r"\b(cancel|mat karo|rehne do|rahne do|nahi karna)\b", joined) and re.search(
            r"\b(shutdown|shut down|band)\b", joined):
        return {"action": "cancel_shutdown"}

    # whole computer: shutdown / restart / sleep / lock / turn on
    restart = _has(words, RESTART)
    if pc or restart or _has(words, SHUTDOWN) or re.search(r"\b(shut down|lock|lok)\b", joined):
        if restart or ("dobara" in words and opening):
            return {"action": "phone_restart"} if phone and not pc else {"action": "restart"}
        if re.search(r"\b(lock|lok)\b", joined) and not phone:
            return {"action": "lock"}
        if _has(words, SHUTDOWN) or "shut down" in joined or (pc and closing):
            return {"action": "shutdown"}
        if pc and re.search(r"\b(sleep|so ja|so jao|sula do|sulao)\b", joined):
            return {"action": "sleep"}
        if pc and (opening or "on" in words):
            return {"action": "wake_pc"}

    # volume
    if _has(words, VOL) or joined in ("unmute", "mute"):
        prefix = "phone_" if phone else ""
        n = _number(words)
        if "unmute" in words or re.search(r"\b(wapas|vapas) (chalu|on)\b", joined):
            return {"action": "unmute"}
        if "mute" in words or _has(words, {"chup"}) or (closing and not _has(words, DOWN) and not _has(words, UP)):
            return {"action": "mute"}
        if n is not None and not phone:
            return {"action": "volume_set", "level": max(0, min(100, n))}
        if _has(words, UP):
            return {"action": prefix + "volume_up"}
        if _has(words, DOWN):
            return {"action": prefix + "volume_down"}

    # media
    if _has(words, MEDIA) or joined in ("pause", "play", "next", "agla gaana"):
        if _has(words, NEXT):
            return {"action": "media_next"}
        if _has(words, PREV):
            return {"action": "media_prev"}
        if _has(words, PAUSE) or _has(words, PLAY):
            return {"action": "media_playpause"}

    if re.search(r"\b(screenshot|screen shot|skreenshot|skrinshot|screen ki photo)\b", joined):
        return {"action": "phone_screenshot" if phone else "screenshot"}
    if re.search(r"\b(desktop dikhao|desktop pe jao|sab minimize|minimize all|sab chhota)\b", joined):
        return {"action": "show_desktop"}
    if re.search(r"\b(kitne baje|kya time|time kya|samay kya|time batao|kya samay|time hua|baj rahe|"
                 r"what time|time is it|the time|whats the time)\b", joined) \
            or joined in ("time", "samay"):
        return {"action": "time"}
    if re.search(r"\b(aaj ki date|date kya|tareekh|taarikh|tarikh|aaj kya din|kaun sa din|aaj kaunsa din|"
                 r"what day|todays date|the date|what date)\b", joined) or joined in ("date",):
        return {"action": "date"}

    # phone navigation / Bunny face back
    if phone:
        if re.search(r"\b(home|hom)\b", joined):
            return {"action": "phone_home"}
        if re.search(r"\b(back|peeche|wapas jao)\b", joined) and not opening:
            return {"action": "phone_back"}
    if re.search(r"\b(wapas aao|vapas aao|wapas aa jao|vapas aa jao|come back)\b", joined) or joined in ("wapas", "vapas"):
        return {"action": "phone_bunny"}

    if phone and opening:
        key, _ = _best_name(words, PHONE_APPS)
        if key:
            return {"action": "phone_open_app", "app": key}

    # folders
    if opening:
        for key, says in FOLDERS.items():
            for s in says:
                if s in joined or any(_like(w, {s}) for w in words if " " not in s):
                    if key in ("desktop",) and "folder" not in words:
                        continue
                    return {"action": "open_folder", "folder": key}

    # files: "Barbarik wali file dhundo", "find file invoice"
    if re.search(r"\b(dhundo|dhoondo|dhundho|dhoondho|search|find|khojo)\b", joined) and re.search(
            r"\b(file|fail|photo|video|document|pdf|folder)\b", joined):
        q = [w for w in words if w not in FILLER and w not in OPEN and w not in {
            "file", "fail", "files", "dhundo", "dhoondo", "dhundho", "dhoondho", "search", "find", "khojo",
            "naam", "name", "wali", "wala", "photo", "video", "document", "pdf"}]
        if q:
            return {"action": "find_file", "query": " ".join(q)}

    if opening or closing:
        extra = [a for a in (installed_apps or []) if a]
        # websites first when the word is a site ("youtube kholo") and it is not a PC app
        key, score = _best_name(words, PC_APPS, extra=extra + list(running or []))
        site, site_score = _best_name(words, WEBSITES)
        if closing and not opening:
            if key:
                return {"action": "close_app", "app": key}
        else:
            if site and (not key or site_score >= score) and opening:
                return {"action": "open_website", "site": site, "url": WEBSITE_URLS[site]}
            if key:
                return {"action": "open_app", "app": key}
    return None
