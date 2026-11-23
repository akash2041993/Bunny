"""Things Bunny can do on the computer. Only the functions in RUN can be called, and none of them
sends, uploads or shares anything: they open/close apps and folders, control sound and media,
take a screenshot into your own Pictures folder, lock, and shut down (after a "yes").

On Linux (tests) or with BUNNY_DRY_RUN=1 nothing is executed; the action is only recorded.
"""
import datetime
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser

from . import intents

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
DRY = bool(os.environ.get("BUNNY_DRY_RUN")) or not (IS_WIN or IS_MAC)
DONE = []  # dry-run log (tests)

_NOWINDOW = 0x08000000 if IS_WIN else 0


def _run(cmd, timeout=15):
    if DRY:
        DONE.append(cmd)
        return 0, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=_NOWINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def _start(target):
    """Open a file, folder, shortcut or app the normal way (like double-clicking it)."""
    if DRY:
        DONE.append(["start", target])
        return True
    try:
        if IS_WIN:
            os.startfile(target)  # noqa: S606 - opening, like a double-click
        else:
            subprocess.Popen(["open", target])
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- installed apps (Start Menu)
_apps_cache = {"t": 0.0, "apps": {}}


def installed_apps():
    """{display name: shortcut path} from the Start Menu (Windows) or /Applications (Mac)."""
    if time.time() - _apps_cache["t"] < 600 and _apps_cache["apps"]:
        return _apps_cache["apps"]
    apps = {}
    if IS_WIN:
        roots = [os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
                 os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")]
        for root in roots:
            for d, _dirs, files in os.walk(root):
                for f in files:
                    if f.lower().endswith((".lnk", ".url")):
                        name = f.rsplit(".", 1)[0]
                        low = name.lower()
                        if "uninstall" in low or "readme" in low or "help" in low:
                            continue
                        apps.setdefault(name, os.path.join(d, f))
    elif IS_MAC:
        for root in ("/Applications", os.path.expanduser("~/Applications"), "/System/Applications"):
            try:
                for d in os.listdir(root):
                    full = os.path.join(root, d)
                    if d.endswith(".app"):
                        apps[d[:-4]] = full
                    elif os.path.isdir(full):  # e.g. /Applications/Adobe Photoshop 2025/Adobe Photoshop 2025.app
                        for x in os.listdir(full):
                            if x.endswith(".app"):
                                apps.setdefault(x[:-4], os.path.join(full, x))
            except OSError:
                pass
    _apps_cache.update(t=time.time(), apps=apps)
    return apps


def _find_shortcut(names):
    """Best Start Menu entry for one of `names` ('Adobe Photoshop' -> 'Adobe Photoshop 2026')."""
    apps = installed_apps()
    hits = []
    for want in names:
        w = want.lower()
        for name, path in apps.items():
            n = name.lower()
            if n == w or n.startswith(w + " ") or n.startswith(w + "("):
                hits.append((n != w, name, path))
    if not hits:
        return None
    # exact name first, otherwise the newest version (largest name, e.g. "2026" > "2025")
    hits.sort(key=lambda h: (h[0], [-ord(c) for c in h[1]]))
    exact = [h for h in hits if not h[0]]
    if exact:
        return exact[0][2]
    return sorted(hits, key=lambda h: h[1], reverse=True)[0][2]


def running_processes():
    if DRY or not IS_WIN:
        return []
    code, out = _run(["tasklist", "/FO", "CSV", "/NH"])
    names = []
    for line in out.splitlines():
        m = re.match(r'"([^"]+)"', line)
        if m:
            names.append(m.group(1))
    return names


# ---------------------------------------------------------------- the actions
def open_app(app, custom=None):
    info = intents.PC_APPS.get(app)
    custom = custom or {}
    if app in custom:
        return _start(custom[app]), app
    if info:
        target = _find_shortcut(info.get("start", []) + [app]) if (info.get("start") or IS_MAC) else None
        if not target and info.get("cmd") and IS_WIN:
            target = info["cmd"]
        if not target:
            target = _find_shortcut([app])
        if target or DRY:
            return _start(target or app), app
        return False, app
    # an app name found in the Start Menu
    path = installed_apps().get(app) or _find_shortcut([app])
    if path or DRY:
        return _start(path or app), app
    return False, app


def close_app(app):
    """Closes the app normally (like clicking X), so it can still ask to save your work."""
    info = intents.PC_APPS.get(app)
    exes = list(info.get("exe", [])) if info else []
    if IS_MAC:
        name = (info.get("start") or [app])[0] if info else app
        code, _ = _run(["osascript", "-e", f'quit app "{name}"'])
        return code == 0, app
    if not exes:
        exes = [app if app.lower().endswith(".exe") else app + ".exe"]
    if DRY:
        DONE.append(["close", exes])
        return True, app
    running = {p.lower(): p for p in running_processes()}
    targets = [running[e.lower()] for e in exes if e.lower() in running]
    if not targets:
        return None, app  # not running
    ok = True
    for t in targets:
        code, _ = _run(["taskkill", "/IM", t])  # no /F: polite close, unsaved work is not lost
        ok = ok and code == 0
    return ok, app


def open_website(url):
    if DRY:
        DONE.append(["web", url])
        return True
    return webbrowser.open(url)


def _known_folder(key):
    home = os.path.expanduser("~")
    names = {"downloads": "Downloads", "documents": "Documents", "desktop": "Desktop", "pictures": "Pictures",
             "videos": "Videos", "music": "Music"}
    p = os.path.join(home, names.get(key, key))
    if not os.path.isdir(p):
        one = os.path.join(home, "OneDrive", names.get(key, key))
        if os.path.isdir(one):
            return one
    return p


def open_folder(key):
    return _start(_known_folder(key))


def find_file(query, budget=5.0):
    """Look for a file by name in your own folders and open the best match. Nothing leaves the PC."""
    words = [w for w in query.lower().split() if len(w) > 1]
    if not words:
        return None, 0
    roots = [_known_folder(k) for k in ("desktop", "documents", "downloads", "videos", "pictures", "music")]
    t0 = time.time()
    hits = []
    seen = 0
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith((".", "$")) and x not in ("node_modules", "AppData")]
            for f in files:
                seen += 1
                low = f.lower()
                if all(w in low for w in words):
                    p = os.path.join(d, f)
                    try:
                        hits.append((os.path.getmtime(p), p))
                    except OSError:
                        pass
            if time.time() - t0 > budget:
                break
    if not hits:
        return None, 0
    hits.sort(reverse=True)
    best = hits[0][1]
    _start(best)
    return best, len(hits)


