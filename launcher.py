import multiprocessing
multiprocessing.freeze_support()  # Must be first — prevents fork bomb in frozen .exe

import os
import socket
import sys
import threading
import time
from pathlib import Path

# Streamlit tries to register signal handlers but signal.signal() only works in the
# main thread. Suppress the error so it doesn't crash when run from a daemon thread.
import signal as _signal_module
_original_signal = _signal_module.signal
def _signal_main_thread_only(signum, handler):
    try:
        return _original_signal(signum, handler)
    except ValueError:
        pass
_signal_module.signal = _signal_main_thread_only


def _app_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys._MEIPASS) / "app.py")
    return str(Path(__file__).parent / "app.py")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _run_streamlit(app_path: str, port: int) -> None:
    from streamlit.web.bootstrap import load_config_options
    from streamlit.web import bootstrap
    flags = {
        "server_headless": True,
        "browser_gatherUsageStats": False,
        "server_port": port,
        "global_developmentMode": False,
    }
    load_config_options(flags)
    bootstrap.run(app_path, False, [], flags)


def _wait_for_ready(port: int, timeout: int = 30) -> bool:
    import requests
    url = f"http://localhost:{port}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


SPLASH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #1e1e1e;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    font-family: 'Segoe UI', sans-serif;
    color: #e0e0e0;
    user-select: none;
  }
  .crest {
    width: 100px;
    height: 100px;
    margin-bottom: 28px;
    opacity: 0.9;
  }
  h1 {
    font-size: 26px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
    color: #ffffff;
  }
  .subtitle {
    font-size: 13px;
    color: #888;
    margin-bottom: 40px;
  }
  .bar-track {
    width: 260px;
    height: 4px;
    background: #2b2b2b;
    border-radius: 2px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    width: 40%;
    background: #2ecc71;
    border-radius: 2px;
    animation: slide 1.4s ease-in-out infinite;
  }
  @keyframes slide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(700%); }
  }
</style>
</head>
<body>
  <h1>Slippi Ranked Stats</h1>
  <p class="subtitle">Loading...</p>
  <div class="bar-track"><div class="bar-fill"></div></div>
</body>
</html>"""


def _navigate_when_ready(window, port: int) -> None:
    if _wait_for_ready(port):
        window.load_url(f"http://localhost:{port}")
        time.sleep(1.5)
        window.evaluate_js('document.documentElement.style.zoom = "0.9"')
    else:
        window.load_url("about:blank")


def main() -> None:
    app_path = _app_path()
    port = _free_port()

    t = threading.Thread(target=_run_streamlit, args=(app_path, port), daemon=True)
    t.start()

    import webview
    window = webview.create_window(
        "Slippi Ranked Stats",
        html=SPLASH_HTML,
        width=1400,
        height=900,
        min_size=(800, 600),
    )

    def on_shown():
        nav_thread = threading.Thread(target=_navigate_when_ready, args=(window, port), daemon=True)
        nav_thread.start()

    webview.start(on_shown)


if __name__ == "__main__":
    main()
