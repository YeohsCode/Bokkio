"""Real pixel click + Unicode input, independently scored from owned fixture JSON."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from bokkio.runtime import Runtime
from bokkio.sdk import Client


def run(fixture, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {"platform": platform.system(), "architecture": platform.machine(), "scope": "owned_icon_and_unicode_without_ocr", "rounds": []}
    for index in range(3):
        folder = output / str(index + 1)
        folder.mkdir()
        state_path = folder / "business.json"
        if sys.platform == "darwin":
            env = {**os.environ, "BOKKIO_VISUAL_ICON": "1", "BOKKIO_VISUAL_RESULT": str(state_path), "BOKKIO_VISUAL_STATE": str(folder / "window.json")}
            process = subprocess.Popen([str(fixture)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            window_state = folder / "window.json"
            title, x, input_y, button_y = "BokkioVisual", 165, 125, 201
        else:
            process = subprocess.Popen([str(fixture), str(state_path), "icon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            window_state = state_path
            title, x, input_y, button_y = "Bokkio visual capture fixture", 165, 130, 215
        client = Client(Runtime(folder / "state", {"apps": [str(process.pid)], "paths": [str(folder)], "write": True, "require_approval": False}))
        try:
            deadline = time.monotonic() + 10
            while not window_state.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Visual fixture exited during startup")
                time.sleep(.1)
            state = json.loads(window_state.read_text())
            for attempt in range(40):
                try:
                    client.open()
                    break
                except RuntimeError:
                    if attempt == 39:
                        raise
                    time.sleep(.1)
            window_id = state.get("window_id", state.get("hwnd"))
            def input(action, y, value=None):
                attempts = []
                for attempt in range(2):
                    observed = client.call("desktop.capture", {"app": str(process.pid), "window_id": window_id, "window": title})
                    if observed["status"] != "completed":
                        raise RuntimeError(observed)
                    meta = observed["result"]["metadata"]
                    # Fixture content is 640x360. Pixel->screen mapping belongs to Runtime.
                    args = {"app": str(process.pid), "window": title, "observation_id": observed["result"]["observation_id"],
                            "action": action, "x": x * meta["width"] / 640, "y": y * meta["height"] / 360}
                    if value is not None:
                        args["value"] = value
                    response = client.call("desktop.pixel", args)
                    attempts.append({k: response.get(k) for k in ("operation_id", "status", "dispatched", "error_code")})
                    if not (response.get("dispatched") in (False, 0) and response.get("error_code") in {"capture_changed", "capture_stale"}):
                        break
                return {**response, "attempts": attempts}
            literal = "视觉CODE" + str(index + 1)
            typed = input("type", input_y, literal)
            clicked = input("click", button_y)
            deadline = time.monotonic() + 2
            while True:
                business = json.loads(state_path.read_text())
                if business.get("input") == literal and business.get("clicks") == 1 or time.monotonic() >= deadline:
                    break
                time.sleep(.05)
            report["rounds"].append({"round": index + 1, "passed": business.get("input") == literal and business.get("clicks") == 1,
                                     "input_matches": business.get("input") == literal, "clicks": business.get("clicks"),
                                     "type_status": typed["status"], "click_status": clicked["status"],
                                     "operation_ids": [typed["operation_id"], clicked["operation_id"]],
                                     "attempts": {"type": typed["attempts"], "click": clicked["attempts"]},
                                     "errors": [r.get("error") for r in (typed, clicked) if r.get("error")]})
        except Exception as error:
            report["rounds"].append({"round": index + 1, "passed": False, "error_type": type(error).__name__, "error": str(error)})
        finally:
            if client.session_id:
                client.call("session.close")
            process.terminate()
            process.wait(timeout=5)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True, help="Owned native painted fixture executable")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.fixture.resolve(), args.output.resolve())
    passed = sum(r["passed"] for r in report["rounds"])
    print(json.dumps({"passed": passed, "total": 3, "report": str(args.output.resolve() / "report.json")}, ensure_ascii=False))
    raise SystemExit(0 if passed == 3 else 1)
