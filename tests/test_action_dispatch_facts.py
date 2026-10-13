"""Exercise actual Xa11yBackend preflight through the enterprise Runtime."""
import pytest

from bokkio.runtime import Runtime
from bokkio.sdk import Client
from test_cli import backend_with_button


@pytest.mark.parametrize("refusal", ["disabled", "window-disabled", "unsupported"])
def test_backend_refusal_is_zero_dispatch_not_unknown(tmp_path, monkeypatch, refusal):
    backend, window, button = backend_with_button()
    if refusal == "disabled":button.enabled = False
    if refusal == "window-disabled":window.enabled = False
    if refusal == "unsupported":button.actions = []
    backend.apps = lambda: [{"pid": 100, "name": "TextEdit"}]
    # No OS input is dispatched by this synthetic provider. Keep all real backend checks.
    monkeypatch.setattr("bokkio.desktop_input.require_input_session", lambda: None)
    client = Client(Runtime(tmp_path, {"apps": ["TextEdit"], "write": True, "require_approval": False}, backend, lambda pid: "birth"))
    client.open()
    observation = client.call("desktop.observe", {"app": "TextEdit"})["result"]
    target = next(n for n in observation["nodes"] if n["name"] == "Save")
    args = {"app": "TextEdit", "observation_id": observation["observation_id"], "ref": target["ref"], "action": "click"}
    result = client.call("desktop.act", args, "refusal")
    assert result["status"] == "failed" and result["dispatched"] is False, result
    assert result["error_code"] in {"target_disabled", "window_disabled", "action_unavailable"}
    assert button.value is None
    assert client.call("desktop.act", args, "refusal") == result


def test_native_transport_failure_after_side_effect_stays_unknown(tmp_path, monkeypatch):
    backend, _, button = backend_with_button()
    backend.apps = lambda: [{"pid": 100, "name": "TextEdit"}]
    monkeypatch.setattr("bokkio.desktop_input.require_input_session", lambda: None)
    def press():
        button.value = "changed"
        raise OSError("Lost provider reply")
    button.press = press
    client = Client(Runtime(tmp_path, {"apps": ["TextEdit"], "write": True, "require_approval": False}, backend, lambda pid: "birth"))
    client.open()
    observation = client.call("desktop.observe", {"app": "TextEdit"})["result"]
    target = next(n for n in observation["nodes"] if n["name"] == "Save")
    args = {"app": "TextEdit", "observation_id": observation["observation_id"], "ref": target["ref"], "action": "click"}
    result = client.call("desktop.act", args, "lost")
    assert result["status"] == "completion_unknown" and button.value == "changed"
    assert client.call("desktop.act", args, "lost") == result
