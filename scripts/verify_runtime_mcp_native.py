"""Manifest-driven native field task over MCP; no application recipes in Core.

Automatic approval is opt-in and allowed only for an owned disposable fixture.
Without it, pending exact requests are saved for separate administrator review.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid


async def run(args):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.approve_owned_fixture and manifest.get("scope") != "owned_disposable_fixture":
        raise ValueError("Automatic test approval requires an owned_disposable_fixture manifest")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"scope": manifest.get("scope"), "caller": "official_mcp_client_manifest_runner",
              "approval_mode": "automated_admin_owned_fixture" if args.approve_owned_fixture else "separate_administrator",
              "tasks": []}
    params = StdioServerParameters(command=sys.executable, args=["-m", "bokkio.runtime_cli", "--state", str(args.state.resolve()),
                                                                "--policy", str(args.policy.resolve()), "serve"])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            opened = await client.call_tool("session.open", {"arguments": {"task_id": "mcp-native-" + uuid.uuid4().hex}})
            if opened.isError:
                raise RuntimeError(opened.structuredContent)
            session = opened.structuredContent["result"]["session_id"]
            async def call(tool, data, operation=None):
                response = await client.call_tool(tool, {"arguments": data, "session_id": session,
                                                         **({"operation_id": operation} if operation else {})})
                return response.structuredContent
            pending_left_open = False
            try:
                for index, task in enumerate(manifest["tasks"]):
                    source = Path(task["source"]).resolve() if task.get("source") else None
                    initial_hash = None
                    if source:
                        checked = await call("evidence.check", {"path": str(source)})
                        if not checked.get("result", {}).get("passed"):
                            raise RuntimeError("Test source is not granted or unavailable")
                        initial_hash = checked["result"]["artifact"]["sha256"]
                    observed = await call("desktop.observe", {"app": manifest["app"], "window": task["window"],
                                                               "max_nodes": 2000, "max_bytes": 1000000})
                    if observed["status"] != "completed" or observed["result"]["truncated"]:
                        raise RuntimeError("Cannot select from a failed or truncated observation")
                    matching = [n for n in observed["result"]["nodes"] if all(n.get(key) == value for key, value in task["match"].items())]
                    if len(matching) != 1 or "set_value" not in matching[0]["actions"]:
                        raise ValueError("Task field must match one writable observed node")
                    operation = uuid.uuid4().hex
                    request = {"app": manifest["app"], "window": task["window"], "ref": matching[0]["ref"],
                               "observation_id": observed["result"]["observation_id"], "action": "set_value", "value": task["value"]}
                    receipt = await call("desktop.act", request, operation)
                    if receipt["status"] == "approval_required":
                        if not args.approve_owned_fixture:
                            pending_left_open = True
                            report.update(status="approval_required", session_id=session, operation_id=operation,
                                          approval_id=receipt["approval_id"], exact_request=request)
                            break
                        subprocess.run([sys.executable, "-m", "bokkio.runtime_cli", "--state", str(args.state.resolve()), "approve",
                                        receipt["approval_id"], "--decision", "approved", "--reason", "Explicitly owned disposable manifest test"],
                                       capture_output=True, check=True, timeout=10)
                        receipt = await call("desktop.act", request, operation)
                    after = await call("desktop.observe", {"app": manifest["app"], "window": task["window"],
                                                            "max_nodes": 2000, "max_bytes": 1000000})
                    checks = [{**{k: v for k, v in task["match"].items() if k != "value"}, "value": task["value"]}, *task.get("readback", [])]
                    nodes = after.get("result", {}).get("nodes", [])
                    readback = after["status"] == "completed" and all(any(all(n.get(k) == v for k, v in check.items()) for n in nodes) for check in checks)
                    unchanged = source is None or hashlib.sha256(source.read_bytes()).hexdigest() == initial_hash
                    report["tasks"].append({"task": index + 1, "passed": receipt["status"] == "verified" and readback and unchanged,
                                            "status": receipt["status"], "dispatched": receipt["dispatched"], "readback": readback,
                                            "source_unchanged": unchanged, "operation_id": operation, "error": receipt.get("error")})
                if not pending_left_open:
                    report.update(status="completed", passed=sum(t["passed"] for t in report["tasks"]), total=len(manifest["tasks"]))
                    report["metrics"] = (await call("metrics.summary", {}))["result"]
                    report["audit_artifact"] = (await call("audit.export", {"format": "jsonl"}))["result"]["artifact"]
            finally:
                (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                if not pending_left_open:
                    await call("session.close", {})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approve-owned-fixture", action="store_true")
    report = asyncio.run(run(parser.parse_args()))
    print(json.dumps({k: report.get(k) for k in ("status", "passed", "total", "approval_id")}, ensure_ascii=False))
    raise SystemExit(0 if report.get("status") == "approval_required" or report.get("passed") == report.get("total") else 1)
