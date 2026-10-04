import pytest

from bokkio.cli import build_parser, execute
from bokkio.model import BokkioActionError, BokkioLookupError
from bokkio.selector import choose
from bokkio.xa11y_backend import Xa11yBackend

from test_cli import App, Element, FakeXa11y, backend_with_button


def test_actions_read_back_state_and_keep_stable_ref():
    backend, _, button = backend_with_button()
    button.actions = ["press", "set_value", "type_text", "AXUnknown"]
    normalized = backend.find("TextEdit", "button", "Save")[0]
    assert normalized["actions"] == ["click", "set_value", "type"]
    assert normalized["platform_data"]["actions"] == button.actions
    ref = backend.find("TextEdit", "button", "Save")[0]["ref"]

    result = backend.perform("TextEdit", "click", ref=ref)
    assert result["target_ref"] == ref
    assert result["after"]["value"] == "pressed"
    assert result["tree_changed"]
    assert button.value == "pressed"

    result = backend.perform("TextEdit", "set_value", ref=ref, value="hello")
    assert result["verification"] == "confirmed"
    assert result["after"]["value"] == "hello"

    result = backend.perform("TextEdit", "type", role="button", name="Save", value=" world")
    assert result["after"]["value"] == "hello world"


def test_selector_rejects_stale_ambiguous_and_mismatched_targets():
    backend, _, _ = backend_with_button()
    tree = backend.snapshot("TextEdit")["windows"]
    with pytest.raises(BokkioLookupError) as stale:
        choose(tree, ref="missing")
    assert stale.value.as_dict()["error"] == "stale_ref"
    assert stale.value.as_dict()["candidates"]

    duplicate = {"ref": "two", "role": "button", "name": "Save", "parent": "parent", "children": []}
    tree[0]["children"][0]["children"].append(duplicate)
    with pytest.raises(BokkioLookupError) as ambiguous:
        choose(tree, role="button", name="Save")
    assert ambiguous.value.code == "ambiguous_element"
    with pytest.raises(BokkioLookupError) as mismatch:
        choose(tree, ref="two", name="Cancel")
    assert mismatch.value.code == "selector_mismatch"


def test_duplicate_siblings_receive_distinct_refs_and_parent_disambiguates():
    first = Element("button", "Save")
    second = Element("button", "Save")
    window = Element("window", "Untitled", children=[first, second])
    module = FakeXa11y()
    module.current = App(window)
    backend = Xa11yBackend(module)
    backend._resolve_app = lambda app: module.current
    nodes = backend.find("TextEdit", "button", "Save")
    assert len({node["ref"] for node in nodes}) == 2
    with pytest.raises(BokkioLookupError) as ambiguous:
        backend.perform("TextEdit", "click", role="button", name="Save")
    assert ambiguous.value.code == "ambiguous_element"
    backend.perform("TextEdit", "click", ref=nodes[1]["ref"])
    assert first.value is None
    assert second.value == "pressed"


def test_missing_value_and_disabled_target_do_not_execute():
    backend, _, button = backend_with_button()
    with pytest.raises(BokkioActionError, match="requires a value"):
        backend.perform("TextEdit", "set_value", role="button", name="Save")
    button.enabled = False
    with pytest.raises(BokkioActionError, match="disabled"):
        backend.perform("TextEdit", "click", role="button", name="Save")
    assert button.value is None
    button.enabled = True
    button.actions = []
    with pytest.raises(BokkioActionError, match="not advertised"):
        backend.perform("TextEdit", "click", role="button", name="Save")
    assert button.value is None


def test_cli_action_dispatch_and_repeatable_value_write():
    backend, _, button = backend_with_button()
    button.actions.append("set_value")
    args = build_parser().parse_args([
        "act", "--app", "TextEdit", "--action", "set_value",
        "--role", "button", "--name", "Save", "--value", "repeatable",
    ])
    refs = []
    for _ in range(3):
        result = execute(args, backend)
        assert result["verification"] == "confirmed"
        refs.append(result["target_ref"])
    assert len(set(refs)) == 1
    assert button.value == "repeatable"


def test_shared_schema_can_label_windows_provider_data():
    backend, _, _ = backend_with_button()
    backend._platform = "windows"
    node = backend.snapshot("TextEdit")["windows"][0]
    assert node["platform"] == "windows"
    assert node["children"][0]["platform"] == "windows"


def test_macos_scroll_noop_is_not_advertised_or_executed():
    backend, _, button = backend_with_button()
    backend._platform = "macos"
    button.actions = ["scroll_into_view"]
    assert backend.find("TextEdit", "button", "Save")[0]["actions"] == []
    with pytest.raises(BokkioActionError, match="requires --direction"):
        backend.perform("TextEdit", "scroll", role="button", name="Save")


def test_type_expected_value_checks_result_including_mismatch():
    backend, _, button = backend_with_button()
    button.actions.append("type_text")
    confirmed = backend.perform("TextEdit", "type", role="button", name="Save", value="text", expected_value="text")
    assert confirmed["verification"] == "confirmed"
    mismatch = backend.perform("TextEdit", "type", role="button", name="Save", value="!", expected_value="wrong")
    assert mismatch["verification"] == "unconfirmed"
    assert mismatch["postcondition"]["actual"] == "text!"


def test_checked_action_target_disappearing_is_unconfirmed():
    backend, _, button = backend_with_button()
    button.actions.append("set_value")
    def rename(value):
        button.name = "Changed"
        button.value = value
    button.set_value = rename
    result = backend.perform("TextEdit", "set_value", role="button", name="Save", value="x")
    assert result["after"] is None
    assert result["verification"] == "unconfirmed"
    assert result["postcondition"]["reason"] == "target_missing"


def test_radio_selection_uses_press_and_checks_checked_state():
    backend, _, radio = backend_with_button()
    radio.role = "radio_button"
    radio.checked = "off"
    def press():
        radio.checked = "on"
    def unsupported_select():
        raise AssertionError("AXSelected does not select this radio button")
    radio.press = press
    radio.select = unsupported_select
    assert "select" in backend.find("TextEdit", "radio_button", "Save")[0]["actions"]
    result = backend.perform("TextEdit", "select", role="radio_button", name="Save")
    assert result["verification"] == "confirmed"
    assert result["after"]["state"]["checked"] == "on"
