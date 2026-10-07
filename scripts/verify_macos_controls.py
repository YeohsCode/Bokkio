"""Native action and two-axis scroll checks on fresh, owned Cocoa fixtures."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import time

from bokkio.selector import flatten
from bokkio.workflow import save_json
from bokkio.xa11y_backend import Xa11yBackend
from verify_macos_horizontal import verify as verify_scroll


def run(fixture, scrolling, output):
    import xa11y
    output.mkdir(parents=True, exist_ok=False)
    backend = Xa11yBackend()
    summary = {"action_runs": [], "scroll_actions": 0, "scope": "owned_macos_native",
               "fixture_sha256": {p.stem: hashlib.sha256((p / "Contents/MacOS" / p.stem).read_bytes()).hexdigest()
                                  for p in (fixture, scrolling)}}
    process = None
    try:
        for bundle in (scrolling, fixture):
            process = subprocess.Popen([str(bundle / "Contents/MacOS" / bundle.stem)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            xa11y.App.by_pid(process.pid, timeout=15)
            time.sleep(1)
            app = str(process.pid)
            if bundle == scrolling:
                verify_scroll(output / "scroll.json", app)
                summary["scroll_actions"] = 12
            else:
                for i in range(1, 4):
                    actions = []
                    actions.append(backend.perform(app, "set_value", role="text_field", name="Search", value=""))
                    actions.append(backend.perform(app, "focus", role="text_field", name="Search"))
                    value = f"Mac native run {i}"
                    actions.append(backend.perform(app, "type", role="text_field", name="Search", value=value, expected_value=value))
                    snapshot = backend.snapshot(app)
                    before = next(n["name"] for n in flatten(snapshot["windows"]) if (n["name"] or "").startswith("Status:"))
                    actions.append(backend.perform(app, "click", role="button", name="Submit"))
                    nodes = flatten(backend.snapshot(app)["windows"])
                    table = next(n for n in nodes if n["role"] == "table" and n["name"] == "Items")
                    rows = [n for n in nodes if n["role"] == "table_row" and n["parent"] == table["ref"]]
                    actions.append(backend.perform(app, "select", ref=rows[i % 2]["ref"]))
                    fresh = backend.snapshot(app)
                    nodes = flatten(fresh["windows"])
                    checks = [any(n["name"] == "Search" and n["value"] == value for n in nodes),
                              any((n["name"] or "").startswith("Status:") and n["name"] != before for n in nodes),
                              actions[-1]["verification"] == "confirmed" and actions[-1]["after"]["state"]["selected"]]
                    save_json(output / f"actions-{i}.json", {"actions": actions, "independent_snapshot": fresh, "checks": checks})
                    summary["action_runs"].append({"run": i, "native_dispatches": len(actions), "independent_checks": checks, "passed": all(checks)})
                    save_json(output / "summary.json", summary)
                    assert all(checks), checks
            process.terminate()
            process.wait(timeout=10)
            process = None
        summary["passed"] = len(summary["action_runs"]) == 3 and all(r["passed"] for r in summary["action_runs"]) and summary["scroll_actions"] == 12
        save_json(output / "summary.json", summary)
        return summary["passed"]
    except Exception as error:
        summary.update(passed=False, error=str(error))
        save_json(output / "summary.json", summary)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path("/tmp/BokkioTest.app"))
    parser.add_argument("--scroll-fixture", type=Path, default=Path("/tmp/BokkioInteractions.app"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture, args.scroll_fixture, args.output) else 1)
