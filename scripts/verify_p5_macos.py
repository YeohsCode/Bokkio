"""Three real planner/Jev tasks across owned Cocoa apps with native preflight."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from bokkio.model import BokkioError
from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def run(first, second, output):
    import xa11y
    backend = Xa11yBackend()
    output.mkdir(parents=True, exist_ok=True)
    owned = []
    try:
        for bundle in (first, second):
            process = subprocess.Popen([str(bundle / "Contents/MacOS" / bundle.stem)])
            owned.append(process); xa11y.App.by_pid(process.pid, timeout=15)
        time.sleep(1)
        apps = [str(p.pid) for p in owned]; rows = []
        for app in apps:
            try:
                nodes = flatten(backend.snapshot(app)["windows"])
                if not any(n["role"] == "text_field" and n["name"] == "Search" for n in nodes) or not any(n["role"] == "button" and n["name"] == "Submit" for n in nodes):
                    raise BokkioError("Owned fixture Search/Submit controls are unavailable")
            except BokkioError as error:
                summary = {"status": "failed", "phase": "native_preflight", "reason": str(error),
                           "tasks": 3, "attempted": 0, "passed": 0,
                           "foreground": [a["name"] for a in backend.apps() if a["is_foreground"]]}
                (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(json.dumps(summary), flush=True)
                return False
        for iteration in (1, 2, 3):
            value_a, value_b = f"P5 Mac source {iteration}", f"P5 Mac received {iteration}"
            goal = f'In BokkioWorkflowA set Search to "{value_a}" and click Submit so its status is "Submitted: {value_a}". Then in BokkioWorkflowB set Search to "{value_b}" and click Submit so its status is "Submitted: {value_b}".'
            trace = DesktopAgent(backend, OpenRouterPlanner(), JevProvider(), max_actions=12, max_replans=1).run(goal, apps, output / f"task-{iteration}.json")
            checks = []
            for app, value in zip(apps, (value_a, value_b)):
                nodes = flatten(backend.snapshot(app)["windows"])
                checks.append(any(n["role"] == "text_field" and n["name"] == "Search" and n["value"] == value for n in nodes)
                              and any(n["name"] == f"Submitted: {value}" for n in nodes))
            row = {"id": iteration, "status": trace["status"], "actions": trace["actions"], "replans": trace["replans"],
                   "independent_checks": checks, "passed": trace["status"] == "completed" and all(checks)}
            rows.append(row)
            (output / "summary.json").write_text(json.dumps({"tasks": 3, "passed": sum(r["passed"] for r in rows), "results": rows}, indent=2), encoding="utf-8")
            print(json.dumps(row), flush=True)
        return all(r["passed"] for r in rows)
    finally:
        for process in owned: process.terminate(); process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-a", type=Path, default=Path("/tmp/BokkioWorkflowA.app"))
    parser.add_argument("--fixture-b", type=Path, default=Path("/tmp/BokkioWorkflowB.app"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture_a, args.fixture_b, args.output) else 1)
