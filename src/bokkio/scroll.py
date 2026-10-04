"""Directional native scrolling with position and content readback."""
from __future__ import annotations

import math
from typing import Any

from .model import BokkioActionError
from .selector import flatten

DIRECTIONS = {"up": ("y", -1), "down": ("y", 1), "left": ("x", -1), "right": ("x", 1)}


def axis(node: dict[str, Any]) -> str | None:
    bounds = node.get("bounds") or {}
    width, height = bounds.get("width", 0), bounds.get("height", 0)
    if width <= 0 or height <= 0 or width == height:
        return None
    return "y" if height > width else "x"


def _bars(scope: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for child in scope["children"]:
        if child["role"] == "scroll_bar":
            result.append(child)
        elif child["platform_data"].get("ax_role") != "AXScrollArea":
            result.extend(_bars(child))
    return result


def plan_scroll(tree: dict[str, Any], target: dict[str, Any], direction: str, amount: float):
    wanted_axis, sign = DIRECTIONS[direction]
    nodes = {n["ref"]: n for n in flatten([tree])}
    scope = target
    if target.get("platform") == "windows":
        while "scroll" not in scope["platform_data"]:
            scope = nodes.get(scope["parent"])
            if scope is None:
                raise BokkioActionError("No containing UIA ScrollPattern")
        info = scope["platform_data"]["scroll"][wanted_axis]
        if scope["state"].get("enabled") is False or not info["scrollable"]:
            raise BokkioActionError(f"Container cannot scroll on {wanted_axis} axis")
        numeric = info["position"]
        if numeric is None or not math.isfinite(numeric) or not 0 <= numeric <= 1:
            raise BokkioActionError("UIA ScrollPattern position must be in [0, 1]")
        return {"source": "UIA.ScrollPattern", "scope_ref": scope["ref"], "axis": wanted_axis,
                "direction": direction, "amount": amount, "before_position": numeric,
                "requested_position": min(1.0, max(0.0, numeric + sign * amount))}
    if target["role"] == "scroll_bar":
        bars = [target]
        scope = nodes.get(target["parent"], target)
    else:
        while scope["platform_data"].get("ax_role") != "AXScrollArea":
            scope = nodes.get(scope["parent"])
            if scope is None:
                raise BokkioActionError("No containing AXScrollArea; target a scroll area or scroll bar")
        bars = _bars(scope)
    bars = [bar for bar in bars if axis(bar) == wanted_axis]
    if len(bars) != 1:
        raise BokkioActionError(f"Expected one {wanted_axis}-axis scroll bar; found {len(bars)}")
    bar = bars[0]
    if bar["state"].get("enabled") is False:
        raise BokkioActionError("Scroll bar is disabled")
    numeric = bar["platform_data"].get("numeric_value")
    if numeric is None or not math.isfinite(numeric) or not 0 <= numeric <= 1:
        raise BokkioActionError("macOS scroll bar must expose a numeric position in [0, 1]")
    # macOS AXScrollBar positions use a normalized 0..1 range.
    requested = min(1.0, max(0.0, numeric + sign * amount))
    return {"bar_ref": bar["ref"], "scope_ref": scope["ref"], "axis": wanted_axis,
            "direction": direction, "amount": amount, "before_position": numeric,
            "requested_position": requested}


def observe_scroll(before_tree, after_tree, plan):
    previous = {n["ref"]: n for n in flatten([before_tree])}
    current = {n["ref"]: n for n in flatten([after_tree])}
    if plan.get("source") == "UIA.ScrollPattern":
        container = current.get(plan["scope_ref"])
        actual = (container or {}).get("platform_data", {}).get("scroll", {}).get(plan["axis"], {}).get("position")
    else:
        bar = current.get(plan["bar_ref"])
        actual = bar["platform_data"].get("numeric_value") if bar else None
    scope = previous[plan["scope_ref"]]
    current_scope = current.get(plan["scope_ref"])
    def content(root):
        if root is None or root["role"] in {"scroll_bar", "scroll_thumb"}:
            return []
        return [root] + [n for child in root["children"] for n in content(child)]
    old_nodes, new_nodes = content(scope), content(current_scope)
    moved = 0
    old_origin = (scope.get("bounds") or {}).get(plan["axis"], 0)
    new_origin = ((current_scope or {}).get("bounds") or {}).get(plan["axis"], 0)
    for old in old_nodes:
        new = current.get(old["ref"])
        if new is None:
            continue
        if old["bounds"] and new["bounds"] and old["bounds"][plan["axis"]] - old_origin != new["bounds"][plan["axis"]] - new_origin:
            moved += 1
    sign = DIRECTIONS[plan["direction"]][1]
    old_content = {n["ref"] for n in old_nodes}
    new_content = {n["ref"] for n in new_nodes}
    content_changes = len(old_content ^ new_content)
    visibility_changes = sum(old["state"].get("visible") != current[old["ref"]]["state"].get("visible")
                             for old in old_nodes if old["ref"] in current)
    position_changed = actual is not None and math.isfinite(actual) and sign * (actual - plan["before_position"]) > 1e-6
    changed = position_changed and bool(moved or content_changes or visibility_changes)
    if actual is None:
        reason = "scroll_position_missing"
    elif plan["requested_position"] == plan["before_position"]:
        reason = "at_boundary"
    elif changed:
        reason = "scroll_position_and_content_changed"
    elif position_changed:
        reason = "content_movement_unconfirmed"
    else:
        reason = "scroll_position_unchanged"
    return {**plan, "after_position": actual, "content_nodes_moved": moved,
            "content_refs_changed": content_changes, "visibility_changes": visibility_changes,
            "reason": reason}, changed
