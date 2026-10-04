"""Test decision dispatch on native fixtures with a scripted offline provider."""
import argparse
import json
from pathlib import Path
from bokkio.decision import decide, execute_decision, options
from bokkio.model import BokkioActionError
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


class Scripted:
    def __init__(self, operation, token): self.operation, self.token = operation, token
    def ask(self, state, questions):
        answers = {"next": {"type": "choice", "choice": self.operation, "confidence": 0.95,
                           "probabilities": {k: float(k == self.operation) for k in questions["next"]["criteria"]}},
                   "goal_satisfied": {"type": "noul", "noul": 0}}
        head = self.operation + "_target"
        answers[head] = {"type": "choice", "choice": self.token, "confidence": 0.95,
                         "probabilities": {k: float(k == self.token) for k in questions[head]["criteria"]}}
        return {"model": "scripted-offline", "answers": answers}


def verify(output):
    b = Xa11yBackend(); app = "bokkio-interactions-fixture"; trace = []
    for action, role, name, params in [
        ("set_value", "text_field", "Search", {"value": "Decision runtime"}),
        ("click", "button", "Submit", {}),
        ("expand", "tree_item", "Parent", {}),
        ("expand", "combo_box", "Mode", {}),
        ("scroll", "group", "Scroll content", {"direction": "right"}),
    ]:
        snapshot = b.snapshot(app, "Bokkio interactions")
        target = next(n for n in flatten(snapshot["windows"]) if n["role"] == role and n["name"] == name)
        values = [params["value"]] if "value" in params else []
        choices = options(snapshot, values)
        token = next(k for k, c in choices.items() if c["action"] == action and c["ref"] == target["ref"] and all(c.get(a) == v for a, v in params.items()))
        decision, _ = decide(Scripted(action, token), f"{action} {name}", snapshot, values)
        result = execute_decision(b, app, decision)
        trace.append({"decision": decision.as_dict(), "result": result})
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"provider": "scripted-offline", "real_model_evaluation": False, "trace": trace}, indent=2), encoding="utf-8")
        if action == "click":
            assert any(n["name"] == "Submitted: Decision runtime" for n in flatten(b.snapshot(app)["windows"]))
        else:
            assert result["verification"] == "confirmed", result.get("scroll")
    b.perform(app, "collapse", role="combo_box", name="Mode")
    b.perform(app, "set_value", role="text_field", name="Search", value="changed after decision")
    try:
        execute_decision(b, app, decision)
        raise AssertionError("Old decision executed after snapshot changed")
    except BokkioActionError as error:
        trace.append({"stale_decision_rejected": str(error)})
    output.write_text(json.dumps({"provider": "scripted-offline", "real_model_evaluation": False, "native_actions_passed": 5, "trace": trace}, indent=2), encoding="utf-8")
    print(json.dumps({"provider": "scripted-offline", "native_actions_passed": 5, "stale_decision_rejected": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
