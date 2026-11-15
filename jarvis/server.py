"""Lightweight local REST & UI server connecting the modern DeepSeek React frontend to the JARVIS engine."""

import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.formatter import load_config, save_config
from jarvis.history import clear_all_history, delete_history_item, list_history

PORT = 8765
DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"


class JarvisAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/history":
            query_params = urllib.parse.parse_qs(parsed.query)
            q = query_params.get("q", [""])[0]
            items = list_history(limit=100, query=q)
            self.send_json(items)
            return

        elif parsed.path == "/api/config":
            cfg = load_config()
            self.send_json(cfg)
            return

        elif parsed.path == "/api/status":
            status = {
                "status": "online",
                "audio_device": "PipeWire default (FIIO JD1)",
                "sample_rate": 16000,
                "engine": "Whistle ASR + Needle 3",
            }
            self.send_json(status)
            return

        # If static file not found, fallback to index.html (SPA routing)
        file_path = DIST_DIR / parsed.path.lstrip("/")
        if not file_path.is_file() and not parsed.path.startswith("/api"):
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""

        if parsed.path == "/api/config":
            try:
                new_data = json.loads(body.decode("utf-8"))
                save_config(new_data)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        elif parsed.path == "/api/history/clear":
            clear_all_history()
            self.send_json({"success": True})
            return

        elif parsed.path == "/api/history/delete":
            try:
                data = json.loads(body.decode("utf-8"))
                delete_history_item(data.get("id"))
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
            return

        elif parsed.path == "/api/trigger":
            # Launch hotkey HUD
            hotkey_script = str(Path(__file__).resolve().parent / "hotkey.py")
            subprocess.Popen([sys.executable, hotkey_script])
            self.send_json({"success": True, "action": "triggered"})
            return

        self.send_json({"error": "Not Found"}, status=404)

    def send_json(self, data, status=200):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


def launch_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), JarvisAPIHandler) as httpd:
        print(f"JARVIS Desktop Server listening on http://127.0.0.1:{PORT}")
        httpd.serve_forever()


def open_desktop_window():
    """Opens the application in dedicated, borderless Chrome app window mode."""
    url = f"http://127.0.0.1:{PORT}"
    # Prefer Chrome app mode for a sleek desktop application experience
    chrome_cmd = ["google-chrome", f"--app={url}", "--class=JarvisApp", "--name=JARVIS"]
    try:
        subprocess.Popen(chrome_cmd)
    except Exception:
        # Fallback to system default browser
        import webbrowser
        webbrowser.open(url)


def main():
    def _open():
        time.sleep(0.5)
        open_desktop_window()

    threading.Thread(target=_open, daemon=True).start()
    launch_server()


if __name__ == "__main__":
    main()
