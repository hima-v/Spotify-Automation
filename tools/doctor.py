from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


LOG_PATH = Path(r"c:\Users\hima2\Spotify-Automation\.cursor\debug.log")


def _log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": f"doctor_{int(time.time() * 1000)}_{os.getpid()}",
        "timestamp": int(time.time() * 1000),
        "runId": "env-doctor",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _run(cmd: list[str]) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15, shell=False)
        return {
            "cmd": cmd,
            "returncode": p.returncode,
            "stdout": (p.stdout or "").strip()[:4000],
            "stderr": (p.stderr or "").strip()[:4000],
        }
    except FileNotFoundError as e:
        return {"cmd": cmd, "error": "FileNotFoundError", "detail": str(e)}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "error": "Timeout"}
    except Exception as e:
        return {"cmd": cmd, "error": type(e).__name__, "detail": str(e)}


def main() -> int:
    _log(
        "H0",
        "tools/doctor.py:main",
        "Starting environment doctor",
        {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cwd": os.getcwd(),
        },
    )

    # Hypothesis H1: Docker not installed (no docker.exe found)
    docker_on_path = shutil.which("docker")
    _log("H1", "tools/doctor.py:which", "which(docker)", {"docker": docker_on_path})

    _log("H1", "tools/doctor.py:where", "where docker", _run(["where", "docker"]))

    # Hypothesis H2: Docker Desktop installed but PATH not set
    candidates = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
    ]
    existing = [p for p in candidates if Path(p).exists()]
    _log("H2", "tools/doctor.py:paths", "known docker paths", {"existing": existing})

    # Hypothesis H3: Docker exists but daemon not running / not reachable
    _log("H3", "tools/doctor.py:docker_version", "docker version", _run(["docker", "version"]))
    _log(
        "H3",
        "tools/doctor.py:docker_compose",
        "docker compose version",
        _run(["docker", "compose", "version"]),
    )

    # Hypothesis H4: Using WSL-only install while running Windows PowerShell
    _log("H4", "tools/doctor.py:wsl", "wsl -l -v", _run(["wsl", "-l", "-v"]))

    _log("H0", "tools/doctor.py:main", "Doctor finished", {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

