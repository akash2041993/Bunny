"""Start Bunny: python -m bunny"""
import os
import shutil
import subprocess
import sys
import threading
import time

from . import config, llm, phone, server, stt


def _ears():
    server.emit({"type": "status", "part": "ears", "text": "ears_loading"})
    try:
        stt.load()
        print("Ears ready (speech-to-text, offline).")
        server.emit({"type": "status", "part": "ears", "text": "ears_ready"})
    except Exception as e:  # noqa: BLE001
        print("Ears problem:", e)
        server.emit({"type": "status", "part": "ears", "text": "ears_error", "detail": str(e)})


def _start_ollama():
    cands = [shutil.which("ollama")]
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA", "")
        cands += [os.path.join(la, "Programs", "Ollama", "ollama app.exe"), os.path.join(la, "Programs", "Ollama", "ollama.exe")]
    for c in cands:
        if c and os.path.isfile(c):
            try:
                args = [c] if c.endswith("app.exe") else [c, "serve"]
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=0x08000000 if os.name == "nt" else 0)
                return True
            except OSError:
                pass
    return False


def _brain():
    cfg = config.load()
    model = cfg.get("llm_model", "gemma3:4b")
    st = llm.status()
    if not st["running"] and _start_ollama():
        for _ in range(30):
            time.sleep(1)
            st = llm.status()
            if st["running"]:
                break
    if not st["running"]:
        print("Brain: Ollama is not running. Install it from ollama.com (Bunny's installer can do it), then restart Bunny.")
        server.emit({"type": "status", "part": "brain", "text": "brain_off"})
        return
    if not llm.has_model(model, st["models"]):
        print(f"Brain: downloading the offline AI model '{model}' once (a few GB)...")
        last = [0.0, ""]

        def prog(f, s):
            if f is None:  # after the download: checking / saving
                if s and s != last[1]:
                    last[1] = s
                    nice = {"verifying sha256 digest": "checking the download (1-3 minutes)...",
                            "writing manifest": "saving...", "success": "done."}.get(s, s)
                    print(f"\n  {model}: {nice}", end="")
                    server.emit({"type": "status", "part": "brain", "text": "brain_download", "progress": 1.0})
                return
            if f - last[0] >= 0.01:
                last[0] = f
                server.emit({"type": "status", "part": "brain", "text": "brain_download", "progress": round(f, 3)})
                print(f"  {model}: {f * 100:.0f}%", end="\r")

        # if the pull's connection hangs after the model is already saved, notice it anyway
        done = threading.Event()

        def watch_ready():
            while not done.wait(15):
                if llm.has_model(model, llm.status()["models"]):
                    done.set()
                    print(f"\nBrain ready (offline AI: {model}).")
                    server.emit({"type": "status", "part": "brain", "text": "brain_ready"})
        threading.Thread(target=watch_ready, daemon=True).start()
        try:
            llm.pull(model, prog)
            print()
            if done.is_set():
                return
            done.set()
        except Exception as e:  # noqa: BLE001
            if done.is_set():
                return
            done.set()
            print("Brain download failed:", e)
            server.emit({"type": "status", "part": "brain", "text": "brain_error", "detail": str(e)})
            return
    print(f"Brain ready (offline AI: {model}).")
    server.emit({"type": "status", "part": "brain", "text": "brain_ready"})


def main():
    cfg = config.load()
    port = config.PORT
    try:
        httpd = server.serve(port)
    except OSError:
        print(f"Bunny is already running (port {port} is busy). You can close this window.")
        time.sleep(6)
        return 1
    print(f"Bunny {config.VERSION} is awake on this computer. Keep this window open (you can minimise it).")
    print(f"  Face on this PC (to test with the PC microphone): http://127.0.0.1:{port}")
    print("  Phone: plug the S10e in with USB (USB debugging on) - the face opens on it by itself.")
    print("  Security: Bunny only listens on this computer, needs its secret token, and cannot send or share files.")
    threading.Thread(target=_ears, daemon=True).start()
    threading.Thread(target=_brain, daemon=True).start()
    phone.start_watcher(server.emit)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
