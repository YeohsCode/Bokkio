from types import SimpleNamespace

import pytest

from bokkio.cli import build_parser, execute
from bokkio.model import BokkioActionError
from bokkio.xa11y_backend import Xa11yBackend
from test_cli import App, Element, FakeXa11y


def scroll_backend(horizontal=False, position=0.5):
    label = Element("static_text", "Contents")
    bar = Element("scroll_bar")
    bar.bounds = SimpleNamespace(x=0, y=0, width=100 if horizontal else 10, height=10 if horizontal else 100)
    bar.numeric_value = position
    writes = []
    def set_numeric(value):
        writes.append(value)
        delta = value - bar.numeric_value
        bar.numeric_value = value
        coordinate = "x" if horizontal else "y"
        setattr(label.bounds, coordinate, getattr(label.bounds, coordinate) - round(delta * 100))
    bar.set_numeric_value = set_numeric
    area = Element("group", children=[label, bar])
    area.raw = {"ax_role": "AXScrollArea"}
    module = FakeXa11y()
    module.current = App(Element("window", "Fixture", children=[area]))
    backend = Xa11yBackend(module, platform="macos")
    backend._resolve_app = lambda app: module.current
    return backend, area, bar, label, writes


@pytest.mark.parametrize("direction,horizontal,expected", [
    ("up", False, 0.25), ("down", False, 0.75), ("left", True, 0.25), ("right", True, 0.75),
])
def test_directional_scroll_resolves_container_and_checks_position(direction, horizontal, expected):
    backend, _, bar, _, writes = scroll_backend(horizontal)
    result = backend.perform("TextEdit", "scroll", role="static_text", name="Contents", direction=direction)
    assert writes == [expected]
    assert result["verification"] == "confirmed"
    assert result["scroll"]["content_nodes_moved"] == 1
    assert "scroll" in backend.find("TextEdit", "scroll_bar")[0]["actions"]


def test_boundary_and_native_noop_do_not_claim_movement():
    backend, _, bar, _, writes = scroll_backend(position=0)
    result = backend.perform("TextEdit", "scroll", role="scroll_bar", direction="up")
    assert writes == []
    assert result["verification"] == "unconfirmed"
    assert result["scroll"]["reason"] == "at_boundary"
    bar.set_numeric_value = lambda value: None
    result = backend.perform("TextEdit", "scroll", role="scroll_bar", direction="down")
    assert result["verification"] == "unconfirmed"
    assert result["scroll"]["reason"] == "scroll_position_unchanged"


@pytest.mark.parametrize("amount", [0, -0.1, 1.01, float("nan"), float("inf")])
def test_invalid_scroll_amount_has_no_side_effect(amount):
    backend, _, _, _, writes = scroll_backend()
    with pytest.raises(BokkioActionError, match="amount"):
        backend.perform("TextEdit", "scroll", role="scroll_bar", direction="down", amount=amount)
    assert writes == []


def test_wrong_axis_ambiguous_bars_and_nested_scope_are_rejected():
    backend, area, bar, label, writes = scroll_backend()
    with pytest.raises(BokkioActionError, match="found 0"):
        backend.perform("TextEdit", "scroll", role="static_text", name="Contents", direction="left")
    area.children_values.append(bar)
    with pytest.raises(BokkioActionError, match="found 2"):
        backend.perform("TextEdit", "scroll", role="static_text", name="Contents", direction="up")
    area.children_values.pop()
    inner = Element("group", children=[label])
    inner.raw = {"ax_role": "AXScrollArea"}
    area.children_values[0] = inner
    with pytest.raises(BokkioActionError, match="found 0"):
        backend.perform("TextEdit", "scroll", role="static_text", name="Contents", direction="up")
    assert writes == []


def test_scroll_cli_routes_direction_and_amount():
    backend, _, _, _, writes = scroll_backend()
    args = build_parser().parse_args(["act", "--app", "TextEdit", "--action", "scroll", "--role", "scroll_bar", "--direction", "down", "--amount", "0.1"])
    assert execute(args, backend)["verification"] == "confirmed"
    assert writes == [0.6]
