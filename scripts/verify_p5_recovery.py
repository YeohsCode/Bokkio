"""Force a native state change after real Jev, then verify real LLM recovery."""
import argparse
import json
from pathlib import Path
from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify(output):
    backend = Xa11yBackend(); provider = JevProvider(); app = "bokkio-interactions-fixture"
    backend.perform(app, "set_value", role="text_field", name="Search", value="")
    backend.perform(app, "click", role="button", name="Submit")
    class Changing:
        changed = False
        def ask(self, state, questions):
            response = provider.ask(state, questions)
            if not self.changed:
                backend.perform(app, "set_value", role="text_field", name="Search", value="Concurrent native change")
                self.changed = True
            return response
    output.mkdir(parents=True, exist_ok=True)
    trace = DesktopAgent(backend, OpenRouterPlanner(), Changing(), max_actions=8, max_replans=1).run(
        'Set Search to "P5 recovered" and click Submit so the status reads "Submitted: P5 recovered".', [app], output / "trace.json")
    nodes = flatten(backend.snapshot(app, "Bokkio interactions")["windows"])
    stale = any(e["kind"] == "error" and "Snapshot changed" in e.get("error", "") for e in trace["events"])
    checks = [any(n["name"] == "Search" and n["value"] == "P5 recovered" for n in nodes),
              any(n["name"] == "Submitted: P5 recovered" for n in nodes)]
    row = {"status": trace["status"], "actions": trace["actions"], "replans": trace["replans"], "stale_guard_observed": stale,
           "independent_checks": checks, "passed": trace["status"] == "completed" and stale and all(checks)}
    (output / "summary.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    print(json.dumps(row), flush=True)
    return row["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); raise SystemExit(0 if verify(args.output) else 1)
