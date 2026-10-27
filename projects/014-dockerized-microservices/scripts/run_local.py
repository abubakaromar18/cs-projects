"""Run all three services as plain processes, without Docker.

Handy for development, or on a machine without Docker. Service discovery
uses localhost ports instead of Compose DNS names:

    gateway  http://127.0.0.1:8080   (same public URL as with Compose)
    notes    http://127.0.0.1:8001
    stats    http://127.0.0.1:8002

Data goes to ./.local-data/ instead of named volumes. Ctrl+C stops everything.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / ".local-data"

SERVICES = {
    "stats": {"PORT": "8002", "DATA_DIR": str(DATA / "stats")},
    "notes": {"PORT": "8001", "DATA_DIR": str(DATA / "notes"), "STATS_URL": "http://127.0.0.1:8002"},
    "gateway": {"PORT": os.environ.get("GATEWAY_PORT", "8080"),
                "NOTES_URL": "http://127.0.0.1:8001", "STATS_URL": "http://127.0.0.1:8002"},
}


def main() -> int:
    procs = []
    try:
        for name, env in SERVICES.items():
            procs.append(subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=ROOT / "services" / name,
                env={**os.environ, **env},
            ))
        print("Gateway on http://127.0.0.1:%s  (Ctrl+C to stop)" % SERVICES["gateway"]["PORT"])
        for proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in procs:
            proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
