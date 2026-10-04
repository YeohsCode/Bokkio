"""Save native Windows scale trees and labeled offline Jev development cases."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def export(executable, output):
    import xa11y
    backend = Xa11yBackend(); cases = []; output.mkdir(parents=True, exist_ok=True)
    for count in (50, 100, 300, 1000):
        process = subprocess.Popen([str(executable.resolve()), str(count)])
        try:
            xa11y.App.by_pid(process.pid, timeout=15)
            deadline = time.monotonic() + 20
            while True:
                snapshot = backend.snapshot(str(process.pid))
                samples = {n["name"]: n for n in flatten(snapshot["windows"]) if n["role"] == "button" and (n["name"] or "").startswith("Sample ")}
                if len(samples) == count: break
                if time.monotonic() >= deadline: raise RuntimeError("Scale fixture did not populate")
                time.sleep(0.1)
            name = f"scale-{count}.json"
            (output / name).write_text(json.dumps(snapshot, separators=(',', ':')), encoding="utf-8")
            for target in (1, count // 2, count):
                node = samples[f"Sample {target}"]
                cases.append({"id": f"scale-{count}-{target}", "content_controls": count, "goal": f"Click Sample {target}",
                              "snapshot": name, "values": [], "expected": {"action": "click", "ref": node["ref"]}})
        finally:
            process.terminate(); process.wait(timeout=10)
    (output / "scale-cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(cases), "scales": [50, 100, 300, 1000]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); export(args.fixture, args.output)
