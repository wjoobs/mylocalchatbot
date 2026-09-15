"""Desktop launcher for My Local ChatGPT.

Run with:
    python app_launcher.py

Build with PyInstaller after installing requirements:
    pyinstaller --noconfirm --windowed --name "My Local ChatGPT" --add-data "frontend;frontend" --add-data "static;static" --add-data "app;app" --hidden-import webview.platforms.edgechromium app_launcher.py
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

import uvicorn
import webview


APP_TITLE = "My Local ChatGPT"
HOST = "127.0.0.1"
PORT = 8000
STARTUP_TIMEOUT_SECONDS = 20


def get_app_root() -> Path:
    """Return the directory that contains persistent data."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def get_resource_root() -> Path:
    """Return the directory that contains bundled frontend/static files."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()

    return get_app_root()


def write_log(message: str) -> None:
    try:
        log_path = get_app_root() / "app_launcher.log"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")
    except Exception:
        pass


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def start_server() -> None:
    try:
        config = uvicorn.Config(
            "app.main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception:
        write_log(traceback.format_exc())
        raise


def wait_for_server() -> None:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS

    while time.time() < deadline:
        if is_port_open(HOST, PORT):
            return
        time.sleep(0.2)

    raise RuntimeError(
        f"FastAPI 서버가 {STARTUP_TIMEOUT_SECONDS}초 안에 시작되지 않았습니다."
    )


def main() -> None:
    try:
        app_root = get_app_root()
        os.chdir(app_root)
        os.environ["MY_LOCAL_CHATGPT_RESOURCE_DIR"] = str(get_resource_root())

        if not is_port_open(HOST, PORT):
            server_thread = threading.Thread(
                target=start_server,
                name="fastapi-server",
                daemon=True,
            )
            server_thread.start()
            wait_for_server()

        webview.create_window(
            APP_TITLE,
            f"http://{HOST}:{PORT}",
            width=1280,
            height=820,
            min_size=(960, 640),
        )
        webview.start()
    except Exception:
        write_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()