# keyboard keys for sound / media / screenshot (Windows virtual-key codes)
VK = {"vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD, "play": 0xB3, "next": 0xB0, "prev": 0xB1,
      "win": 0x5B, "d": 0x44, "prtsc": 0x2C}


def _keys(*names, times=1):
    if DRY:
        DONE.append(["keys", names, times])
        return True
    if IS_MAC:
        return False
    import ctypes
    user32 = ctypes.windll.user32
    for _ in range(times):
        for n in names:
            user32.keybd_event(VK[n], 0, 0, 0)
        for n in reversed(names):
            user32.keybd_event(VK[n], 0, 2, 0)
        time.sleep(0.02)
    return True


def _mac_volume(script):
    return _run(["osascript", "-e", script])[0] == 0


def volume_up():
    return _mac_volume("set volume output volume ((output volume of (get volume settings)) + 12)") if IS_MAC \
        else _keys("vol_up", times=6)


def volume_down():
    return _mac_volume("set volume output volume ((output volume of (get volume settings)) - 12)") if IS_MAC \
        else _keys("vol_down", times=6)


def volume_set(level):
    if IS_MAC:
        return _mac_volume(f"set volume output volume {int(level)}")
    _keys("vol_down", times=50)  # to 0 (each press = 2 %)
    return _keys("vol_up", times=int(round(level / 2)))


def mute():
    return _mac_volume("set volume with output muted") if IS_MAC else _keys("mute")


def unmute():
    if IS_MAC:
        return _mac_volume("set volume without output muted")
    _keys("vol_up")
    return _keys("vol_down")


def media(which):
    return _keys({"playpause": "play", "next": "next", "prev": "prev"}[which])


def screenshot():
    """Windows saves it in Pictures\\Screenshots (Win + Print Screen)."""
    if IS_MAC:
        p = os.path.join(_known_folder("pictures"), datetime.datetime.now().strftime("Bunny %Y-%m-%d %H.%M.%S.png"))
        return _run(["screencapture", "-x", p])[0] == 0
    return _keys("win", "prtsc")


def show_desktop():
    return _keys("win", "d")


def lock():
    if DRY:
        DONE.append(["lock"])
        return True
    if IS_MAC:
        return _run(["pmset", "displaysleepnow"])[0] == 0
    import ctypes
    return bool(ctypes.windll.user32.LockWorkStation())


def shutdown(kind):
    """Shutdown / restart start with a 30 second countdown that 'cancel' can stop."""
    if IS_MAC:
        cmd = {"shutdown": 'tell app "System Events" to shut down',
               "restart": 'tell app "System Events" to restart',
               "sleep": 'tell app "System Events" to sleep'}[kind]
        return _run(["osascript", "-e", cmd])[0] == 0
    if kind == "sleep":
        return _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])[0] == 0
    flag = "/s" if kind == "shutdown" else "/r"
    return _run(["shutdown", flag, "/t", "30", "/c", "Bunny: shutting down in 30 seconds"])[0] == 0


def cancel_shutdown():
    return False if IS_MAC else _run(["shutdown", "/a"])[0] == 0


def wol_info():
    """MAC address of the wired network card, for 'computer on karo' from the phone app later."""
    if DRY or not IS_WIN:
        return {}
    code, out = _run(["getmac", "/fo", "csv", "/nh", "/v"])
    best = {}
    for line in out.splitlines():
        cols = [c.strip('"') for c in line.split('","')]
        if len(cols) >= 3 and re.match(r"([0-9A-F]{2}-){5}[0-9A-F]{2}", cols[2] or ""):
            wired = "ethernet" in (cols[0] + cols[1]).lower() and "virtual" not in cols[1].lower()
            if wired or not best:
                best = {"adapter": cols[1], "mac": cols[2].replace("-", ":"), "wired": wired}
                if wired:
                    break
    return best


def now_text(kind, lang):
    t = datetime.datetime.now()
    if kind == "time":
        h12 = t.hour % 12 or 12
        if lang == "english":
            return t.strftime("It's %I:%M %p.").lstrip("0")
        part = "सुबह" if 4 <= t.hour < 12 else "दोपहर" if t.hour < 17 else "शाम" if t.hour < 20 else "रात"
        if lang == "hinglish":
            return f"Abhi {part} ke {h12} baj kar {t.minute} minute hue hain."
        return f"अभी {part} के {h12} बजकर {t.minute} मिनट हुए हैं।"
    months_hi = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर",
                 "नवंबर", "दिसंबर"]
    days_hi = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
    if lang == "english":
        return t.strftime("Today is %A, %d %B %Y.")
    if lang == "hinglish":
        return t.strftime("Aaj %A hai, %d %B %Y.")
    return f"आज {days_hi[t.weekday()]} है, {t.day} {months_hi[t.month - 1]} {t.year}।"


_lock = threading.Lock()
