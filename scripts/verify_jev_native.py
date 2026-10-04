"""Real Jev decisions and independently checked outcomes on native fixtures."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
from bokkio.decision import decide, execute_decision
from bokkio.jev import JevProvider
from bokkio.model import BokkioError
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


class Capture:
    def __init__(self, provider): self.provider, self.response = provider, None
    def ask(self, state, questions):
        self.response = self.provider.ask(state, questions)
        return self.response


def run(output: Path):
    backend = Xa11yBackend(); provider = JevProvider(); capture = Capture(provider)
    app = "bokkio-interactions-fixture"; window = "Bokkio interactions"; rows = []
    specs = [
        ("input", 'Set Search to "Bokkio Jev native"', ["Bokkio Jev native"], "text_field", "Search", "value", "Bokkio Jev native"),
        ("submit", "Click Submit", [], "static_text", "Submitted: Bokkio Jev native", "name", "Submitted: Bokkio Jev native"),
        ("tree", "Expand Parent in Folders", [], "tree_item", "Parent", "expanded", True),
        ("dropdown", "Select Second in the Mode dropdown", [], "combo_box", "Mode", "value", "Second"),
        ("scroll", "Scroll the Scroll content container to the right", [], "group", "Scroll content", "scroll", None),
    ]
    # Reset only the known disposable fixture before independent tasks.
    backend.perform(app, "collapse", role="tree_item", name="Parent")
    backend.perform(app, "collapse", role="combo_box", name="Mode")
    backend.perform(app, "expand", role="combo_box", name="Mode")
    backend.perform(app, "select", role="list_item", name="First")
    backend.perform(app, "collapse", role="combo_box", name="Mode")
    backend.perform(app, "set_value", role="text_field", name="Search", value="")
    backend.perform(app, "scroll", role="group", name="Scroll content", direction="left", amount=1)
    for cid, goal, values, role, name, check, wanted in specs:
        if cid == "scroll":
            backend.perform(app, "collapse", role="combo_box", name="Mode")
        row = {"id": cid, "goal": goal, "passed": False}; capture.response = None
        started = time.monotonic()
        row["steps"] = []
        try:
            for attempt in range(3):
                snapshot = backend.snapshot(app, window)
                decision, _ = decide(capture, goal, snapshot, values)
                step = {"decision": decision.as_dict()}
                result = execute_decision(backend, app, decision)
                step["result"] = result
                step["model_call"] = {k: capture.response.get(k) for k in ("model", "source", "answers", "usage", "elapsed_seconds")}
                row["steps"].append(step)
                fresh = backend.snapshot(app, window)
                nodes = flatten(fresh["windows"])
                if check == "scroll":
                    scope = next(n for n in nodes if n["role"] == role and n["name"] == name)
                    before_scope = next(n for n in flatten(snapshot["windows"]) if n["role"] == role and n["name"] == name)
                    actual = scope["platform_data"]["scroll"]["x"]["position"]
                    old_position = before_scope["platform_data"]["scroll"]["x"]["position"]
                    old_buttons = {n["ref"]: n for n in flatten([before_scope]) if n["role"] == "button"}
                    moved = sum(n["ref"] in old_buttons and n["bounds"]["x"] < old_buttons[n["ref"]]["bounds"]["x"] for n in flatten([scope]) if n["role"] == "button")
                    row["outcome"] = {"before_position": old_position, "after_position": actual, "buttons_moved_left": moved}
                    row["passed"] = actual > old_position and moved > 0
                else:
                    target = next(n for n in nodes if n["role"] == role and n["name"] == name)
                    actual = target["state"][check] if check == "expanded" else target[check]
                    row["outcome"] = {"check": check, "expected": wanted, "actual": actual}
                    row["passed"] = actual == wanted
                if row["passed"]:
                    break
        except (BokkioError, StopIteration) as error:
            row["error"] = str(error) or "Expected native outcome missing"
        if capture.response:
            row["model_call"] = {k: capture.response.get(k) for k in ("model", "source", "answers", "usage", "elapsed_seconds")}
        row["total_seconds"] = round(time.monotonic() - started, 3)
        rows.append(row)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"provider": provider.source, "real_model_evaluation": True,
                                     "passed": sum(r["passed"] for r in rows), "tasks": 5, "results": rows}, indent=2), encoding="utf-8")
        print(json.dumps({"id": cid, "passed": row["passed"], "error": row.get("error")}), flush=True)
    return all(r["passed"] for r in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(0 if run(parser.parse_args().output) else 1)
