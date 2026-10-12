import asyncio
import json
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from bokkio.runtime import Runtime
from bokkio.sdk import Client


def test_official_mcp_client_and_cli_share_session(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def check():
        params = StdioServerParameters(command=sys.executable, args=["-m", "bokkio.runtime_cli", "--state", str(tmp_path), "serve"])
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as client:
                initialized = await client.initialize()
                assert initialized.serverInfo.name == "bokkio"
                tools = await client.list_tools()
                names = {t.name for t in tools.tools}
                assert {"desktop.pixel", "code.run", "audit.export", "events.follow"} <= names
                assert "approval.approve" not in names
                by_name = {t.name: t for t in tools.tools}
                assert 'session_id' in by_name['code.run'].inputSchema['required']
                assert 'arguments' in by_name['code.run'].inputSchema['required']
                assert 'session_id' not in by_name['session.open'].inputSchema['required']
                malformed = await client.call_tool('code.run', {'arguments': {'code': 'print(1)'}})
                assert malformed.isError
                with Runtime(tmp_path).store.connect() as db:
                    assert db.execute("SELECT count(*) FROM operations WHERE tool='code.run'").fetchone()[0] == 0
                opened = await client.call_tool("session.open", {"arguments": {}})
                assert not opened.isError
                session = opened.structuredContent["result"]["session_id"]
                result = subprocess.run([sys.executable, "-m", "bokkio.runtime_cli", "--state", str(tmp_path), "call", "metrics.summary", "--session", session], capture_output=True, text=True, timeout=10)
                assert result.returncode == 0, result.stderr
                assert json.loads(result.stdout)["status"] == "completed"
                events = await client.call_tool("audit.query", {"arguments": {}, "session_id": session})
                assert any(row["data"].get("tool") == "metrics.summary" for row in events.structuredContent["result"])
                rejected = await client.call_tool("code.run", {"arguments": {"code": "print(1)"}, "session_id": session})
                assert rejected.isError
    asyncio.run(check())


@pytest.mark.browser_live
def test_real_browser_worker_persistence_and_origin_denial(tmp_path):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).exists():
            pytest.skip("Run playwright install chromium for the live Browser contract")

    class Page(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            html = b"""<html><body><input id="field"><button id="go" onclick="document.getElementById('result').textContent=document.getElementById('field').value">Confirm</button><p id="result">Ready</p></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)
    web = HTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=web.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{web.server_port}"
    client = Client(Runtime(tmp_path, {"origins": [url], "write": True, "require_approval": False}))
    client.open()
    try:
        opened = client.call("browser.open", {"url": url})
        assert opened["status"] == "executed"
        expected_url = opened["result"]["url"]
        assert client.call("browser.act", {"action": "fill", "selector": "#field", "value": "independent-result", "expected_url": expected_url})["status"] == "executed"
        assert client.call("browser.act", {"action": "click", "selector": "#go", "expected_url": expected_url})["status"] == "executed"
        assert "independent-result" in client.call("browser.observe")["result"]["text"]
        denied = client.call("browser.open", {"url": "http://127.0.0.1:1"})
        assert denied["status"] == "denied" and denied["dispatched"] is False
        # Browser state also survives a different CLI/client Runtime instance.
        other = Client(Runtime(tmp_path, {"origins": [url], "write": True, "require_approval": False}), client.session_id)
        assert "independent-result" in other.call("browser.observe")["result"]["text"]
    finally:
        client.call("session.close")
        web.shutdown()


def test_cli_human_approval_and_export(tmp_path):
    runtime = Runtime(tmp_path / "state", {"paths": [str(tmp_path)], "write": True, "trusted_host": True})
    client = Client(runtime)
    client.open()
    request = {"code": "print('approved fixture')", "cwd": str(tmp_path)}
    pending = client.call("code.run", request, "approved-job")
    assert pending["status"] == "approval_required"
    result = subprocess.run([sys.executable, "-m", "bokkio.runtime_cli", "--state", str(runtime.store.root), "approve", pending["approval_id"], "--decision", "approved", "--reason", "authorized test fixture"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    launched = client.call("code.run", request, "approved-job")
    final = client.wait_job(launched["result"]["job_id"], timeout=10)
    assert final["result"]["result"]["stdout"].strip() == "approved fixture"
    exported = client.call("audit.export", {"format": "jsonl"})
    record = client.call("artifact.read", {"artifact_id": exported["result"]["artifact"]["artifact_id"]})
    assert record["status"] == "completed"
    import base64
    events = [json.loads(line) for line in base64.b64decode(record["result"]["data_base64"]).decode().splitlines()]
    assert {"approval.requested", "approval.approved", "approval.consumed", "job.finished"} <= {e["kind"] for e in events}


def test_generated_code_uses_delegated_sdk_and_parent_audit(tmp_path):
    client = Client(Runtime(tmp_path / "state", {"paths": [str(tmp_path)], "write": True,
                                               "trusted_host": True, "require_approval": False}))
    client.open()
    request = {"code": "from bokkio.sdk import Client\nc=Client.from_environment()\nr=c.call('metrics.summary')\nassert r['status']=='completed'\nprint('delegated SDK works')", "cwd": str(tmp_path)}
    started = client.call("code.run", request, "parent-code")
    result = client.wait_job(started["result"]["job_id"], timeout=10)
    assert result["result"]["status"] == "completed", result
    assert result["result"]["result"]["stdout"].strip() == "delegated SDK works"
    assert any(e["data"].get("parent_operation") == "parent-code" for e in client.runtime.store.query(session_id=client.session_id))
