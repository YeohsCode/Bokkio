"""Real native P5 checks: large-tree planning, recovery, resume and restart."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from bokkio.agent import DesktopAgent, file_control, replace_checkpoint
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify_extended_order(trace):
    """Check the requested milestones against executed native action results."""
    expected = ["input", "submit", "137", "document", "619", "mode", "997"]
    observed = []
    for event in trace["events"]:
        if event["kind"] != "action": continue
        result = event["result"]
        before, after = result["before"], result.get("after") or {}
        name, role, action = before["name"], before["role"], result["action"]
        if name == "Search" and action in {"set_value", "type"} and after.get("value") == "P5 extended":
            observed.append("input")
        elif name == "Submit" and action == "click": observed.append("submit")
        elif name in {"Sample 137", "Sample 619", "Sample 997"} and action == "click":
            observed.append(name.split()[1])
        elif role == "text_area" and after.get("value") == "P5 extended document": observed.append("document")
        elif ((name == "Mode" and after.get("value") == "Second" and action == "set_value")
              or (name == "Second" and action == "select")):
            observed.append("mode")
    return observed == expected, observed


def verify_windows_checkpoint_lock(output):
    """Hold a real Windows handle that briefly denies replacement of our file."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    target, source = output / "lock-target.txt", output / "lock-source.txt"
    target.write_text("old", encoding="utf-8"); source.write_text("new", encoding="utf-8")
    handle = kernel.CreateFileW(str(target), 0x80000000, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    def release():
        time.sleep(0.15); kernel.CloseHandle(handle)
    thread = threading.Thread(target=release)
    thread.start(); started = time.perf_counter()
    try:
        replace_checkpoint(source, target)
    finally:
        thread.join(timeout=5)
    elapsed = time.perf_counter() - started
    result = {"passed": target.read_text(encoding="utf-8") == "new" and not source.exists() and elapsed >= 0.15,
              "elapsed_seconds": round(elapsed, 3), "lock_hold_seconds": 0.15}
    target.unlink()
    return result


def run(scale_fixture, hard_fixture, output, *, extended_only=False):
    import xa11y
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_lock = verify_windows_checkpoint_lock(output)
    (output / "checkpoint-lock.json").write_text(json.dumps(checkpoint_lock, indent=2), encoding="utf-8")
    if not checkpoint_lock["passed"]: raise RuntimeError("Native Windows checkpoint lock verification failed")
    backend = Xa11yBackend()
    planner, provider = OpenRouterPlanner(), JevProvider()
    main = "bokkio-interactions-fixture"
    owned, rows = [], []

    def start(path, *args):
        process = subprocess.Popen([str(path.resolve()), *args])
        owned.append(process)
        xa11y.App.by_pid(process.pid, timeout=20)
        time.sleep(1)
        return process

    def nodes(app):
        return flatten(backend.snapshot(app)["windows"])

    def reset():
        backend.perform(main, "set_value", role="text_field", name="Search", value="")
        backend.perform(main, "click", role="button", name="Submit")

    def save(name, trace, checks, **details):
        row = {"case": name, "status": trace["status"], "actions": trace["actions"],
               "replans": trace["replans"], "independent_checks": checks,
               "passed": trace["status"] == "completed" and all(checks), **details}
        rows.append(row)
        (output / "summary.json").write_text(json.dumps({"tasks": 1 if extended_only else 4, "attempted": len(rows),
            "passed": sum(r["passed"] for r in rows), "results": rows}, indent=2), encoding="utf-8")
        print(json.dumps(row), flush=True)

    try:
        scale = start(scale_fixture, "1000")
        note = start(Path(os.environ["SystemRoot"]) / "System32/notepad.exe")
        scale_app, note_app = str(scale.pid), str(note.pid)
        reset()
        backend.perform(main, "expand", role="combo_box", name="Mode")
        backend.perform(main, "select", role="list_item", name="First")
        backend.perform(main, "collapse", role="combo_box", name="Mode")
        activated = []
        class ObservedBackend:
            def snapshot(self, *args): return backend.snapshot(*args)
            def windows(self, *args): return backend.windows(*args)
            def perform(self, app, action, **kwargs):
                result = backend.perform(app, action, **kwargs)
                if app == scale_app and action == "click":
                    activated.extend(n["name"] for n in nodes(app)
                                     if n["role"] == "static_text" and (n["name"] or "").startswith("Activated Sample "))
                return result
        goal = ('In bokkio-interactions-fixture set Search to "P5 extended" and click Submit '
                'so its status reads "Submitted: P5 extended". Then in Bokkio scale 1000 '
                'click Sample 137 so its status reads "Activated Sample 137". Then in Notepad '
                'replace the document text with "P5 extended document". Then in Bokkio scale 1000 '
                'click Sample 619 so its status reads "Activated Sample 619". Then in '
                'bokkio-interactions-fixture select Second in Mode. Finally in Bokkio scale 1000 '
                'click Sample 997 so its status reads "Activated Sample 997". Keep this order.')
        trace = DesktopAgent(ObservedBackend(), planner, provider, max_actions=20, max_replans=2).run(
            goal, [main, scale_app, note_app], output / "extended.json")
        observations = next(e["observations"] for e in trace["events"] if e["kind"] == "planner_observations")
        visible_targets = {n["name"] for n in observations[scale_app]["nodes"]}
        ordered, milestones = verify_extended_order(trace)
        checks = [any(n["name"] == "Submitted: P5 extended" for n in nodes(main)),
                  any(n["role"] == "combo_box" and n["name"] == "Mode" and n["value"] == "Second" for n in nodes(main)),
                  any(n["role"] == "text_area" and n["value"] == "P5 extended document" for n in nodes(note_app)),
                  activated == ["Activated Sample 137", "Activated Sample 619", "Activated Sample 997"],
                  {"Sample 137", "Sample 619", "Sample 997"} <= visible_targets, ordered]
        save("extended_large_tree", trace, checks, activated=activated,
             action_milestones=milestones,
             planner_scope=observations[scale_app]["observation_scope"])
        if extended_only: return rows[0]["passed"]

        reset()
        class RepeatedChanges:
            injected = 0
            def ask(self, state, questions):
                response = provider.ask(state, questions)
                if self.injected < 2:
                    self.injected += 1
                    backend.perform(main, "set_value", role="text_field", name="Search",
                                    value=f"Concurrent change {self.injected}")
                return response
        changing = RepeatedChanges()
        trace = DesktopAgent(backend, planner, changing, max_actions=10, max_replans=2).run(
            'Set Search to "P5 recovered twice" and click Submit so its status is "Submitted: P5 recovered twice".',
            [main], output / "repeated-recovery.json")
        stale_count = sum(e["kind"] == "error" and "Snapshot changed" in e.get("error", "") for e in trace["events"])
        save("repeated_recovery", trace, [stale_count == 2, trace["replans"] == 2,
             any(n["name"] == "Search" and n["value"] == "P5 recovered twice" for n in nodes(main)),
             any(n["name"] == "Submitted: P5 recovered twice" for n in nodes(main))], stale_rejections=stale_count)

        reset()
        control = output / "control.json"
        class Pausing:
            paused = False
            def ask(self, state, questions):
                response = provider.ask(state, questions)
                if not self.paused:
                    control.write_text('{"action":"pause"}', encoding="utf-8")
                    self.paused = True
                return response
        goal = 'Set Search to "P5 resumed" and click Submit so its status is "Submitted: P5 resumed".'
        agent = DesktopAgent(backend, planner, Pausing(), max_actions=8, max_replans=1, control=file_control(control))
        checkpoint = output / "resume.json"
        paused = agent.run(goal, [main], checkpoint)
        (output / "paused.json").write_text(json.dumps(paused, indent=2), encoding="utf-8")
        paused_checks = [paused["status"] == "paused", paused["actions"] == 0,
                         any(n["name"] == "Search" and n["value"] == "" for n in nodes(main))]
        control.write_text('{"action":null}', encoding="utf-8")
        resumed = agent.run(goal, [main], checkpoint, resume=checkpoint)
        save("pause_resume", resumed, paused_checks + [
            any(n["name"] == "Submitted: P5 resumed" for n in nodes(main))], paused_actions=paused["actions"])

        # Use a unique application name so a restart can remain in the explicit
        # allowlist. Never close an application owned by another task or user.
        hard_name = "bokkio-jev-hard-fixture"
        if any(a["name"] == hard_name for a in backend.apps()):
            raise RuntimeError("Restart fixture name is already in use; no existing process was closed")
        hard = [start(hard_fixture)]
        original_pid = hard[0].pid
        class Restarting:
            restarted = False
            def ask(self, state, questions):
                response = provider.ask(state, questions)
                if not self.restarted:
                    hard[0].terminate(); hard[0].wait(timeout=10)
                    hard[0] = start(hard_fixture)
                    self.restarted = True
                return response
        trace = DesktopAgent(backend, planner, Restarting(), max_actions=6, max_replans=1).run(
            'Click Action in Right pane so the status reads "Clicked Right pane".',
            [hard_name], output / "restart.json")
        rejected = any(e["kind"] == "error" and "Snapshot changed" in e.get("error", "") for e in trace["events"])
        save("application_restart", trace, [hard[0].pid != original_pid, rejected,
             any(n["name"] == "Clicked Right pane" for n in nodes(hard_name))],
             original_pid=original_pid, restarted_pid=hard[0].pid, stale_rejected=rejected)
        return len(rows) == 4 and all(r["passed"] for r in rows)
    finally:
        for process in owned:
            if process.poll() is None:
                process.terminate(); process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale-fixture", type=Path, required=True)
    parser.add_argument("--hard-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extended-only", action="store_true")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.scale_fixture, args.hard_fixture, args.output, extended_only=args.extended_only) else 1)
