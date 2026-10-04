"""Windows-only UIA acceptance harness for the disposable WinForms fixture."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import time

from bokkio.selector import flatten
from verify_native import cli, node_named


def verify(output: Path, read_apps: list[str]):
    if sys.platform != "win32":
        raise SystemExit("Windows UIA verification requires an interactive Windows host")
    fixture_app = "xa11y-winforms-test-app"
    output.mkdir(parents=True, exist_ok=True)
    apps = cli("apps", "--json")
    assert any(a["name"].casefold() == fixture_app for a in apps), "Launch the fixed WinForms fixture first"
    matrix = []
    required = {"ref", "platform", "role", "name", "value", "state", "bounds", "parent", "children", "actions", "platform_data"}
    for app in [fixture_app, *read_apps]:
        started = time.monotonic()
        first = cli("snapshot", "--app", app, "--json")
        second = cli("snapshot", "--app", app, "--json")
        nodes, other = flatten(first["windows"]), flatten(second["windows"])
        refs = {n["ref"] for n in nodes}
        assert len(refs) == len(nodes)
        assert all(required <= n.keys() and n["platform"] == "windows" for n in nodes)
        assert all(n["parent"] is None or n["parent"] in refs for n in nodes)
        assert all("read_error" not in n["platform_data"] for n in nodes)
        matrix.append({"app": app, "nodes": len(nodes), "roles": dict(Counter(n["role"] for n in nodes)),
                       "refs_unique": True, "refs_stable": refs == {n["ref"] for n in other},
                       "two_reads_seconds": round(time.monotonic() - started, 3)})
        print(json.dumps(matrix[-1]), flush=True)
        (output / "matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    snapshot = cli("snapshot", "--app", fixture_app, "--json")
    assert snapshot["app"]["name"].casefold() == fixture_app
    search = node_named(snapshot, "text_field", "Search")
    (output / "fixture.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    assert cli("get", search["ref"], "--app", fixture_app)["name"] == "Search"
    trace = []
    for run in range(1, 4):
        before = cli("snapshot", "--app", fixture_app, "--json")
        old_status = [n["name"] for n in flatten(before["windows"]) if (n["name"] or "").startswith("Status:")]
        clicked = cli("act", "--app", fixture_app, "--action", "click", "--role", "button", "--name", "Submit")
        after = cli("snapshot", "--app", fixture_app, "--json")
        new_status = [n["name"] for n in flatten(after["windows"]) if (n["name"] or "").startswith("Status:")]
        assert old_status and new_status and old_status != new_status
        write = cli("act", "--app", fixture_app, "--action", "set_value", "--role", "text_field", "--name", "Search", "--value", "seed")
        assert write["verification"] == "confirmed", write
        cleared = cli("act", "--app", fixture_app, "--action", "set_value", "--role", "text_field", "--name", "Search", "--value", "")
        # xa11y 0.15.0 collapses empty UIA ValuePattern strings to None.
        # Preserve unconfirmed readback; exact typed text below verifies the reset.
        assert cleared["after"]["value"] in (None, ""), cleared
        focused = cli("act", "--app", fixture_app, "--action", "focus", "--role", "text_field", "--name", "Search")
        assert focused["verification"] == "confirmed", focused
        value = f"Bokkio Windows run {run}"
        typed = cli("act", "--app", fixture_app, "--action", "type", "--role", "text_field", "--name", "Search", "--value", value, "--expect-value", value)
        assert typed["verification"] == "confirmed", typed
        selected = cli("act", "--app", fixture_app, "--action", "select", "--role", "list_item", "--name", f"Item {1 + run % 2}")
        assert selected["verification"] == "confirmed", selected
        trace.append({"run": run, "click": clicked, "status_after": new_status, "set_value": write, "clear": cleared,
                      "focus": focused, "type": typed, "select": selected})
        (output / "actions.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Windows native action sequence {run}: passed", flush=True)
    stale = cli("act", "--app", fixture_app, "--action", "click", "--ref", "missing-ref", expect_error=True)
    assert json.loads(stale)["error"] == "stale_ref"
    output.mkdir(parents=True, exist_ok=True)
    summary = {"date": date.today().isoformat(), "host": platform.platform(), "python": platform.python_version(),
               "xa11y": version("xa11y"), "apps_listed": len(apps), "matrix": matrix, "native_action_runs": 3}
    for name, data in [("summary", summary), ("fixture", snapshot), ("actions", trace), ("stale-ref", json.loads(stale))]:
        (output / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidence saved to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--read-app", action="append", default=[], help="Additional read-only matrix application name or PID")
    args = parser.parse_args()
    verify(args.output, args.read_app)
