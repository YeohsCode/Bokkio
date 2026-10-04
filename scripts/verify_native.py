"""Run live AX reads and actions against the disposable BokkioTest fixture."""
from __future__ import annotations

import argparse
import collections
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import time

from bokkio.selector import flatten


def cli(*args: str, expect_error: bool = False):
    result = subprocess.run(
        [sys.executable, "-m", "bokkio", *args], capture_output=True, text=True, timeout=45
    )
    if expect_error:
        assert result.returncode == 1, result.stdout
        return result.stderr.strip()
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def node_named(snapshot, role, name):
    matches = [n for n in flatten(snapshot["windows"]) if n["role"] == role and n["name"] == name]
    assert len(matches) == 1, (role, name, len(matches))
    return matches[0]


def verify(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    apps = cli("apps", "--json")
    assert any(app["name"] == "BokkioTest" for app in apps), "Launch the fixed BokkioTest app first"
    matrix = []
    for app in ["TextEdit", "Finder", "System Settings", "Safari", "BokkioTest"]:
        start = time.monotonic()
        first = cli("snapshot", "--app", app, "--json")
        second = cli("snapshot", "--app", app, "--json")
        nodes = flatten(first["windows"])
        other = flatten(second["windows"])
        refs = {n["ref"] for n in nodes}
        other_refs = {n["ref"] for n in other}
        previous = {n["ref"]: n for n in nodes}
        assert len(refs) == len(nodes), f"Duplicate refs in {app}"
        assert all(n["parent"] is None or n["parent"] in refs for n in nodes)
        assert all("read_error" not in n["platform_data"] for n in nodes)
        matrix.append({
            "app": app, "nodes": len(nodes), "roles": dict(collections.Counter(n["role"] for n in nodes)),
            "refs_unique": True, "refs_stable": refs == other_refs,
            "changed_refs": len(refs ^ other_refs), "raw_read_errors": 0,
            "names_changed_same_ref": sum(n["ref"] in previous and n["name"] != previous[n["ref"]]["name"] for n in other),
            "two_reads_seconds": round(time.monotonic() - start, 3),
        })
        print(json.dumps(matrix[-1]), flush=True)

    blank = cli("snapshot", "--app", "TextEdit", "--window", "Untitled", "--json")
    assert all(n["value"] in (None, "") for n in flatten(blank["windows"]) if n["role"] == "text_area"), "TextEdit Untitled must be empty"
    (output / "textedit-blank.json").write_text(json.dumps(blank, ensure_ascii=False, indent=2))
    fixture = cli("snapshot", "--app", "BokkioTest", "--json")
    (output / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2))
    matches = cli("find", "--app", "BokkioTest", "--role", "text_field", "--name", "Search")
    assert len(matches) == 1
    assert cli("get", matches[0]["ref"], "--app", "BokkioTest")["name"] == "Search"
    windows = cli("windows", "--app", "BokkioTest", "--json")
    main = next(w for w in windows if w["role"] == "window")
    selected = cli("snapshot", "--app", "BokkioTest", "--window", main["ref"], "--json")
    assert selected["windows"][0]["ref"] == main["ref"]
    assert cli("get", main["ref"], "--app", "BokkioTest")["role"] == "window"

    trace = []
    for run in range(1, 4):
        start = cli("snapshot", "--app", "BokkioTest", "--json")
        status_before = [n["name"] for n in flatten(start["windows"]) if (n["name"] or "").startswith("Status:")]
        click = cli("act", "--app", "BokkioTest", "--action", "click", "--role", "button", "--name", "Submit")
        fresh = cli("snapshot", "--app", "BokkioTest", "--json")
        status_after = [n["name"] for n in flatten(fresh["windows"]) if (n["name"] or "").startswith("Status:")]
        assert status_before != status_after, "Submit did not change status"
        write = cli("act", "--app", "BokkioTest", "--action", "set_value", "--role", "text_field", "--name", "Search", "--value", "")
        assert write["verification"] == "confirmed"
        focus = cli("act", "--app", "BokkioTest", "--action", "focus", "--role", "text_field", "--name", "Search")
        assert focus["verification"] == "confirmed"
        text = f"Bokkio native run {run}"
        typed = cli("act", "--app", "BokkioTest", "--action", "type", "--role", "text_field", "--name", "Search", "--value", text, "--expect-value", text)
        assert typed["verification"] == "confirmed", typed
        assert typed["after"]["value"] == text, typed
        nodes = flatten(fresh["windows"])
        table = node_named(fresh, "table", "Items")
        rows = [n for n in nodes if n["role"] == "table_row" and n["parent"] == table["ref"]]
        selected = cli("act", "--app", "BokkioTest", "--action", "select", "--ref", rows[run % 2]["ref"])
        assert selected["verification"] == "confirmed", selected
        trace.append({"run": run, "click": click, "set_value": write, "focus": focus, "type": typed, "select": selected, "status_after": status_after})
        print(f"Native action sequence {run}: passed", flush=True)

    bar = cli("find", "--app", "BokkioTest", "--role", "scroll_bar")
    assert len(bar) == 1
    scroll_ref = bar[0]["ref"]
    reset = cli("act", "--app", "BokkioTest", "--action", "scroll", "--ref", scroll_ref, "--direction", "up", "--amount", "1")
    assert reset["scroll"]["after_position"] == 0
    scroll_runs = []
    for run in range(1, 4):
        down = cli("act", "--app", "BokkioTest", "--action", "scroll", "--ref", scroll_ref, "--direction", "down")
        up = cli("act", "--app", "BokkioTest", "--action", "scroll", "--ref", scroll_ref, "--direction", "up")
        for result in [down, up]:
            assert result["verification"] == "confirmed", result
            assert result["scroll"]["content_nodes_moved"] > 0, result
        scroll_runs.append({"run": run, "down": down, "up": up})
        print(f"Native scroll sequence {run}: passed", flush=True)
    boundary = cli("act", "--app", "BokkioTest", "--action", "scroll", "--ref", scroll_ref, "--direction", "up")
    assert boundary["verification"] == "unconfirmed"
    assert boundary["scroll"]["reason"] == "at_boundary"
    mismatch = cli("act", "--app", "BokkioTest", "--action", "type", "--role", "text_field", "--name", "Search", "--value", "!", "--expect-value", "intentionally wrong")
    assert mismatch["verification"] == "unconfirmed"

    errors = {
        "stale_ref": cli("act", "--app", "BokkioTest", "--action", "click", "--ref", "missing-ref", expect_error=True),
        "ambiguous": cli("act", "--app", "BokkioTest", "--action", "set_value", "--role", "text_field", "--value", "x", expect_error=True),
        "unsupported": cli("act", "--app", "BokkioTest", "--action", "click", "--role", "text_area", "--name", "Notes", expect_error=True),
    }
    assert json.loads(errors["stale_ref"])["error"] == "stale_ref"
    assert json.loads(errors["ambiguous"])["error"] == "ambiguous_element"
    assert "not advertised" in errors["unsupported"]
    summary = {"date": date.today().isoformat(), "ref_strategy": "structural-v2", "apps_listed": len(apps), "matrix": matrix, "native_action_runs": 3, "native_scroll_runs": 3, "errors": errors}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    (output / "actions.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))
    (output / "scroll.json").write_text(json.dumps({"reset": reset, "runs": scroll_runs, "boundary": boundary}, ensure_ascii=False, indent=2))
    (output / "postcondition-mismatch.json").write_text(json.dumps(mismatch, ensure_ascii=False, indent=2))
    print(f"Evidence saved to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
