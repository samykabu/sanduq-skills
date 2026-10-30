"""A tiny notes API: one process, notes kept in memory, an API key per user."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

KEYS = {"key-alice": "alice", "key-bob": "bob"}
NOTES: dict[str, list[str]] = {}


class Handler(BaseHTTPRequestHandler):
    def user(self):
        return KEYS.get(self.headers.get("X-Api-Key", ""))

    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        user = self.user()
        if not user:
            return self.reply(401, {"error": "unknown key"})
        self.reply(200, {"notes": NOTES.get(user, [])})

    def do_POST(self):
        user = self.user()
        if not user:
            return self.reply(401, {"error": "unknown key"})
        length = int(self.headers.get("Content-Length", 0))
        text = json.loads(self.rfile.read(length) or b"{}").get("text", "")
        NOTES.setdefault(user, []).append(text)
        self.reply(201, {"count": len(NOTES[user])})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
