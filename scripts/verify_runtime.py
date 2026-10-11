"""Portable real-runtime acceptance. Desktop writes require an explicitly supplied test app."""
from __future__ import annotations

import argparse
import asyncio
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import platform
import subprocess
import sys
import threading

from bokkio.runtime import Runtime
from bokkio.sdk import Client


def run(output, native_app=None, field="Search", rounds=3):
    output.mkdir(parents=True, exist_ok=False)
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
    policy = {"apps": [native_app] if native_app else [], "paths": [str(output)], "origins": [url],
              "write": True, "trusted_host": True, "require_approval": False}
    policy_path = output / "test-policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    client = Client(Runtime(output / "state", policy))
    client.open()
    report = {"platform": platform.system(), "architecture": platform.machine(), "scope": "explicit_disposable_runtime_acceptance",
              "rounds": [], "native": [], "mcp": None, "approval": None}

    try:
        for index in range(rounds):
            token = "RUNTIME-" + str(index + 1)
            code = "from pathlib import Path\nfrom bokkio.sdk import Client\np=Path('report.csv')\np.write_text('name,value\\nfixture," + token + "\\n',encoding='utf-8')\nc=Client.from_environment()\nr=c.call('evidence.check',{'path':str(p.resolve()),'csv_rows':1,'csv_columns':['name','value']})\nassert r['result']['passed'],r\nprint('verified')"
            queued = client.call("code.run", {"code": code, "cwd": str(output)})
            final = client.wait_job(queued["result"]["job_id"], timeout=15)
            with (output / "report.csv").open(encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            browser_open = client.call("browser.open", {"url": url})
            expected_url = browser_open["result"]["url"]
            browser_fill = client.call("browser.act", {"action": "fill", "selector": "#field", "value": token, "expected_url": expected_url})
            browser_click = client.call("browser.act", {"action": "click", "selector": "#go", "expected_url": expected_url})
            observed = client.call("browser.observe")
            report["rounds"].append({"round": index + 1, "code": final["result"]["status"] == "completed" and rows == [{"name": "fixture", "value": token}],
                                     "browser": token in observed.get("result", {}).get("text", ""),
                                     "receipts": [queued["operation_id"], browser_open["operation_id"], browser_fill["operation_id"], browser_click["operation_id"]]})
            if native_app:
                attempts = []
                # Only a proven zero-dispatch stale rejection may be observed anew.
                # Each new attempt gets a new operation ID; unknown writes are never repeated.
                for attempt in range(2):
                    before = client.call("desktop.observe", {"app": native_app, "max_nodes": 600})
                    candidates = [n for n in before.get("result", {}).get("nodes", []) if n.get("name") == field and n["role"] == "text_field"]
                    if len(candidates) != 1:
                        raise RuntimeError("Explicit test field did not resolve uniquely")
                    action = client.call("desktop.act", {"app": native_app, "ref": candidates[0]["ref"], "action": "set_value", "value": token,
                                                         "observation_id": before["result"]["observation_id"]})
                    attempts.append({"operation_id": action["operation_id"], "status": action["status"], "dispatched": action["dispatched"]})
                    if not (action["dispatched"] is False and action.get("error_type") == "BokkioStaleSnapshot"):
                        break
                after = client.call("desktop.observe", {"app": native_app, "max_nodes": 600})
                passed = any(n.get("name") == field and n.get("value") == token for n in after.get("result", {}).get("nodes", []))
                report["native"].append({"round": index + 1, "passed": passed, "status": action["status"], "operation_id": action["operation_id"], "attempts": attempts})

        # Actual local admin CLI path, automated only for this explicitly owned fixture.
        approved_policy = {**policy, "require_approval": True}
        admin_client = Client(Runtime(output / "approval-state", approved_policy))
        admin_client.open()
        args = {"code": "print('approval fixture')", "cwd": str(output)}
        pending = admin_client.call("code.run", args, "approval-fixture")
        decision = subprocess.run([sys.executable, "-m", "bokkio.runtime_cli", "--state", str(admin_client.runtime.store.root),
                                   "approve", pending["approval_id"], "--decision", "approved", "--reason", "automated disposable acceptance"], capture_output=True, timeout=10)
        queued = admin_client.call("code.run", args, "approval-fixture")
        final = admin_client.wait_job(queued["result"]["job_id"], timeout=15)
        report["approval"] = {"passed": decision.returncode == 0 and final["result"]["status"] == "completed",
                              "mode": "automated_local_admin_cli_fixture", "operation_id": "approval-fixture"}
        admin_client.call("session.close")

        async def mcp_check():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            params = StdioServerParameters(command=sys.executable, args=["-m", "bokkio.runtime_cli", "--state", str(output / "state"),
                                                                         "--policy", str(policy_path), "serve"])
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as transport:
                    await transport.initialize()
                    tools = await transport.list_tools()
                    response = await transport.call_tool("audit.query", {"session_id": client.session_id, "arguments": {}})
                    return {"passed": not response.isError, "tools": len(tools.tools), "client": "official_mcp_sdk"}
        report["mcp"] = asyncio.run(mcp_check())
        cli = subprocess.run([sys.executable, "-m", "bokkio.runtime_cli", "--state", str(output / "state"), "--policy", str(policy_path),
                              "call", "metrics.summary", "--session", client.session_id], capture_output=True, text=True, timeout=10)
        report["cli"] = {"passed": cli.returncode == 0 and json.loads(cli.stdout)["status"] == "completed"}
        store = client.runtime.store
        events = store.query(session_id=client.session_id, limit=1000)
        stats = store.stats(client.session_id)
        report["audit"] = {"events": len(events), "logical_operations": stats["logical_operations"],
                           "reconciled": stats["logical_operations"] == len({e["operation_id"] for e in events if e["kind"] == "request.received"}),
                           "generated_code_parent_links": sum(bool(e["data"].get("parent_operation")) for e in events)}
        (output / "audit.jsonl").write_text(store.export(session_id=client.session_id), encoding="utf-8")
        (output / "audit.csv").write_text(store.export("csv", session_id=client.session_id), encoding="utf-8")
        report["stats"] = stats
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        client.call("session.close")
        web.shutdown()
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    required = all(r["code"] and r["browser"] for r in report["rounds"]) and len(report["rounds"]) == rounds
    required = required and not report.get("error") and (report.get("mcp") or {}).get("passed") and (report.get("approval") or {}).get("passed")
    required = required and (report.get("cli") or {}).get("passed") and (report.get("audit") or {}).get("reconciled")
    if native_app:
        required = required and len(report["native"]) == rounds and all(r["passed"] for r in report["native"])
    return report, bool(required)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-app", help="Explicitly authorized disposable app name/PID; writes test text")
    parser.add_argument("--field", default="Search")
    args = parser.parse_args()
    report, passed = run(args.output.resolve(), args.native_app, args.field)
    print(json.dumps({"passed": passed, "report": str(args.output.resolve() / "report.json"), "platform": report["platform"], "error": report.get("error")}, ensure_ascii=False))
    raise SystemExit(0 if passed else 1)
