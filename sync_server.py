#!/usr/bin/env python3
"""
Daycycle LAN sync server — zero dependencies, just Python's standard library.

Just run:
    python3 sync_server.py

It will:
  1. Figure out your PC's local network address automatically.
  2. Serve the Daycycle app itself (index.html, etc. from this same folder).
  3. Open it in your PC's browser automatically.
  4. Print the address to type ONCE into your phone's browser (same WiFi).

After that, both devices load the app from this same address, so they
auto-detect each other and sync in the background — no IP typing on the
phone beyond that first visit, and no push/pull buttons needed.

Data is stored in data.json next to this script, so it survives restarts.
"""
import json
import os
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PORT = 8765
DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DIR, "data.json")


def get_lan_ip():
    """Find this machine's LAN IP without needing internet access."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # doesn't actually send anything
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def read_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"todos": [], "schedule": []}


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


CONTENT_TYPES = {
    ".html": "text/html", ".js": "text/javascript", ".json": "application/json",
    ".png": "image/png", ".ico": "image/x-icon", ".css": "text/css",
}


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/data"):
            body = json.dumps(read_data()).encode("utf-8")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve app files (static hosting) — default to index.html for "/"
        if path == "/":
            path = "/index.html"
        file_path = os.path.join(DIR, path.lstrip("/"))
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path.startswith("/data"):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                incoming = json.loads(raw.decode("utf-8"))
            except Exception:
                self.send_response(400)
                self._cors()
                self.end_headers()
                return
            write_data({
                "todos": incoming.get("todos", []),
                "schedule": incoming.get("schedule", [])
            })
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # keep the console quiet


if __name__ == "__main__":
    ip = get_lan_ip()
    url = f"http://{ip}:{PORT}"
    server = HTTPServer(("0.0.0.0", PORT), Handler)

    print("=" * 56)
    print("  Daycycle is running.")
    print(f"  This PC:    {url}   (opening now)")
    print(f"  Your phone: open {url} in a browser, same WiFi")
    print("  That's it — both devices will auto-sync from here.")
    print("=" * 56)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    server.serve_forever()
