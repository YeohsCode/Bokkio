import json
from types import SimpleNamespace

from bokkio.cli import build_parser, execute, render_tree
from bokkio.xa11y_backend import Xa11yBackend


class Rect:
    def __init__(self):
        self.x = 1
        self.y = 2
        self.width = 30
        self.height = 40


class Element:
    def __init__(self, role, name=None, value=None, children=None):
        self.role = role
        self.name = name
        self.value = value
        self.children_values = children or []
        self.parent_value = None
        self.description = None
        self.actions = ["press"] if role == "button" else []
        self.stable_id = None
        self.numeric_value = None
        self.bounds = Rect()
        self.raw = {"AXRole": role}
        self.enabled = True
        self.visible = True
        self.focused = False
        self.active = False
        self.selected = False
        self.editable = False
        self.focusable = False
        self.checked = None
        self.expanded = None
        self.minimized = False
        self.maximized = None
        self.fullscreen = None
        for child in self.children_values:
            child.parent_value = self

    def press(self):
        self.value = "pressed"

    def set_value(self, value):
        self.value = value

    def type_text(self, value):
        self.value = (self.value or "") + value

    def select(self):
        self.selected = True

    def focus(self):
        self.focused = True

    def scroll_into_view(self):
        self.visible = True

    def children(self):
        return self.children_values

    def parent(self):
        return self.parent_value


class App:
    name = "TextEdit"
    pid = 100
    is_foreground = True

    def __init__(self, window):
        self.window = window
        self.element = Element("application", self.name, children=[window])
        self.element.bounds = None
        self.element.active = True

    def as_element(self):
        return self.element

    def windows(self):
        return [self.window]

    def children(self):
        return self.element.children()


class FakeXa11y:
    App = App


def backend_with_button():
    button = Element("button", "Save")
    window = Element("window", "Untitled", children=[button])
    module = FakeXa11y()
    module.current = App(window)
    backend = Xa11yBackend(module)
    backend._resolve_app = lambda app: module.current
    return backend, window, button


def test_snapshot_has_complete_fields_and_consistent_tree():
    backend, window, button = backend_with_button()
    snapshot = backend.snapshot("TextEdit")
    assert snapshot["app"]["pid"] == 100
    root = snapshot["windows"][0]
    assert root["role"] == "application"
    window = root["children"][0]
    assert window["role"] == "window"
    assert window["children"][0]["role"] == "button"

    for node in (root, window, window["children"][0]):
        assert set(node) == {
            "ref", "platform", "role", "name", "value", "state", "bounds", "parent",
            "children", "actions", "platform_data",
        }
    assert root["parent"] is None
    assert window["parent"] == root["ref"]
    assert window["children"][0]["parent"] == window["ref"]
    assert window["children"][0]["platform_data"]["AXRole"] == "button"
    assert "read_error" not in root["platform_data"]


def test_refs_are_stable_for_identical_snapshot():
    backend, _, _ = backend_with_button()
    first = backend.snapshot("TextEdit")
    second = backend.snapshot("TextEdit")
    assert first == second


def test_window_filter_returns_selected_window_root():
    backend, window, _ = backend_with_button()
    app_ref = backend.snapshot("TextEdit")["windows"][0]["children"][0]["ref"]
    snapshot = backend.snapshot("TextEdit", "Untitled")
    assert len(snapshot["windows"]) == 1
    assert snapshot["windows"][0]["role"] == "window"
    assert snapshot["windows"][0]["name"] == "Untitled"
    assert snapshot["windows"][0]["ref"] == app_ref
    assert snapshot["windows"][0]["parent"] is None
    assert backend.get(snapshot["windows"][0]["children"][0]["ref"], "TextEdit")["name"] == "Save"

    windows = backend.windows("TextEdit")
    assert len(windows) == 1
    assert windows[0]["name"] == "Untitled"


def test_window_selection_prefers_exact_title_and_identity():
    backend, _, _ = backend_with_button()
    windows = [{"ref": "a", "name": "Main", "platform_data": {}},
               {"ref": "1234567890", "name": "Main detail", "platform_data": {}},
               {"ref": "c", "name": "0", "platform_data": {"native_stable_id": "hwnd:c"}}]
    assert backend._select_windows(windows, "Main") == [windows[0]]
    assert backend._select_windows(windows, "1234567890") == [windows[1]]
    assert backend._select_windows(windows, "0") == [windows[2]]
    assert backend._select_windows(windows, "1") == [windows[1]]
    assert backend._select_windows(windows, "hwnd:c") == [windows[2]]


def test_find_returns_exact_role_and_name():
    backend, _, button = backend_with_button()
    matches = backend.find("TextEdit", "button", "Save")
    assert len(matches) == 1
    assert matches[0]["name"] == "Save"
    assert backend.find("TextEdit", "button", "Close") == []


def test_get_resolves_ref_from_current_app():
    backend, _, button = backend_with_button()
    snapshot = backend.snapshot("TextEdit")
    root = snapshot["windows"][0]
    ref = root["children"][0]["children"][0]["ref"]
    assert backend.get(ref, "TextEdit")["name"] == "Save"


def test_cli_tree_renderer_indents_children():
    backend, _, _ = backend_with_button()
    snapshot = backend.snapshot("TextEdit")
    rendered = render_tree(snapshot["windows"][0])
    assert rendered.startswith("application[")
    assert "\n  window[" in rendered
    assert "\n    button[" in rendered


def test_cli_parser_routes_find():
    backend, _, _ = backend_with_button()
    args = build_parser().parse_args(
        ["find", "--app", "TextEdit", "--role", "button", "--name", "Save", "--json"]
    )
    result = execute(args, backend)
    assert isinstance(result, list)
    assert json.dumps(result)


def test_windows_preserve_distinct_nodes_with_repeated_native_ids():
    backend, first, _ = backend_with_button()
    first.stable_id = "_NS:34"
    second = Element("window", "Second")
    second.stable_id = "_NS:34"
    app = backend._resolve_app("TextEdit")
    app.element.children_values.append(second)
    # The upstream window API may deduplicate these IDs; use the app tree.
    assert len(app.windows()) == 1
    windows = backend.windows("TextEdit")
    assert [window["name"] for window in windows] == ["Untitled", "Second"]
    selected = backend.snapshot("TextEdit", windows[1]["ref"])["windows"][0]
    assert selected["name"] == "Second"
    assert backend.get(selected["ref"], "TextEdit")["name"] == "Second"


def test_apps_uses_app_metadata_without_element_properties():
    app = App(Element("window", "Untitled"))
    module = SimpleNamespace(App=SimpleNamespace(list=lambda: [app]))
    result = Xa11yBackend(module).apps()
    assert result == [{"pid": 100, "name": "TextEdit", "is_foreground": True, "role": "application"}]


def test_macos_nested_application_node_fails_before_recursive_traversal():
    import pytest
    from bokkio.model import BokkioError
    backend, _, _ = backend_with_button(); backend._platform = "macos"
    root = backend._resolve_app("TextEdit").element
    root.children_values = [root]
    with pytest.raises(BokkioError, match="application node nested below its root"):
        backend.snapshot("TextEdit")


def test_macos_other_application_identity_is_not_mistaken_for_root_cycle():
    backend, window, _ = backend_with_button(); backend._platform = "macos"
    remote = Element("application", "TextEdit"); remote.pid = 200
    window.children_values.append(remote); remote.parent_value = window
    snapshot = backend.snapshot("TextEdit")
    assert snapshot["windows"][0]["children"][0]["children"][-1]["name"] == "TextEdit"
