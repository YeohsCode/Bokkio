"""A per-session Playwright worker keeps browser state across CLI/SDK calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from .audit import AuditStore, canonical, identifier


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTP(S) origins are supported")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return f"{parsed.scheme}://{parsed.hostname.lower()}:{port}"


def call(store, session_id, arguments, origins):
    with store.connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS browsers(session_id TEXT PRIMARY KEY, endpoint TEXT, token TEXT)")
        row = db.execute("SELECT * FROM browsers WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        # Core desktop lock also serializes creation of the session browser.
        with (store.root / "browser-worker.log").open("ab") as log:
            subprocess.Popen([sys.executable, "-m", "bokkio.browser_driver", str(store.root), session_id],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log,
                             **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with store.connect() as db:
                row = db.execute("SELECT * FROM browsers WHERE session_id=?", (session_id,)).fetchone()
            if row is not None:
                break
            time.sleep(.05)
        if row is None:
            raise ValueError("Browser worker unavailable; install bokkio[browser] and run playwright install chromium")
    request = Request(row["endpoint"], data=canonical({"arguments": arguments, "origins": origins}).encode(),
                      headers={"Authorization": "Bearer " + row["token"], "Content-Type": "application/json"})
    try:
        # Never send this local control token through a configured HTTP proxy.
        with build_opener(ProxyHandler({})).open(request, timeout=20) as response:
            result = json.load(response)
    except Exception as error:
        raise RuntimeError("Browser worker response unavailable: " + type(error).__name__ + "; inspect state before retrying a write") from error
    if "error" in result:
        from .windows_capture import CaptureError
        raise CaptureError("browser_action_failed", result["error"], dispatched=result.get("dispatched", "unknown"))
    return result


def worker(root, session_id):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from playwright.sync_api import sync_playwright

    store = AuditStore(root)
    token = identifier() + identifier()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        allowed = set()
        def permitted(url):
            try:
                return origin(url) in allowed
            except ValueError:
                return False
        context.route("**/*", lambda route: route.continue_() if permitted(route.request.url) else route.abort())
        # Browser traffic is limited to the granted origins, including WebSockets.
        if hasattr(context, "route_web_socket"):
            context.route_web_socket("**/*", lambda ws: ws.connect_to_server() if permitted(ws.url.replace("wss:", "https:").replace("ws:", "http:")) else ws.close())

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if self.headers.get("Authorization") != "Bearer " + token:
                    self.send_error(403)
                    return
                dispatched = False
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 200000:
                        raise ValueError("Invalid request size")
                    request = json.loads(self.rfile.read(size))
                    with store.connect() as db:
                        session = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
                    if session is None or session["status"] != "open" or session["expires"] <= time.time():
                        raise ValueError("Browser session is closed or expired")
                    granted = set(json.loads(session["policy"])["origins"])
                    if not set(request["origins"]).issubset(granted):
                        raise ValueError("Browser scope escalation refused")
                    allowed.clear()
                    allowed.update(request["origins"])
                    args = request["arguments"]
                    action = args.get("action", "observe")
                    if action == "open":
                        if origin(args["url"]) not in allowed:
                            raise ValueError("URL outside authorized origins")
                        dispatched = "unknown"
                        page.goto(args["url"], timeout=10000, wait_until="domcontentloaded")
                        dispatched = True
                    elif action != "observe":
                        if origin(page.url) not in allowed:
                            raise ValueError("Current page outside authorized origins")
                        if args.get("expected_url") != page.url:
                            raise ValueError("Browser page changed since request; observe again before input")
                        locator = page.locator(args["selector"])
                        if locator.count() != 1:
                            raise ValueError("Browser selector must match exactly one element")
                        dispatched = "unknown"
                        if action == "fill":
                            locator.fill(args["value"], timeout=5000)
                        elif action == "click":
                            locator.click(timeout=5000)
                        elif action == "press":
                            locator.press(args["key"], timeout=5000)
                        else:
                            raise ValueError("Unsupported browser action")
                        dispatched = True
                    if page.url != "about:blank" and origin(page.url) not in allowed:
                        raise ValueError("Navigation ended outside authorized origins")
                    # Read-only snapshot with bounded text and observed form values.
                    content = page.locator("body").inner_text(timeout=5000) if page.url != "about:blank" else ""
                    fields = page.locator("input,textarea,select").evaluate_all("els => els.slice(0,100).map(e=>({tag:e.tagName,id:e.id,type:e.type,value:e.type==='password'?null:e.value}))")
                    result = {"url": page.url, "title": page.title(), "text": content[:20000],
                              "truncated": len(content) > 20000, "fields": fields, "action": action}
                except Exception as error:
                    result = {"error": str(error), "dispatched": dispatched}
                data = canonical(result).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        server.timeout = 1
        with store.connect() as db:
            db.execute("INSERT INTO browsers VALUES(?,?,?)", (session_id, f"http://127.0.0.1:{server.server_port}", token))
        try:
            while True:
                server.handle_request()
                with store.connect() as db:
                    session = db.execute("SELECT status,expires FROM sessions WHERE id=?", (session_id,)).fetchone()
                if session is None or session["status"] != "open" or session["expires"] <= time.time():
                    break
        finally:
            server.server_close()
            browser.close()
            with store.connect() as db:
                db.execute("DELETE FROM browsers WHERE session_id=?", (session_id,))


if __name__ == "__main__":
    worker(sys.argv[1], sys.argv[2])
