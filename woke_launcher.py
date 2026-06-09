#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Start the visual console quietly and open it in a browser."""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8787"
HEALTH_URL = f"{URL}/api/v1/health"
LOG_FILE = ROOT / "logs" / "woke_launcher.log"
SERVER_LOG_FILE = ROOT / "logs" / "woke_server.log"


def log(message: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def service_ready() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=0.8) as response:
            return response.status == 200
    except Exception:
        return False


def start_server() -> subprocess.Popen[str]:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    server_log = SERVER_LOG_FILE.open("a", encoding="utf-8")
    server_log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} starting backend ---\n")
    server_log.flush()
    kwargs = {
        "cwd": str(ROOT),
        "stdout": server_log,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    return subprocess.Popen([sys.executable, "-m", "app_server.main"], **kwargs)


def wait_for_service(timeout_seconds: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if service_ready():
            return True
        time.sleep(0.25)
    return False


def main() -> int:
    dist = ROOT / "frontend" / "dist" / "index.html"
    if not dist.exists():
        message = "未找到 frontend/dist/index.html，请先运行：cd frontend && npm run build"
        log(message)
        print(message, file=sys.stderr)
        return 1

    if not service_ready():
        log("starting backend")
        process = start_server()
        log(f"backend pid={process.pid}")
        if not wait_for_service():
            exit_code = process.poll()
            log(f"backend health check timeout; exit_code={exit_code}")
            message = "后端启动超时，请手动运行 python -m app_server.main 查看错误。"
            log(message)
            print(message, file=sys.stderr)
            return 1
        log("backend health check ok")
    else:
        log("backend already running")

    log(f"opening {URL}")
    webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
