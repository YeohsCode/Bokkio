"""Verify native planning can discover Submit beside a named Search field."""
import argparse
import json
from pathlib import Path
from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify(output):
    backend = Xa11yBackend(); app = "bokkio-interactions-fixture"
    output.mkdir(parents=True, exist_ok=True)
    backend.perform(app, "set_value", role="text_field", name="Search", value="")
    backend.perform(app, "click", role="button", name="Submit")
    goal = 'In Bokkio interactions search for "P5 neighbor" so its status reads "Submitted: P5 neighbor".'
    trace = DesktopAgent(backend, OpenRouterPlanner(), JevProvider(), max_actions=6, max_replans=1).run(
        goal, [app], output / "trace.json")
    observations = next(e["observations"][app] for e in trace["events"] if e["kind"] == "planner_observations")
    nodes = flatten(backend.snapshot(app)["windows"])
    checks = [any(n["name"] == "Submit" for n in observations["nodes"]),
              any(n["name"] == "Search" and n["value"] == "P5 neighbor" for n in nodes),
              any(n["name"] == "Submitted: P5 neighbor" for n in nodes)]
    row = {"status": trace["status"], "actions": trace["actions"], "replans": trace["replans"],
           "independent_checks": checks, "passed": trace["status"] == "completed" and all(checks),
           "planner_scope": observations["observation_scope"]}
    (output / "summary.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    print(json.dumps(row), flush=True)
    return row["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(0 if verify(parser.parse_args().output) else 1)
