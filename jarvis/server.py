"""Lightweight local REST & UI server connecting the modern Whistle React frontend to the transcription engine."""

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


def get_active_audio_device() -> str:
    """Dynamically query the active PipeWire / WirePlumber audio capture device."""
    try:
        res = subprocess.run(["wpctl", "status"], capture_output=True, text=True, timeout=1)
        in_sources = False
        for line in res.stdout.splitlines():
            if "Sources:" in line:
                in_sources = True
                continue
            if in_sources and ("Filters:" in line or "Streams:" in line or "Sinks:" in line):
                break
            if in_sources and "*" in line:
                clean = line.replace("*", "").strip()
                parts = clean.split(".", 1)
                name = parts[1].split("[")[0].strip() if len(parts) > 1 else clean
                return name
        res = subprocess.run(["pactl", "get-default-source"], capture_output=True, text=True, timeout=1)
        src = res.stdout.strip()
        if src:
            return src
    except Exception:
        pass
    return "PipeWire Default Mic"


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
                "audio_device": get_active_audio_device(),
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

        elif parsed.path == "/api/format":
            try:
                data = json.loads(body.decode("utf-8"))
                raw_text = data.get("text", "")
                from jarvis.formatter import polish_transcript
                from jarvis.history import add_history_entry
                formatted = polish_transcript(raw_text)
                add_history_entry(raw_text=raw_text, formatted_text=formatted, duration_sec=1.5)
                self.send_json({"formatted": formatted, "raw": raw_text})
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
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
        print(f"Whistle Desktop Server listening on http://127.0.0.1:{PORT}")
        httpd.serve_forever()


def open_desktop_window():
    """Opens the application in dedicated, borderless Chrome app window mode."""
    url = f"http://127.0.0.1:{PORT}"
    # Prefer Chrome app mode for a sleek desktop application experience
    chrome_cmd = [
        "google-chrome",
        f"--app={url}",
        "--class=WhistleApp",
        "--name=Whistle",
        "--force-dark-mode",
        "--enable-features=WebUIDarkMode",
    ]
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
