import os
from pathlib import Path

__version__ = "1.0.0"

def _setup_gio():
    if "GIO_MODULE_DIR" in os.environ:
        return
    candidates = [
        "/usr/lib/x86_64-linux-gnu/gio/modules",
        "/usr/lib/aarch64-linux-gnu/gio/modules",
        "/usr/lib/gio/modules",
        "/usr/lib64/gio/modules"
    ]
    for c in candidates:
        p = Path(c)
        if p.exists() and (p / "libgvfsdbus.so").exists():
            os.environ["GIO_MODULE_DIR"] = c
            break

_setup_gio()
