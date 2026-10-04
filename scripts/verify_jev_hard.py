"""Real Jev native hard cases with fresh observations and outcome checks."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from bokkio.decision import decide, execute_decision
from bokkio.jev import JevProvider
from bokkio.model import BokkioError
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def run(fixture, output):
    import xa11y
    backend = Xa11yBackend(); provider = JevProvider(); rows = []
    process = subprocess.Popen([str(fixture.resolve())])
    app = str(process.pid)
    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"provider": provider.source, "real_model_evaluation": True,
                                     "passed": sum(r["passed"] for r in rows), "results": rows}, indent=2), encoding="utf-8")
    class Capture:
        calls = []
        def ask(self, state, questions):
            response = provider.ask(state, questions)
            self.calls.append(response)
            return response
    try:
        xa11y.App.by_pid(process.pid, timeout=15); time.sleep(1)
        # A real model's old decision must be rejected after native replacement.
        row = {"id": "tree-change-guard", "passed": False, "steps": []}; rows.append(row)
        try:
            snapshot = backend.snapshot(app)
            decision, response = decide(provider, "Click Old 2 in Dynamic items", snapshot)
            row.update(decision=decision.as_dict(), model_call=response)
            backend.perform(app, "click", role="button", name="Refresh")
            try:
                execute_decision(backend, app, decision)
                row["error"] = "Changed tree allowed old decision"
            except BokkioError as error:
                row["guard_error"] = str(error)
                row["passed"] = "Snapshot changed" in str(error)
        except BokkioError as error: row["error"] = str(error)
        save()
        specs = [("duplicate-parent", "Click Action in Right pane", "Clicked Right pane", 2),
                 ("dynamic-reobserve", "Click Fresh 2 in Dynamic items", "Clicked Fresh 2", 2),
                 ("deep-tree", "Select Leaf inside Workflow / Level 1 / Level 2 / Level 3 / Level 4 / Level 5 in Workflow folders. Expand the path as needed.", "Selected Leaf", 8)]
        for cid, goal, wanted, budget in specs:
            row = {"id": cid, "goal": goal, "passed": False, "steps": []}; rows.append(row)
            capture = Capture(); capture.calls = []
            try:
                for attempt in range(budget):
                    snapshot = backend.snapshot(app)
                    capture.calls = []
                    step = {"snapshot": snapshot, "model_calls": capture.calls}; row["steps"].append(step)
                    decision, response = decide(capture, goal, snapshot)
                    step["decision"] = decision.as_dict()
                    step["result"] = execute_decision(backend, app, decision)
                    fresh = backend.snapshot(app)
                    row["passed"] = any(n["name"] == wanted for n in flatten(fresh["windows"]))
                    row["expected_status"] = wanted
                    if row["passed"]: break
                if not row["passed"]: row["error"] = "Step budget exhausted"
            except BokkioError as error: row["error"] = str(error)
            save()
            print(json.dumps({"id": cid, "passed": row["passed"], "error": row.get("error")}), flush=True)
    finally:
        process.terminate(); process.wait(timeout=10)
    return all(r["passed"] for r in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture, args.output) else 1)
