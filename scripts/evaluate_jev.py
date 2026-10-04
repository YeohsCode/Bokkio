"""Evaluate real Jev choices on saved native snapshots without executing actions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from bokkio.decision import decide
from bokkio.jev import JevProvider
from bokkio.model import BokkioError


def evaluate(cases_path: Path, output: Path):
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    provider = JevProvider()
    class Capture:
        response = None
        questions = None
        responses = None
        def ask(self, state, questions):
            self.questions = questions
            self.response = provider.ask(state, questions)
            self.responses.append(self.response)
            return self.response
    capture = Capture()
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for case in cases:
        snapshot = json.loads((cases_path.parent / case["snapshot"]).read_text(encoding="utf-8"))
        row = {"id": case["id"], "goal": case["goal"]}
        capture.response = None
        capture.responses = []
        try:
            decision, response = decide(capture, case["goal"], snapshot, case.get("values", []))
            actual = decision.as_dict()
            row.update(decision=actual, matched=all(actual.get(k) == v for k, v in case["expected"].items()),
                       usage=response.get("usage"), elapsed_seconds=response.get("elapsed_seconds"), model=response.get("model"))
        except BokkioError as error:
            row.update(matched=False, error=str(error))
        if capture.response:
            row.update({k: capture.response.get(k) for k in ("model", "source")})
            row["calls"] = capture.responses
            row["usage"] = {k: sum((r.get("usage") or {}).get(k, 0) or 0 for r in capture.responses)
                            for k in ("input_tokens", "output_tokens", "cost")}
            row["elapsed_seconds"] = sum(r["elapsed_seconds"] for r in capture.responses)
            row["answers"] = capture.responses[0].get("answers")
        row["model_calls"] = len(capture.responses)
        row["content_controls"] = case.get("content_controls")
        row["question_options"] = {k: len(q.get("criteria", {})) for k, q in (capture.questions or {}).items()}
        results.append(row)
        output.write_text(json.dumps({"provider": provider.source, "execution": False,
                                     "completed": len(results), "cases": len(cases), "results": results,
                                     "matched": sum(r["matched"] for r in results)}, indent=2), encoding="utf-8")
        print(json.dumps({"id": row["id"], "matched": row["matched"], "error": row.get("error")}), flush=True)
    print(json.dumps({"cases": len(results), "matched": sum(r["matched"] for r in results)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try: evaluate(args.cases, args.output)
    except BokkioError as error: parser.exit(1, f"bokkio: {error}\n")
