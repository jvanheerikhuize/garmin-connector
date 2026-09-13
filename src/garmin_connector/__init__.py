"""
garmin-connector: Sideload and manage routes (GPX/FIT) on Garmin Venu and other Garmin watches.
"""

import os

for _cand in [
    "/usr/lib/x86_64-linux-gnu/gio/modules",
    "/usr/lib/aarch64-linux-gnu/gio/modules",
    "/usr/lib/gio/modules",
    "/usr/lib64/gio/modules",
]:
    if os.path.exists(os.path.join(_cand, "libgvfsdbus.so")):
        os.environ["GIO_MODULE_DIR"] = _cand
        break

__version__ = "0.1.0"
