"""Measure live UIA reads; report content counts separately from window chrome."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import sysconfig
import time

from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def benchmark(executable: Path, output: Path, runs: int):
    if sys.platform != "win32":
        raise SystemExit("Live UIA benchmarks require an interactive Windows host")
    if runs < 1:
        raise SystemExit("runs must be positive")
    import xa11y

    backend = Xa11yBackend()
    results = []
    for size in (50, 100, 300, 1000):
        process = subprocess.Popen([str(executable.resolve()), str(size)])
        try:
            xa11y.App.by_pid(process.pid, timeout=15)
            app = str(process.pid)
            # Wait for the fixture's full content tree, without counting startup.
            deadline = time.monotonic() + 30
            while True:
                snapshot = backend.snapshot(app)
                nodes = flatten(snapshot["windows"])
                samples = [n for n in nodes if n["role"] == "button"
                           and (n["name"] or "").startswith("Sample ")]
                if len(samples) == size:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Expected {size} sample controls, found {len(samples)}")
                time.sleep(0.1)
            timings = {"snapshot": [], "find": []}
            for _ in range(runs):
                started = time.perf_counter()
                fresh = backend.snapshot(app)
                timings["snapshot"].append(time.perf_counter() - started)
                assert len(flatten(fresh["windows"])) == len(nodes)
                started = time.perf_counter()
                matches = backend.find(app, "button", f"Sample {size}")
                timings["find"].append(time.perf_counter() - started)
                assert len(matches) == 1
            row = {"content_controls": size, "total_tree_nodes": len(nodes), "runs": runs,
                   "seconds": timings,
                   "median_seconds": {k: statistics.median(v) for k, v in timings.items()}}
            results.append(row)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps({"host": platform.platform(), "host_arch": platform.machine(),
                                         "python_platform": sysconfig.get_platform(),
                                         "includes_cli_startup": False, "results": results}, indent=2), encoding="utf-8")
            print(json.dumps(row), flush=True)
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    benchmark(args.fixture, args.output, args.runs)
