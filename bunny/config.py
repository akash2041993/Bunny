"""Bunny's files and settings. Everything stays on this computer."""
import json
import os
import secrets
import sys
import threading

VERSION = "0.2.3"
PORT = 47865  # an unusual port, so no other program on the PC is likely to use it

_lock = threading.Lock()


def bundle_dir():
    """Folder with bundled files (web page, adb, speech model) - source or packaged .exe."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_dir():
    base = os.environ.get("BUNNY_HOME")
    if not base:
        if os.name == "nt":
            base = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Bunny")
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Bunny")
        else:
            base = os.path.join(os.path.expanduser("~"), ".bunny")
    os.makedirs(base, exist_ok=True)
    return base


def web_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


DEFAULTS = {
    "user_name": "Akash",
    "character": "bunny",               # bunny | pixel | robo (say a name to switch)
    "reply_language": "auto",           # auto (answer in the language you spoke) | hindi | english | hinglish
    "llm_model": "gemma3:4b",            # Ollama model; gemma3:1b for PCs with 8 GB RAM
    "ollama_url": "http://127.0.0.1:11434",
    "whisper_model": "small",            # tiny | base | small | medium
    "stt_language": "auto",              # auto (Hindi or English per sentence) | hi | en
    "wake_words": [],                    # extra wake words (each character also answers to its own name)
    "follow_up_seconds": 8,              # after Bunny answers, you can talk again without "Bunny"
    "custom_apps": {},                   # "my editor": "C:\\path\\to\\app.exe"
    "token": "",                         # secret the face page must send (made on first start)
    "pc_mac": "",                         # for "computer on karo" (Wake-on-LAN, phone app)
}


def _path():
    return os.path.join(app_dir(), "settings.json")


def load():
    with _lock:
        data = dict(DEFAULTS)
        try:
            with open(_path(), "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except (OSError, ValueError):
            pass
        if not data.get("token"):
            data["token"] = secrets.token_urlsafe(24)
            _write(data)
        return data


def _write(data):
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path())


def save(updates):
    data = load()
    with _lock:
        for k, v in updates.items():
            if k in DEFAULTS:
                data[k] = v
        _write(data)
    return data
