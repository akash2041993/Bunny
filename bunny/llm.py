"""Bunny's brain: a local AI model run by Ollama on this PC (http://127.0.0.1:11434).
Works without internet once the model is downloaded. The AI can only talk; it cannot run anything.
When it is asked to pick a command, its answer is checked against the fixed action list."""
import json
import urllib.error
import urllib.request

from . import config, intents

LANG_RULE = {
    "hindi": "हमेशा हिंदी में, देवनागरी लिपि में जवाब दो (अंग्रेज़ी के आम शब्द देवनागरी में लिख सकते हो)।",
    "english": "Always answer in simple English.",
    "hinglish": "Always answer in Hinglish written in Roman letters (Hindi words in English letters).",
}


def system_prompt(cfg):
    name, user = cfg.get("bunny_name", "Bunny"), cfg.get("user_name", "Akash")
    return (
        f"You are {name}, a cute, warm and playful little bunny who is {user}'s AI friend. "
        f"{user} is a video editor from Indore. You live on his old phone and his PC. "
        "You are speaking out loud, so: answer in 1 to 3 short sentences unless he asks for detail, "
        "no markdown, no lists, no emojis, no symbols. "
        "You work offline and have no internet: for news, prices, scores or anything recent, say you are "
        "offline and might not know the latest. If you are not sure about a fact, say so honestly. "
        "You cannot send, upload or share files, and you never pretend you did something on the computer: "
        "the app does the commands, you only talk. "
        + LANG_RULE.get(cfg.get("reply_language", "hindi"), LANG_RULE["hindi"])
    )


def _url(path):
    return config.load().get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + path


def _post(path, body, timeout=120):
    data = json.dumps(body).encode()
    req = urllib.request.Request(_url(path), data=data, method="POST", headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def status():
    try:
        with urllib.request.urlopen(_url("/api/tags"), timeout=3) as r:
            models = [m.get("name") for m in json.loads(r.read().decode()).get("models", [])]
        return {"running": True, "models": models}
    except (urllib.error.URLError, OSError, ValueError):
        return {"running": False, "models": []}


def has_model(name, models):
    base = name if ":" in name else name + ":latest"
    return name in models or base in models


def pull(name, progress=None):
    """Download a model once (Ollama does the download)."""
    with _post("/api/pull", {"model": name, "stream": True}, timeout=3600) as r:
        for line in r:
            try:
                ev = json.loads(line.decode())
            except ValueError:
                continue
            if ev.get("error"):
                raise RuntimeError(ev["error"])
            if progress and ev.get("total"):
                progress(ev.get("completed", 0) / ev["total"], ev.get("status", ""))
    return True


def chat_stream(history, text, cfg=None):
    """Yields pieces of the answer as they are generated."""
    cfg = cfg or config.load()
    msgs = [{"role": "system", "content": system_prompt(cfg)}] + history[-8:] + [{"role": "user", "content": text}]
    body = {"model": cfg.get("llm_model", "gemma3:4b"), "messages": msgs, "stream": True,
            "options": {"temperature": 0.6, "num_predict": 300}, "keep_alive": "30m"}
    with _post("/api/chat", body, timeout=300) as r:
        for line in r:
            try:
                ev = json.loads(line.decode())
            except ValueError:
                continue
            if ev.get("error"):
                raise RuntimeError(ev["error"])
            piece = (ev.get("message") or {}).get("content", "")
            if piece:
                yield piece
            if ev.get("done"):
                break


CLASSIFY = """You turn a spoken request (Hindi, English or Hinglish, written in Roman letters) into ONE command.
Allowed commands (JSON):
{"action":"open_app","app":"<app name>"}  {"action":"close_app","app":"<app name>"}
{"action":"open_website","site":"<site name>"}  {"action":"open_folder","folder":"downloads|documents|desktop|pictures|videos|music"}
{"action":"find_file","query":"<words in the file name>"}
{"action":"volume_up"} {"action":"volume_down"} {"action":"mute"} {"action":"unmute"}
{"action":"media_playpause"} {"action":"media_next"} {"action":"media_prev"}
{"action":"screenshot"} {"action":"lock"} {"action":"show_desktop"} {"action":"time"} {"action":"date"}
{"action":"shutdown"} {"action":"restart"} {"action":"sleep"}
{"action":"phone_open_app","app":"<app>"} {"action":"phone_volume_up"} {"action":"phone_volume_down"}
If it is a question, chat, or anything else (including sending, sharing, uploading, deleting): {"action":"none"}
Reply with JSON only."""


def classify(text, cfg=None):
    """Ask the AI which command was meant. The answer is checked: only allowed actions pass."""
    cfg = cfg or config.load()
    body = {"model": cfg.get("llm_model", "gemma3:4b"), "stream": False, "format": "json",
            "messages": [{"role": "system", "content": CLASSIFY}, {"role": "user", "content": text}],
            "options": {"temperature": 0}, "keep_alive": "30m"}
    try:
        with _post("/api/chat", body, timeout=60) as r:
            out = json.loads(r.read().decode())
        data = json.loads((out.get("message") or {}).get("content", "{}"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    act = data.get("action") if isinstance(data, dict) else None
    if act not in intents.ACTIONS:
        return None
    clean = {"action": act}
    for k in ("app", "site", "folder", "query"):
        if isinstance(data.get(k), str):
            clean[k] = data[k][:80]
    if act == "open_website":
        site = (clean.get("site") or "").lower()
        key, _ = intents._best_name(site.split(), intents.WEBSITES)
        if not key:
            return None
        clean = {"action": act, "site": key, "url": intents.WEBSITE_URLS[key]}
    return clean
