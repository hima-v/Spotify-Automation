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
        "id": f"doctor2_{int(time.time() * 1000)}_{os.getpid()}",
        "timestamp": int(time.time() * 1000),
        "runId": "env-doctor2",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _run(cmd: list[str], timeout_s: int = 20) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, shell=False)
        return {
            "cmd": cmd,
            "returncode": p.returncode,
            "stdout": (p.stdout or "").strip()[:6000],
            "stderr": (p.stderr or "").strip()[:6000],
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
        "tools/doctor2.py:main",
        "Starting environment doctor2",
        {"python": platform.python_version(), "platform": platform.platform(), "cwd": os.getcwd()},
    )

    # H1/H2: installed + PATH
    candidates = [
        r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
    ]
    _log(
        "H1",
        "tools/doctor2.py:docker_presence",
        "Docker presence checks",
        {
            "which_docker": shutil.which("docker"),
            "where_docker": _run(["where", "docker"]),
            "known_paths_existing": [p for p in candidates if Path(p).exists()],
        },
    )

    # H3: CLI usable + compose present
    _log(
        "H3",
        "tools/doctor2.py:docker_cli",
        "Docker CLI checks",
        {
            "docker_version": _run(["docker", "version"]),
            "docker_compose_version": _run(["docker", "compose", "version"]),
        },
    )

    # H4: WSL installed + version list
    _log("H4", "tools/doctor2.py:wsl", "WSL status", {"wsl_l_v": _run(["wsl", "-l", "-v"])})

    # H5: winget sees Docker Desktop package
    _log(
        "H5",
        "tools/doctor2.py:winget",
        "winget status",
        {
            "winget_version": _run(["winget", "--version"]),
            "winget_list_docker": _run(["winget", "list", "--id", "Docker.DockerDesktop"]),
        },
    )

    # H6: Windows features needed for WSL2 / Docker
    _log(
        "H6",
        "tools/doctor2.py:dism",
        "Windows feature status (WSL/VM Platform)",
        {
            "wsl_feature": _run(
                ["dism", "/online", "/get-featureinfo", "/featurename:Microsoft-Windows-Subsystem-Linux"]
            ),
            "vm_platform_feature": _run(
                ["dism", "/online", "/get-featureinfo", "/featurename:VirtualMachinePlatform"]
            ),
        },
    )

    # H7: Docker service presence (may require admin; useful signal anyway)
    _log(
        "H7",
        "tools/doctor2.py:services",
        "Docker service checks",
        {"com_docker_service": _run(["sc", "query", "com.docker.service"])},
    )

    _log("H0", "tools/doctor2.py:main", "Doctor2 finished", {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

