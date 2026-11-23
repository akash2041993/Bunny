"""Entry point for the packaged Bunny.exe"""
import os
import sys

if getattr(sys, "frozen", False):
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
from bunny.__main__ import main  # noqa: E402

if __name__ == "__main__":
    if os.name == "nt":
        os.system("title Bunny")
    sys.exit(main())
