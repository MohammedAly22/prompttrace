"""Built-in HTTP server for the PromptTrace dashboard. Zero external dependencies."""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from prompttrace import db


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serves the SPA dashboard and JSON API."""

    def log_message(self, format, *args):
        pass  # Silence default logging

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _html_response(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/stats":
            exp_id = params.get("experiment_id", [None])[0]
            self._json_response(db.fetch_stats(
                experiment_id=int(exp_id) if exp_id else None
            ))

        elif path == "/api/experiments":
            self._json_response(db.fetch_all_experiments())

        elif path == "/api/traces":
            exp_id = params.get("experiment_id", [None])[0]
            limit = int(params.get("limit", [200])[0])
            traces = db.fetch_traces(
                experiment_id=int(exp_id) if exp_id else None,
                limit=limit,
            )
            self._json_response(traces)

        elif path.startswith("/api/trace/"):
            trace_id = int(path.split("/")[-1])
            trace = db.fetch_trace_by_id(trace_id)
            if trace:
                trace["evals"] = db.fetch_evals_for_trace(trace_id)
                self._json_response(trace)
            else:
                self._json_response({"error": "Not found"}, 404)

        elif path == "/api/prompts":
            exp_id = params.get("experiment_id", [None])[0]
            prompts = db.fetch_unique_prompts(
                experiment_id=int(exp_id) if exp_id else None
            )
            self._json_response(prompts)

        elif path == "/api/compare":
            hash_a = params.get("a", [None])[0]
            hash_b = params.get("b", [None])[0]
            if not hash_a or not hash_b:
                self._json_response({"error": "Provide ?a=hash&b=hash"}, 400)
                return
            conn = db._connect()
            rows_a = conn.execute(
                "SELECT * FROM traces WHERE prompt_hash = ? ORDER BY created_at DESC LIMIT 10",
                (hash_a,),
            ).fetchall()
            rows_b = conn.execute(
                "SELECT * FROM traces WHERE prompt_hash = ? ORDER BY created_at DESC LIMIT 10",
                (hash_b,),
            ).fetchall()
            conn.close()
            self._json_response({
                "a": [dict(r) for r in rows_a],
                "b": [dict(r) for r in rows_b],
            })

        elif path == "/logo.png":
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            if os.path.exists(logo_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(logo_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        else:
            # Serve SPA
            self._html_response(_get_dashboard_html())

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/experiment/"):
            exp_id = int(path.split("/")[-1])
            db.delete_experiment(exp_id)
            self._json_response({"ok": True})

        elif path.startswith("/api/trace/"):
            trace_id = int(path.split("/")[-1])
            db.delete_trace(trace_id)
            self._json_response({"ok": True})

        else:
            self._json_response({"error": "Not found"}, 404)


def _get_dashboard_html() -> str:
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def run_server(host: str = "127.0.0.1", port: int = 8777):
    server = HTTPServer((host, port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()