"""Real macOS fixture/process fault checks; no customer app or screen-lock claim."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import threading
import time
import uuid

from bokkio.runtime import Runtime
from bokkio.sdk import Client


def wait_for(probe, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = probe()
            if value:
                return value
        except (OSError, ValueError, KeyError, RuntimeError):
            pass
        time.sleep(.05)
    raise TimeoutError("Owned fixture/process did not reach expected state")


def live(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


class Fixture:
    def __init__(self, executable, folder, windows=1):
        folder.mkdir(parents=True)
        self.folder = folder
        self.state = folder / "window.json"
        self.business = folder / "business.json"
        self.control = folder / "control.json"
        env = {**os.environ, "BOKKIO_VISUAL_ICON": "1", "BOKKIO_VISUAL_WINDOWS": str(windows),
               "BOKKIO_VISUAL_STATE": str(self.state), "BOKKIO_VISUAL_RESULT": str(self.business),
               "BOKKIO_VISUAL_CONTROL": str(self.control)}
        self.process = subprocess.Popen([str(executable)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(lambda: self.state.exists() and self.business.exists())
        self.client = Client(Runtime(folder / "runtime", {"apps": [str(self.process.pid)], "paths": [str(folder)],
                                                          "write": True, "require_approval": False}))
        wait_for(self.client.open)

    def command(self, action, **args):
        token = uuid.uuid4().hex
        temporary = self.control.with_suffix(".tmp")
        temporary.write_text(json.dumps({"id": token, "action": action, **args}))
        temporary.replace(self.control)
        return wait_for(lambda: (data if (data := json.loads(self.state.read_text())).get("command_id") == token else None))

    def capture(self, exact=True, retry=True):
        state = json.loads(self.state.read_text())
        attempts = []
        for _ in range(3 if retry else 1):
            receipt = self.client.call("desktop.capture", {"app": str(self.process.pid), "window": "BokkioVisual",
                                                           **({"window_id": state["window_id"]} if exact else {})})
            attempts.append({k: receipt.get(k) for k in ("operation_id", "status", "error_code")})
            if receipt["status"] == "completed" or receipt.get("error_code") not in {"window_not_visible", "capture_timeout"}:
                break
            time.sleep(.1)
        return {**receipt, "read_attempts": attempts}

    def click(self, observation, operation=None):
        meta = observation["result"]["metadata"]
        state = json.loads(self.state.read_text())
        return self.client.call("desktop.pixel", {"app": str(self.process.pid), "window": "BokkioVisual",
                                                 "observation_id": observation["result"]["observation_id"],
                                                 "action": "click", "x": 165 * meta["width"] / state["client_width"],
                                                 "y": 201 * meta["height"] / state["client_height"]}, operation)

    def clicks(self):
        return json.loads(self.business.read_text())["clicks"]

    def close(self):
        if self.client.session_id:
            self.client.call("session.close")
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=5)


def job_checks(folder):
    folder.mkdir()
    client = Client(Runtime(folder / "state", {"paths": [str(folder)], "write": True,
                                              "trusted_host": True, "require_approval": False}))
    client.open()
    checks = []
    def tree(token, timeout=20):
        child = "import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('" + token + "-child').write_text(str(__import__('os').getpid()));time.sleep(30)"
        parent = "import subprocess,sys,time\nsubprocess.Popen([sys.executable,'-c'," + repr(child) + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(30)"
        args = {"code": parent, "cwd": str(folder), "timeout": timeout}
        queued = client.call("code.run", args, token)
        job = queued["result"]["job_id"]
        pid = wait_for(lambda: int((folder / (token + "-child")).read_text()))
        return args, job, pid
    try:
        args, job, pid = tree("cancel-tree")
        client.call("job.cancel", {"job_id": job})
        ended = client.wait_job(job, timeout=10)
        checks.append({"case": "cancel_descendant_ignoring_sigterm", "passed": ended["result"]["status"] == "cancelled" and not live(pid),
                       "job_status": ended["result"]["status"], "descendant_running": live(pid)})
        args, job, pid = tree("timeout-tree", timeout=2)
        ended = client.wait_job(job, timeout=10)
        checks.append({"case": "timeout_terminates_process_tree", "passed": ended["result"]["status"] == "timed_out" and not live(pid),
                       "job_status": ended["result"]["status"], "descendant_running": live(pid)})
        args, job, pid = tree("lost-worker")
        with client.runtime.store.connect() as db:
            row = wait_for(lambda: db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone())
            worker = row["worker_pid"]
        os.kill(worker, signal.SIGKILL)
        wait_for(lambda: not live(worker))
        ended = client.wait_job(job, timeout=10)
        duplicate = client.call("code.run", args, "lost-worker")
        events = client.runtime.store.query(operation_id="lost-worker")
        checks.append({"case": "worker_crash_unknown_never_replayed", "passed": ended["result"]["status"] == "completion_unknown"
                       and duplicate["status"] == "completion_unknown" and not live(pid)
                       and len([e for e in events if e["kind"] == "job.started"]) == 1,
                       "job_status": ended["result"]["status"], "duplicate_status": duplicate["status"],
                       "descendant_running": live(pid), "worker_lost_event": any(e["kind"] == "job.worker_lost" for e in events)})
        queued = client.call("code.run", {"code": "import sys;sys.stdout.write('x'*200000);sys.stderr.write('y'*90000)",
                                          "cwd": str(folder), "output_limit": 1024})
        ended = client.wait_job(queued["result"]["job_id"], timeout=10)
        result = ended["result"]["result"]
        checks.append({"case": "output_drained_and_bounded", "passed": ended["result"]["status"] == "completed"
                       and len(result["stdout"]) == len(result["stderr"]) == 1024
                       and result["output_bytes"] == {"stdout": 200000, "stderr": 90000},
                       "output_bytes": result.get("output_bytes"), "truncated": result.get("truncated")})
        args, job, pid = tree("session-close")
        client.call("session.close")
        from bokkio.executor import get
        ended = wait_for(lambda: (result if (result := get(client.runtime.store, job, client.session_id))["status"] not in {"running", "queued"} else None))
        checks.append({"case": "session_close_cancels_running_tree", "passed": ended["status"] == "cancelled" and not live(pid),
                       "job_status": ended["status"], "descendant_running": live(pid)})
    finally:
        client.call("session.close")
    return checks


def run(executable, output):
    if sys.platform != "darwin":
        raise RuntimeError("This fault matrix requires macOS")
    output.mkdir(parents=True, exist_ok=False)
    report = {"platform": platform.system(), "architecture": platform.machine(), "scope": "owned_fixture_physical_faults_and_real_processes",
              "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "working_tree_changes": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)), "checks": []}
    class Checks(list):
        def append(self, record):
            super().append(record)
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(json.dumps(record), flush=True)
    report["checks"] = Checks()
    fixture = Fixture(executable, output / "desktop")
    def rejected(case, observed, change):
        before = fixture.clicks()
        change()
        receipt = fixture.click(observed)
        after = fixture.clicks()
        report["checks"].append({"case": case, "passed": receipt["dispatched"] in (False, 0) and before == after,
                                 "dispatched": receipt["dispatched"], "error_code": receipt.get("error_code"),
                                 "status": receipt["status"], "business_clicks_unchanged": before == after})
    try:
        state = json.loads(fixture.state.read_text())
        report["displays"] = state["displays"]
        fixture.command("front")
        rejected("window_moved", fixture.capture(), lambda: fixture.command("move", x=260, y=260))
        fixture.command("front")
        rejected("window_resized", fixture.capture(), lambda: fixture.command("resize", width=680, height=400))
        fixture.command("resize", width=640, height=360)
        rejected("pixels_changed", fixture.capture(), lambda: fixture.command("repaint"))
        other = None
        observed = fixture.capture()
        try:
            other = Fixture(executable, output / "competitor")
            other.command("front")
            rejected("other_process_takes_foreground", observed, lambda: None)
            rejected("nonforeground_fresh_pixels", fixture.capture(), lambda: None)
        finally:
            if other:
                other.close()
        fixture.command("front")
        observed = fixture.capture()
        rejected("window_rebuilt_same_title", observed, lambda: fixture.command("rebuild"))
        fixture.command("front")
        observed = fixture.capture()
        before = fixture.clicks()
        receipt = fixture.click(observed)
        if receipt["dispatched"] is True:
            wait_for(lambda: fixture.clicks() == before + 1)
        report["checks"].append({"case": "fresh_window_after_rebuild", "passed": receipt["dispatched"] is True and fixture.clicks() == before + 1})
        observed = fixture.capture()
        # Real wall-clock expiry, no injected clock or altered persisted observation.
        time.sleep(15.1)
        rejected("real_observation_expired", observed, lambda: None)
        for display in state["displays"]:
            fixture.command("display", index=display["index"])
            fixture.command("front")
            observed = fixture.capture()
            before = fixture.clicks()
            receipt = fixture.click(observed)
            if receipt["dispatched"] is True:
                wait_for(lambda: fixture.clicks() == before + 1)
            meta = observed["result"]["metadata"]
            report["checks"].append({"case": "physical_display_coordinate_mapping", "display_index": display["index"],
                                     "scale": meta["point_pixel_scale"], "passed": receipt["dispatched"] is True and fixture.clicks() == before + 1,
                                     "dispatched": receipt["dispatched"], "error_code": receipt.get("error_code")})
        observed = fixture.capture()
        before = fixture.clicks()
        from bokkio.desktop_input import desktop_lock
        with desktop_lock():
            result = []
            operation = uuid.uuid4().hex
            thread = threading.Thread(target=lambda: result.append(fixture.click(observed, operation)))
            thread.start()
            wait_for(lambda: any(e["kind"] == "execution.intent" and e["data"].get("tool") == "desktop.pixel"
                                for e in fixture.client.runtime.store.query(operation_id=operation)))
            fixture.client.call("session.close")
        thread.join(timeout=10)
        report["checks"].append({"case": "session_closed_while_waiting_input_lock", "passed": bool(result) and result[0]["dispatched"] in (False, 0)
                                 and result[0].get("error_code") == "dispatch_scope_changed" and fixture.clicks() == before,
                                 "error_code": result[0].get("error_code") if result else "thread_timeout"})
    finally:
        fixture.close()
    ambiguous = Fixture(executable, output / "ambiguous", windows=2)
    try:
        receipt = ambiguous.capture(exact=False)
        report["checks"].append({"case": "same_title_ambiguous_window", "passed": receipt.get("error_code") == "window_ambiguous"
                                 and receipt["dispatched"] in (False, 0), "error_code": receipt.get("error_code")})
        observed = ambiguous.capture()
        ambiguous.process.terminate()
        ambiguous.process.wait(timeout=5)
        receipt = ambiguous.click(observed)
        report["checks"].append({"case": "terminated_process", "passed": receipt["dispatched"] in (False, 0), "status": receipt["status"]})
    finally:
        ambiguous.close()
    minimized = Fixture(executable, output / "minimized")
    try:
        minimized.command("minimize")
        wait_for(lambda: (data if (data := json.loads(minimized.state.read_text())).get("minimized") and not data.get("on_screen") else None))
        receipt = minimized.capture(retry=False)
        report["checks"].append({"case": "minimized_window_capture_rejected", "passed": receipt.get("error_code") == "window_not_visible"
                                 and receipt["dispatched"] in (False, 0), "error_code": receipt.get("error_code")})
    finally:
        minimized.close()
    report["checks"] += job_checks(output / "jobs")
    report["not_tested"] = ["physical_screen_lock_and_unlock", "customer_application", "customer_harness"]
    if len(report["displays"]) < 2:
        report["not_tested"].append("second_physical_display_or_different_scale")
    report["passed"] = sum(c["passed"] for c in report["checks"])
    report["total"] = len(report["checks"])
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.fixture.resolve(), args.output.resolve())
    print(json.dumps({"passed": report["passed"], "total": report["total"], "report": str(args.output / "report.json"), "not_tested": report["not_tested"]}))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
