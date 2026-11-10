"""Read-only local observability endpoint; no external notifications."""

import argparse, json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from .core import ROOT


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=9091)
    p.add_argument("--state", default=str(ROOT / "state"))
    a = p.parse_args()
    root = Path(a.state) / "telemetry"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            routes = {
                "/metrics": ("metrics.prom", "text/plain; version=0.0.4"),
                "/traces": ("events.jsonl", "application/x-ndjson"),
                "/alerts": ("alerts.jsonl", "application/x-ndjson"),
            }
            if self.path == "/health":
                body = b'{"status":"ok"}'
                mime = "application/json"
            elif self.path in routes:
                name, mime = routes[self.path]
                f = root / name
                body = f.read_bytes() if f.exists() else b""
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    HTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
