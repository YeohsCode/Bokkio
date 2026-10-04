"""Execute independent targets in a real 1,000-control native tree."""
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


def verify(fixture, output):
    import xa11y
    process = subprocess.Popen([str(fixture.resolve()), "1000"])
    backend = Xa11yBackend(); provider = JevProvider(); rows = []
    try:
        xa11y.App.by_pid(process.pid, timeout=15); time.sleep(1)
        for target in (137, 619, 997):
            snapshot = backend.snapshot(str(process.pid))
            node = next(n for n in flatten(snapshot["windows"]) if n["role"] == "button" and n["name"] == f"Sample {target}")
            row = {"target": target, "passed": False, "snapshot": snapshot, "expected_ref": node["ref"]}
            try:
                decision, response = decide(provider, f"Click Sample {target}", snapshot)
                row.update(decision=decision.as_dict(), model=response)
                if decision.action != "click" or decision.ref != node["ref"]: raise BokkioError("Wrong accepted action/ref")
                row["result"] = execute_decision(backend, str(process.pid), decision)
                fresh = backend.snapshot(str(process.pid))
                row["passed"] = any(n["name"] == f"Activated Sample {target}" for n in flatten(fresh["windows"]))
            except BokkioError as error: row["error"] = str(error)
            rows.append(row); output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({"content_controls": 1000, "passed": sum(r["passed"] for r in rows), "results": rows}, indent=2), encoding="utf-8")
            print(json.dumps({"target": target, "passed": row["passed"], "error": row.get("error")}), flush=True)
    finally:
        process.terminate(); process.wait(timeout=10)
    return all(r["passed"] for r in rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.fixture, args.output) else 1)
