"""Exercise native macOS recording/replay and compile a successful owned-app trace.

Only fresh Bokkio Cocoa fixture processes are authorized. Replays use semantic
AX actions and no model calls. The input trace must come from verify_p5_macos.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from bokkio.model import BokkioError
from bokkio.selector import flatten
from bokkio.workflow import (
    Recorder, WorkflowReplay, from_agent_trace, make_workflow, repair_version, save_json,
)
from bokkio.xa11y_backend import Xa11yBackend


def run(first: Path, second: Path, trace_path: Path, output: Path) -> bool:
    import xa11y

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if len(trace.get("apps", [])) != 2:
        raise BokkioError("Expected a successful two-fixture macOS trace")
    output.mkdir(parents=True, exist_ok=False)
    source_root = Path(__file__).resolve().parents[1]
    files = [Path(__file__), *[source_root / "src/bokkio" / name for name in
             ("workflow.py", "workflow_inputs.py", "xa11y_backend.py", "agent.py", "planner.py")]]
    summary = {"scope": "owned_macos_native", "recorded_replays": [], "agent_trace_replays": [],
               "source_sha256": {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
               "fixture_sha256": {p.stem: hashlib.sha256((p / "Contents/MacOS" / p.stem).read_bytes()).hexdigest()
                                  for p in (first, second)},
               "input_trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    backend = Xa11yBackend()
    processes = []

    def close():
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        processes.clear()

    def start(reorder=False):
        close()
        for bundle in (first, second):
            environment = dict(os.environ)
            environment.pop("BOKKIO_FIXTURE_REORDER", None)
            if reorder:
                environment["BOKKIO_FIXTURE_REORDER"] = "1"
            p = subprocess.Popen([str(bundle / "Contents/MacOS" / bundle.stem)], env=environment,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(p)
            xa11y.App.by_pid(p.pid, timeout=15)
        time.sleep(1)
        return {"source": str(processes[0].pid), "destination": str(processes[1].pid)}

    def checks(bindings, values):
        results = []
        for alias, value in zip(("source", "destination"), values):
            snapshot = backend.snapshot(bindings[alias])
            nodes = flatten(snapshot["windows"])
            results.append(any(n["role"] == "text_field" and n["name"] == "Search" and n["value"] == value for n in nodes)
                           and any(n["name"] == "Submitted: " + value for n in nodes))
        return results

    def replay_case(workflow, values, name, target):
        bindings = start()
        report = WorkflowReplay(backend).run(workflow, bindings, output / (name + ".json"))
        independent = checks(bindings, values)
        row = {"status": report["status"], "native_dispatches": sum(s["dispatched"] for s in report["steps"]),
               "independent_checks": independent, "passed": report["status"] == "completed" and all(independent)}
        target.append(row)
        save_json(output / "summary.json", summary)
        print(json.dumps({"case": name, **row}), flush=True)

    try:
        bindings = start()
        recorder = Recorder(backend, bindings)
        values = ("P6 Mac source", "P6 Mac received")
        recorder.perform("source", "focus", intent="Focus Search", role="text_field", name="Search")
        recorder.perform("source", "type", intent="Write source", role="text_field", name="Search", value=values[0], expected_value=values[0])
        for alias, value in zip(("source", "destination"), values):
            if alias == "destination":
                recorder.perform(alias, "set_value", intent="Write received text", role="text_field", name="Search", value=value)
            recorder.perform(alias, "click", intent="Submit native text", role="button", name="Submit",
                             verify=[{"role": "static_text", "name": "Submitted: " + value, "field": "present", "equals": True}])
        recorded = recorder.export("Mac AX cross-app input and submit")
        save_json(output / "recorded-workflow.json", recorded)
        save_json(output / "recording.json", recorder.events)
        for i in range(1, 4):
            replay_case(recorded, values, f"recorded-replay-{i}", summary["recorded_replays"])

        def child_order(snapshot):
            window = next(n for n in flatten(snapshot["windows"]) if n["role"] == "window")
            return [n["name"] for n in window["children"]]
        baseline_order = child_order(recorder.events[0]["before"])
        bindings = start(reorder=True)
        reordered_snapshot = backend.snapshot(bindings["source"])
        reordered_order = child_order(reordered_snapshot)
        save_json(output / "reordered-before.json", reordered_snapshot)
        reordered_run = WorkflowReplay(backend).run(recorded, bindings, output / "reordered-replay.json")
        summary["structure_reorder"] = {"before_order": baseline_order, "after_order": reordered_order,
                                        "same_workflow_sha256": reordered_run["workflow_sha256"] == recorded["sha256"],
                                        "passed": baseline_order != reordered_order and reordered_run["status"] == "completed"
                                                  and all(checks(bindings, values))}

        steps = copy.deepcopy(recorded["steps"])
        steps[0]["target"]["name"] = "Missing Search"
        broken = make_workflow(recorded["name"], steps, "macos_selector_failure")
        save_json(output / "broken-workflow.json", broken)
        bindings = start()
        failed = WorkflowReplay(backend, timeout=0).run(broken, bindings, output / "failed-run.json")
        repaired = repair_version(broken, failed, recorded["steps"], "Restore selector from verified Mac AX recording")
        save_json(output / "repaired-workflow.json", repaired)
        fixed = WorkflowReplay(backend).run(repaired, bindings, output / "repair-replay.json")
        summary["repair"] = {"failed_dispatches": sum(s["dispatched"] for s in failed["steps"]),
                             "parent_preserved": repaired["parent_sha256"] == broken["sha256"],
                             "passed": failed["status"] == "failed" and not any(s["dispatched"] for s in failed["steps"])
                                       and fixed["status"] == "completed" and all(checks(bindings, values))}

        bindings = start()
        # Pause before the destination write. Source outcomes remain present;
        # resume must dispatch only the final two actions, retaining receipts.
        def control():
            report = json.loads((output / "paused.json").read_text(encoding="utf-8"))
            return "pause" if sum(s["status"] == "completed" for s in report["steps"]) >= 3 else None
        paused = WorkflowReplay(backend, control=control).run(recorded, bindings, output / "paused.json")
        resumed = WorkflowReplay(backend).run(recorded, bindings, output / "resumed.json", resume=paused)
        summary["resume"] = {"pause_status": paused["status"], "completed_before_pause": sum(s["status"] == "completed" for s in paused["steps"]),
                             "remaining_dispatches": sum(s["dispatched"] for s in resumed["steps"]) - sum(s["dispatched"] for s in paused["steps"]),
                             "passed": paused["status"] == "paused" and resumed["status"] == "completed" and all(checks(bindings, values))}

        aliases = dict(zip(trace["apps"], ("source", "destination")))
        compiled = from_agent_trace(trace, "Successful Mac Planner/Jev trace", aliases)
        save_json(output / "agent-workflow.json", compiled)
        expected = []
        for alias in ("source", "destination"):
            writes = [s["arguments"]["value"] for s in compiled["steps"]
                      if s["app"] == alias and s["action"] in {"type", "set_value"}]
            if not writes:
                raise BokkioError("Successful trace lacks verified native text")
            expected.append(writes[-1])
        for i in range(1, 4):
            replay_case(compiled, expected, f"agent-replay-{i}", summary["agent_trace_replays"])
        summary["passed"] = (all(r["passed"] for r in summary["recorded_replays"] + summary["agent_trace_replays"])
                             and summary["repair"]["passed"] and summary["resume"]["passed"]
                             and summary["structure_reorder"]["passed"]
                             and summary["resume"]["remaining_dispatches"] == 2)
        save_json(output / "summary.json", summary)
        return summary["passed"]
    except Exception as error:
        summary.update(passed=False, error=str(error))
        save_json(output / "summary.json", summary)
        raise
    finally:
        close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-a", type=Path, default=Path("/tmp/BokkioWorkflowA.app"))
    parser.add_argument("--fixture-b", type=Path, default=Path("/tmp/BokkioWorkflowB.app"))
    parser.add_argument("--agent-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture_a, args.fixture_b, args.agent_trace, args.output) else 1)
