"""Exercise disposable native WinForms controls and a newly created Notepad."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import time
from bokkio.model import BokkioActionError, BokkioLookupError
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    backend = Xa11yBackend()
    app = "bokkio-interactions-fixture"
    trace = []

    def record(name, result):
        trace.append({"test": name, "result": result})
        (output / "interactions.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    def act(action, role, name, **args):
        result = backend.perform(app, action, role=role, name=name, **args)
        record(f"{action}:{name}", result)
        return result

    first = backend.snapshot(app)
    (output / "interaction-fixture.json").write_text(json.dumps(first, indent=2), encoding="utf-8")
    for iteration in range(3):
        assert act("set_value", "text_field", "Search", value="seed")["verification"] == "confirmed"
        assert act("set_value", "text_field", "Search", value="")["verification"] == "confirmed"
        assert act("focus", "text_field", "Search")["verification"] == "confirmed"
        assert act("type", "text_field", "Search", value="Bokkio native", expected_value="Bokkio native")["verification"] == "confirmed"
        act("click", "button", "Submit")
        assert any(n["value"] == "Submitted: Bokkio native" or n["name"] == "Submitted: Bokkio native" for n in flatten(backend.snapshot(app)["windows"]))
    try:
        act("set_value", "text_field", "Read only", value="changed")
        raise AssertionError("Read-only write executed")
    except BokkioActionError as error:
        record("readonly-rejected", {"error": str(error)})

    for direction in ["right", "left", "down", "up"] * 3:
        result = act("scroll", "group", "Scroll content", direction=direction, amount=0.25)
        assert result["verification"] == "confirmed", result["scroll"]
    boundary = act("scroll", "group", "Scroll content", direction="up")
    assert boundary["verification"] == "unconfirmed" and boundary["scroll"]["reason"] == "at_boundary"

    assert act("expand", "tree_item", "Parent")["verification"] == "confirmed"
    assert act("collapse", "tree_item", "Parent")["verification"] == "confirmed"
    assert act("expand", "combo_box", "Mode")["verification"] == "confirmed"
    assert act("select", "list_item", "Second")["verification"] == "confirmed"

    peers = backend.find(app, "button", "Duplicate")
    act("click", "button", "Reorder")
    reordered = backend.find(app, "button", "Duplicate")
    assert {n["ref"] for n in reordered} == {n["ref"] for n in peers}
    result = backend.perform(app, "click", ref=peers[0]["ref"])
    record("duplicate-ref-after-reorder", result)
    # Rebuild disposes the first control in current provider order.
    before = {n["ref"] for n in reordered}
    act("click", "button", "Rebuild")
    after = {n["ref"] for n in backend.find(app, "button", "Duplicate")}
    removed = before - after
    assert len(removed) == 1 and len(after - before) == 1, (before, after)
    try:
        backend.perform(app, "click", ref=removed.pop())
        raise AssertionError("Rebuilt target accepted an old ref")
    except BokkioLookupError as error:
        assert error.code == "stale_ref"
        record("rebuild-stale-ref", error.as_dict())

    windows = backend.windows("ApplicationFrameHost")
    record("settings-top-level-windows", windows)
    assert len(windows) == 1, len(windows)

    # Win32 owner-data ListView is virtual internally, but UIA may expose all rows.
    virtual_before = backend.find(app, "list", "Virtual rows")[0]
    rows_before = {n["ref"] for n in flatten([virtual_before]) if n["role"] == "list_item"}
    virtual_scroll = act("scroll", "list", "Virtual rows", direction="down", amount=0.5)
    assert virtual_scroll["verification"] == "confirmed"
    virtual_after = backend.find(app, "list", "Virtual rows")[0]
    rows_after = {n["ref"] for n in flatten([virtual_after]) if n["role"] == "list_item"}
    record("owner-data-list-coverage", {"native_rows": 1000, "exposed_before": len(rows_before),
                                       "exposed_after": len(rows_after), "refs_changed": len(rows_before ^ rows_after),
                                       "provider_exposes_partial_tree": len(rows_before) < 1000})
    assert act("scroll", "list", "Virtual rows", direction="up", amount=0.5)["verification"] == "confirmed"

    # Own this process, so no existing user document is edited.
    process = subprocess.Popen(["notepad.exe"])
    try:
        for _ in range(30):
            try:
                editors = backend.find(str(process.pid), "text_area", "Text Editor")
                if editors: break
            except Exception: pass
            time.sleep(0.2)
        else: raise AssertionError("New Notepad editor unavailable")
        for _ in range(3):
            for action, value, expected in [("set_value", "seed", None), ("set_value", "", None), ("type", "Bokkio Notepad", "Bokkio Notepad")]:
                result = backend.perform(str(process.pid), action, role="text_area", name="Text Editor", value=value, expected_value=expected)
                record(f"notepad:{action}", result)
                assert result["verification"] == "confirmed", result.get("postcondition")
        backend.perform(str(process.pid), "set_value", role="text_area", name="Text Editor", value="")
    finally:
        process.terminate()
    summary = {"passed": True, "recorded_checks": len(trace), "input_rounds": 3, "scroll_rounds": 3, "notepad_rounds": 3}
    (output / "interactions-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
