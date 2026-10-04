"""Three real planner/Jev tasks across disposable native Windows applications."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def run(fixture, output):
    import xa11y
    backend = Xa11yBackend(); owned = []
    hard = subprocess.Popen([str(fixture.resolve())]); owned.append(hard)
    notepad = subprocess.Popen([str(Path(os.environ["SystemRoot"]) / "System32/notepad.exe")]); owned.append(notepad)
    apps = ["bokkio-interactions-fixture", str(hard.pid), str(notepad.pid)]
    try:
        for app in (hard, notepad): xa11y.App.by_pid(app.pid, timeout=20)
        time.sleep(1)
        output.mkdir(parents=True, exist_ok=True)
        backend.perform(apps[0], "set_value", role="text_field", name="Search", value="")
        backend.perform(apps[0], "click", role="button", name="Submit")
        backend.perform(apps[0], "expand", role="combo_box", name="Mode")
        backend.perform(apps[0], "select", role="list_item", name="First")
        backend.perform(apps[0], "collapse", role="combo_box", name="Mode")
        goals = [
            'In bokkio-interactions-fixture set Search to "P5 cross app one" and click Submit so its status is "Submitted: P5 cross app one". Then in Bokkio Jev hard click Action in Right pane so its status is "Clicked Right pane".',
            'In bokkio-interactions-fixture select Second in Mode. Then in Notepad replace the document text with "P5 cross app two".',
            'In Notepad replace the document text with "P5 cross app three". Then in Bokkio Jev hard click Refresh and click Fresh 2 in Dynamic items so its status is "Clicked Fresh 2".',
        ]
        rows = []
        for i, goal in enumerate(goals, 1):
            trace = DesktopAgent(backend, OpenRouterPlanner(), JevProvider(), max_actions=16, max_replans=1).run(goal, apps, output / f"task-{i}.json")
            # Verify user-requested outcomes independently of the generated plan.
            main = flatten(backend.snapshot(apps[0], "Bokkio interactions")["windows"])
            hard_nodes = flatten(backend.snapshot(apps[1])["windows"])
            note = flatten(backend.snapshot(apps[2])["windows"])
            if i == 1:
                checks = [any(n["name"] == "Submitted: P5 cross app one" for n in main), any(n["name"] == "Clicked Right pane" for n in hard_nodes)]
            elif i == 2:
                checks = [any(n["role"] == "combo_box" and n["name"] == "Mode" and n["value"] == "Second" for n in main),
                          any(n["role"] == "text_area" and n["value"] == "P5 cross app two" for n in note)]
            else:
                checks = [any(n["role"] == "text_area" and n["value"] == "P5 cross app three" for n in note), any(n["name"] == "Clicked Fresh 2" for n in hard_nodes)]
            row = {"id": i, "status": trace["status"], "actions": trace["actions"], "replans": trace["replans"], "independent_checks": checks,
                   "passed": trace["status"] == "completed" and all(checks)}
            rows.append(row)
            (output / "summary.json").write_text(json.dumps({"passed": sum(r["passed"] for r in rows), "tasks": 3, "results": rows}, indent=2), encoding="utf-8")
            print(json.dumps(row), flush=True)
        return all(r["passed"] for r in rows)
    finally:
        # Only processes started by this verifier are closed; no user's documents.
        for process in owned:
            process.terminate(); process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture, args.output) else 1)
