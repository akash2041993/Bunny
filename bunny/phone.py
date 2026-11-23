"""The S10e over the USB cable (adb). Only used locally: nothing goes to the internet.

- keeps the link "phone -> http://127.0.0.1:<port>" working (adb reverse), so the face page on the
  phone talks to this PC through the cable, not through Wi-Fi;
- keeps the screen on while plugged in and opens Bunny's face in Chrome;
- a few phone actions: open an app, volume, home/back, screenshot (saved on the PC), restart.
"""
import datetime
import os
import shutil
import subprocess
import threading
import time

from . import config, intents

_NOWINDOW = 0x08000000 if os.name == "nt" else 0
state = {"devices": [], "adb": None, "error": None, "port": config.PORT}
_seen = set()


def adb_path():
    exe = "adb.exe" if os.name == "nt" else "adb"
    for p in (os.path.join(config.bundle_dir(), "platform-tools", exe), os.path.join(config.app_dir(), "platform-tools", exe)):
        if os.path.isfile(p):
            return p
    return shutil.which("adb")


def adb(*args, serial=None, timeout=20):
    a = adb_path()
    if not a:
        return 1, "adb not found"
    cmd = [a] + (["-s", serial] if serial else []) + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=_NOWINDOW)
        out = (r.stdout or b"") + (r.stderr or b"")
        return r.returncode, out.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def devices():
    code, out = adb("devices")
    state["raw"] = out.strip()
    if code != 0 and state.get("adb_err") != out:
        state["adb_err"] = out
        print("Phone check problem (adb):", out.strip()[:300])
    res = []
    for line in out.splitlines():
        parts = line.split()
        # skip "List of devices attached" and "* daemon started" lines
        if len(parts) >= 2 and not line.startswith(("*", "List")) and parts[1] in (
                "device", "unauthorized", "offline", "recovery", "sideload", "authorizing", "no"):
            res.append((parts[0], parts[1]))  # (serial, "device" | "unauthorized" | "offline")
    return res


_link_ok = {}


def _setup(serial, port):
    code, out = adb("reverse", f"tcp:{port}", f"tcp:{port}", serial=serial)
    _, lst = adb("reverse", "--list", serial=serial)
    ok = f"tcp:{port}" in lst
    if _link_ok.get(serial) != ok:  # report changes only
        _link_ok[serial] = ok
        if ok:
            print(f"Phone link ready: on the phone, Bunny is at http://127.0.0.1:{port}")
        else:
            print("Phone link FAILED (adb reverse):", (out or lst).strip()[:300])
    if serial not in _seen:
        _seen.add(serial)
        adb("shell", "svc", "power", "stayon", "usb", serial=serial)   # screen stays on while charging
        open_face(serial, port)


def open_face(serial=None, port=None):
    port = port or state["port"]
    # 127.0.0.1, not "localhost": "localhost" may go to another program on IPv6
    return adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"http://127.0.0.1:{port}",
               "com.android.chrome", serial=serial)[0] == 0


def watch(port=config.PORT, emit=None):
    """Background loop: notice the phone being plugged in / unlocked / unplugged."""
    state["adb"] = adb_path()
    state["port"] = port
    if not state["adb"]:
        state["error"] = "adb not found"
        return
    last = None
    while True:
        try:
            devs = devices()
            for serial, st in devs:
                if st == "device":
                    _setup(serial, port)
            summary = [(s, st) for s, st in devs]
            if summary != last:
                state["devices"] = summary
                if emit:
                    emit({"type": "devices", "devices": summary})
                for s, st in summary:
                    if st == "unauthorized":
                        print("Phone found: tap 'Allow' on the USB debugging message on the phone.")
                    elif st == "device":
                        print(f"Phone connected ({s}). Bunny's face opens on it.")
                    else:
                        print(f"Phone found but not ready (state: {st}). Unplug and plug the cable again.")
                if not summary:
                    print("No phone found on USB. On the phone: USB debugging on, cable in, USB mode 'Transferring files'.")
                for s in list(_seen):
                    if s not in [x for x, _ in summary]:
                        _seen.discard(s)
                last = summary
        except Exception as e:  # noqa: BLE001 - keep watching
            if state["error"] != str(e):
                print("Phone link problem:", e)
            state["error"] = str(e)
        time.sleep(3)


def _serial():
    for s, st in state["devices"]:
        if st == "device":
            return s
    return None


def connected():
    return _serial() is not None


def open_app(key):
    info = intents.PHONE_APPS.get(key)
    s = _serial()
    if not info or not s:
        return False
    if "intent" in info:
        return adb("shell", "am", "start", "-a", info["intent"], serial=s)[0] == 0
    code, out = adb("shell", "monkey", "-p", info["pkg"], "-c", "android.intent.category.LAUNCHER", "1", serial=s)
    return code == 0 and "No activities found" not in out


def key(code):
    s = _serial()
    return bool(s) and adb("shell", "input", "keyevent", str(code), serial=s)[0] == 0


def volume(up):
    return all(key(24 if up else 25) for _ in range(3))


def screenshot():
    s = _serial()
    if not s:
        return None
    folder = os.path.join(os.path.expanduser("~"), "Pictures", "Bunny")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, datetime.datetime.now().strftime("Phone %Y-%m-%d %H.%M.%S.png"))
    a = adb_path()
    try:
        with open(path, "wb") as f:
            r = subprocess.run([a, "-s", s, "exec-out", "screencap", "-p"], stdout=f, timeout=20,
                               creationflags=_NOWINDOW)
        return path if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def restart():
    s = _serial()
    if not s:
        return False
    _seen.discard(s)  # open the face again after it comes back
    return adb("reboot", serial=s)[0] == 0


def start_watcher(emit=None, port=config.PORT):
    t = threading.Thread(target=watch, kwargs={"emit": emit, "port": port}, daemon=True)
    t.start()
    return t
