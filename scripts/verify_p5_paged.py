"""Real Planner/Jev/UIA checks with targets absent until native pagination."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.model import BokkioLookupError
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


class Timed:
    """Measure actual calls without changing observations or model responses."""
    def __init__(self, wrapped, samples, group):
        self.wrapped, self.samples, self.group = wrapped, samples, group

    def __getattr__(self, name):
        original = getattr(self.wrapped, name)
        if not callable(original): return original
        def call(*args, **kwargs):
            started = time.perf_counter()
            try: return original(*args, **kwargs)
            finally: self.samples.append({"operation": f"{self.group}.{name}", "seconds": round(time.perf_counter() - started, 6)})
        return call


def run(fixture, output, *, preflight_only=False):
    import xa11y
    output.mkdir(parents=True, exist_ok=True)
    backend = Xa11yBackend()
    owned, results = [], []

    def start(path):
        process = subprocess.Popen([str(path.resolve())]); owned.append(process)
        xa11y.App.by_pid(process.pid, timeout=20)
        time.sleep(1)
        return str(process.pid)

    def nodes(app): return flatten(backend.snapshot(app)["windows"])
    def row_names(snapshot):
        return sorted(n["name"] for n in flatten(snapshot["windows"])
                      if n["role"] == "button" and (n["name"] or "").startswith("Row "))
    def reset(app):
        backend.perform(app, "set_value", role="text_field", name="Page", value="1")
        backend.perform(app, "click", role="button", name="Go")

    try:
        app = start(fixture)
        baseline = backend.snapshot(app)
        old = next(n for n in flatten(baseline["windows"]) if n["name"] == "Row 1")
        backend.perform(app, "click", role="button", name="Next")
        rejected, error_code = False, None
        try: backend.perform(app, "click", ref=old["ref"])
        except BokkioLookupError as error:
            error_code = error.code
            rejected = error_code == "stale_ref"
        preflight = {"initial_rows": row_names(baseline), "after_next_rows": row_names(backend.snapshot(app)),
                     "old_ref_rejected": rejected, "old_ref_error": error_code}
        preflight["passed"] = (set(preflight["initial_rows"]) == {f"Row {i}" for i in range(1, 26)}
                               and set(preflight["after_next_rows"]) == {f"Row {i}" for i in range(26, 51)} and rejected)
        (output / "preflight.json").write_text(json.dumps(preflight, indent=2), encoding="utf-8")
        if not preflight["passed"]: raise RuntimeError("Partial UIA exposure or stale-ref preflight failed")
        if preflight_only:
            print(json.dumps(preflight), flush=True)
            return True
        note = start(Path(os.environ["SystemRoot"]) / "System32/notepad.exe")

        cases = [
            ("hidden_target_cross_app", [app, note],
             'In Bokkio paged rows set Page to "40" and click Go so the range reads '
             '"Page 40 of 40: rows 976 to 1000". Then activate Row 997 so the status reads '
             '"Activated Row 997". Finally in Notepad replace the document with '
             '"P5 paged result 997". Keep this order.', "Row 997", "Page 40 of 40: rows 976 to 1000"),
            ("next_page_target", [app],
             'In Bokkio paged rows click Next so the range reads "Page 2 of 40: rows 26 to 50". '
             'Then activate Row 37 so the status reads "Activated Row 37". Keep this order.',
             "Row 37", "Page 2 of 40: rows 26 to 50"),
        ]
        for name, apps, goal, target, expected_range in cases:
            reset(app)
            before = backend.snapshot(app)
            samples = []
            agent = DesktopAgent(Timed(backend, samples, "native"),
                                 Timed(OpenRouterPlanner(), samples, "planner"),
                                 Timed(JevProvider(), samples, "jev"), max_actions=8, max_replans=2)
            started = time.perf_counter()
            trace = agent.run(goal, apps, output / f"{name}.json")
            elapsed = time.perf_counter() - started
            actions = [e for e in trace["events"] if e["kind"] == "action"]
            action_names = [e["result"]["before"]["name"] for e in actions]
            target_actions = [e for e in actions if e["result"]["before"]["name"] == target]
            target_decisions = [e for e in trace["events"] if e["kind"] == "observation"
                                and any(n["name"] == target for n in flatten(e["snapshot"]["windows"]))]
            final = nodes(app)
            expected_order = ["Page", "Go", target] if name == "hidden_target_cross_app" else ["Next", target]
            checks = [target not in row_names(before), len(row_names(before)) == 25,
                      any(n["name"] == expected_range for n in final),
                      any(n["name"] == "Activated " + target for n in final),
                      len(target_actions) == 1, bool(target_decisions),
                      action_names[:len(expected_order)] == expected_order]
            if name == "hidden_target_cross_app":
                checks.append(any(n["role"] == "text_area" and n["value"] == "P5 paged result 997" for n in nodes(note)))
            totals = {}
            for sample in samples:
                totals[sample["operation"]] = round(totals.get(sample["operation"], 0) + sample["seconds"], 6)
            row = {"case": name, "status": trace["status"], "actions": trace["actions"], "replans": trace["replans"],
                   "independent_checks": checks, "passed": trace["status"] == "completed" and all(checks),
                   "action_names": action_names, "elapsed_seconds": round(elapsed, 3), "call_seconds": totals}
            results.append(row)
            (output / f"{name}-timing.json").write_text(json.dumps(samples, indent=2), encoding="utf-8")
            (output / "summary.json").write_text(json.dumps({"tasks": len(cases), "attempted": len(results),
                "passed": sum(r["passed"] for r in results), "results": results}, indent=2), encoding="utf-8")
            print(json.dumps(row), flush=True)
        return all(r["passed"] for r in results)
    finally:
        for process in owned:
            if process.poll() is None: process.terminate(); process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true", help="Check native exposure and stale refs without model calls")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.fixture, args.output, preflight_only=args.preflight_only) else 1)
