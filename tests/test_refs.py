from bokkio.xa11y_backend import Xa11yBackend
from test_cli import App, Element, FakeXa11y


def make_backend(children):
    module = FakeXa11y()
    module.current = App(Element("window", "Fixture", children=children))
    backend = Xa11yBackend(module)
    backend._resolve_app = lambda app: module.current
    return backend


def test_single_label_value_changes_keep_ref_but_control_names_invalidate():
    label = Element("static_text", "Status: Ready")
    button = Element("button", "Save")
    backend = make_backend([label, button])
    label_ref = backend.find("TextEdit", "static_text")[0]["ref"]
    button_ref = backend.find("TextEdit", "button")[0]["ref"]
    label.name = "Status: Done"
    label.bounds.y += 30
    button.name = "Delete"
    assert backend.find("TextEdit", "static_text")[0]["ref"] == label_ref
    assert backend.get(label_ref, "TextEdit")["name"] == "Status: Done"
    assert backend.find("TextEdit", "button")[0]["ref"] != button_ref


def test_multiple_or_clickable_labels_keep_name_in_identity():
    first, second = Element("static_text", "A"), Element("static_text", "B")
    backend = make_backend([first, second])
    old = backend.find("TextEdit", "static_text", "A")[0]["ref"]
    first.name = "Changed"
    assert backend.find("TextEdit", "static_text", "Changed")[0]["ref"] != old
    clickable = Element("static_text", "Activate")
    clickable.actions = ["press"]
    backend = make_backend([clickable])
    old = backend.find("TextEdit", "static_text")[0]["ref"]
    clickable.name = "Remove"
    assert backend.find("TextEdit", "static_text")[0]["ref"] != old
