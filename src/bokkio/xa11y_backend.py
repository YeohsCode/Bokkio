from __future__ import annotations

import sys
import math
from collections import Counter
from typing import Any

from .model import BokkioActionError, BokkioError, BokkioPermissionError, path_signature, stable_hash, tree_digest
from .selector import choose, flatten
from .scroll import DIRECTIONS, axis, observe_scroll, plan_scroll


ACTION_METHODS = {
    "click": "press",
    "invoke": "press",
    "type": "type_text",
    "set_value": "set_value",
    "select": "select",
    "focus": "focus",
    "scroll": "set_numeric_value",
    "expand": "expand",
    "collapse": "collapse",
}

NORMALIZED_ACTIONS = {
    "press": "click",
    "axpress": "click",
    "click": "click",
    "invoke": "click",
    "type_text": "type",
    "set_value": "set_value",
    "select": "select",
    "focus": "focus",
    "expand": "expand",
    "collapse": "collapse",
}


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as error:
        message = str(error)
        if "Permission denied" in message and "Accessibility" in message:
            raise BokkioPermissionError.from_platform(error) from error
        if isinstance(error, BokkioError):
            raise
        raise BokkioError(message) from error


class Xa11yBackend:
    """Adapter around xa11y's Python element API."""

    def __init__(self, module: Any | None = None, platform: str | None = None, native: Any | None = None) -> None:
        real_provider = module is None
        if module is None:
            try:
                import xa11y as module
            except ImportError as error:
                raise BokkioError(
                    "xa11y is required. Install this package in an environment "
                    "that includes the xa11y wheel."
                ) from error
        self._xa11y = module
        self._platform = platform or (
            "windows" if sys.platform == "win32" else
            "macos" if sys.platform == "darwin" else "unknown"
        )
        self._native = native
        self._app_bindings = {}
        if real_provider and self._platform == "windows" and native is None:
            from .windows_uia import WindowsUIA
            self._native = _call(WindowsUIA)

    def apps(self) -> list[dict[str, Any]]:
        return [
            {
                "pid": app.pid,
                "name": app.name,
                "is_foreground": app.is_foreground,
                "role": "application",
            }
            for app in _call(self._xa11y.App.list)
        ]

    def windows(self, app: str) -> list[dict[str, Any]]:
        native_app = self._resolve_app(app)
        result = []
        app_tree = self._app_tree(native_app)
        for node in self._window_nodes(app_tree):
            result.append(
                {
                    "ref": node["ref"],
                    "role": node["role"],
                    "name": node["name"],
                    "value": node["value"],
                    "bounds": node["bounds"],
                    "minimized": node["state"]["minimized"],
                    "active": node["state"]["active"],
                    "platform_data": node["platform_data"],
                }
            )
        return result

    def snapshot(self, app: str, window: str | None = None) -> dict[str, Any]:
        native_app = self._resolve_app(app)
        app_tree = self._app_tree(native_app)
        if window is None:
            trees = [app_tree]
        else:
            selected = self._select_windows(self._window_nodes(app_tree), window)
            trees = [{**node, "parent": None} for node in selected]
        return {
            "app": self._app_info(native_app),
            "ref_strategy": "structural-v3",
            "window_filter": window,
            "windows": trees,
        }

    def perform(
        self,
        app: str,
        action: str,
        *,
        ref: str | None = None,
        role: str | None = None,
        name: str | None = None,
        parent: str | None = None,
        value: str | None = None,
        direction: str | None = None,
        amount: float | None = None,
        expected_value: str | None = None,
        expected_snapshot: str | None = None,
        window: str | None = None,
    ) -> dict[str, Any]:
        if action not in ACTION_METHODS:
            raise BokkioActionError(f"Unsupported action: {action}")
        if action == "scroll":
            if direction not in DIRECTIONS:
                raise BokkioActionError("scroll requires --direction up/down/left/right")
            amount = 0.25 if amount is None else amount
            if not math.isfinite(amount) or not 0 < amount <= 1:
                raise BokkioActionError("scroll amount must be finite and in (0, 1]")
        elif direction is not None or amount is not None:
            raise BokkioActionError("direction and amount are only valid for scroll")
        if expected_value is not None and action != "type":
            raise BokkioActionError("expect-value is only valid for type")
        if action in {"type", "set_value"} and value is None:
            raise BokkioActionError(f"{action} requires a value")
        if action not in {"type", "set_value"} and value is not None:
            raise BokkioActionError(f"{action} does not accept a value")

        native_app = self._resolve_app(app)
        live: dict[str, Any] = {}
        before_tree = self._app_tree(native_app, live)
        before_scope = ([before_tree] if window is None else
                        [{**n, "parent": None} for n in self._select_windows(self._window_nodes(before_tree), window)])
        if expected_snapshot is not None and tree_digest(before_scope) != expected_snapshot:
            raise BokkioActionError("Snapshot changed since decision; observe and decide again")
        before = choose(before_scope, ref=ref, role=role, name=name, parent=parent)
        native_value_write = action == "set_value" and before["platform_data"].get("value_runtime_id") and hasattr(self._native, "set_value")
        native_action = (action in before['platform_data'].get('verified_native_actions', [])
                         and before['platform_data'].get('action_runtime_id') and hasattr(self._native,'perform_action'))
        if expected_snapshot is not None and before["platform_data"].get("ambiguous_ref_identity") and not (native_value_write or native_action):
            raise BokkioActionError("Target has indistinguishable siblings without a unique native identity")
        radio_select = action == "select" and before["role"] == "radio_button"
        if before["state"].get("enabled") is False:
            raise BokkioActionError(f"Target is disabled: {before['ref']}")
        capability = "click" if action == "invoke" else action
        if action != "scroll" and capability not in before["actions"]:
            raise BokkioActionError(f"Action {action} is not advertised by target: {before['ref']}")
        element = live[before["ref"]]
        scope = before
        nodes = {n['ref']:n for n in flatten([before_tree])}
        while scope['role'] not in {'window','dialog'} and scope['parent'] in nodes:
            scope = nodes[scope['parent']]
        if scope['role'] in {'window','dialog'} and scope['state'].get('enabled') is False:
            raise BokkioActionError("Target window is disabled by a modal dialog; observe the active dialog")
        scroll_plan = plan_scroll(before_tree, before, direction, amount) if action == "scroll" else None
        write_source = None
        action_source = None
        try:
            if scroll_plan is not None:
                if scroll_plan["requested_position"] != scroll_plan["before_position"]:
                    if scroll_plan.get("source") == "UIA.ScrollPattern":
                        _call(self._native.scroll, live[scroll_plan["scope_ref"]],
                              scroll_plan["axis"], scroll_plan["requested_position"])
                    else:
                        _call(live[scroll_plan["bar_ref"]].set_numeric_value, scroll_plan["requested_position"])
            else:
                if action == "set_value" and before["platform_data"].get("value_source") == "UIA.ValuePattern" and hasattr(self._native, "set_value"):
                    identity = before["platform_data"].get("value_runtime_id")
                    write = _call(self._native.set_value, element, value, before["platform_data"].get("value_scope_hwnd"),
                          **({"expected_runtime_id":identity} if identity else {}))
                    if isinstance(write, dict): write_source = write.get('write_source')
                elif native_action:
                    native_result = _call(self._native.perform_action, element, action,
                                          before['platform_data']['action_scope_hwnd'],
                                          before['platform_data']['action_runtime_id'])
                    action_source = native_result.get('action_source')
                else:
                    method = getattr(element, "press" if radio_select else ACTION_METHODS[action])
                    if value is None:
                        _call(method)
                    else:
                        _call(method, value)
        except BokkioPermissionError:
            raise
        except Exception as error:
            raise BokkioActionError(f"{action} failed for {before['ref']}: {error}") from error

        after_tree = self._app_tree(native_app)
        after = self._find_by_ref(after_tree, before["ref"])
        verification = "observed"
        postcondition = None
        if action in {"set_value", "focus", "select", "expand", "collapse"} or expected_value is not None:
            verification = "unconfirmed"
            if after is None:
                postcondition = {"reason": "target_missing"}
        if action == "type" and expected_value is not None and after is not None:
            verification = "confirmed" if after["value"] == expected_value else "unconfirmed"
            postcondition = {"check": "value", "expected": expected_value, "actual": after["value"]}
        elif action == "set_value" and after is not None:
            verification = "confirmed" if after["value"] == value else "unconfirmed"
            postcondition = {"check": "value", "expected": value, "actual": after["value"]}
        elif action == "focus" and after is not None:
            verification = "confirmed" if after["state"]["focused"] else "unconfirmed"
        elif action == "select" and after is not None:
            selected = (
                after["state"]["checked"] == "on" if radio_select
                else after["state"]["selected"]
            )
            verification = "confirmed" if selected else "unconfirmed"
        elif action in {"expand", "collapse"} and after is not None:
            wanted = action == "expand"
            verification = "confirmed" if after["state"]["expanded"] is wanted else "unconfirmed"
            postcondition = {"check": "expanded", "expected": wanted, "actual": after["state"]["expanded"]}
        result = {
            "action": action,
            "target_ref": before["ref"],
            "before": before,
            "after": after,
            "verification": verification,
            "tree_changed": before_tree != after_tree,
        }
        if postcondition is not None:
            result["postcondition"] = postcondition
        if write_source is not None:
            result['write_source'] = write_source
        if action_source is not None:
            result['action_source'] = action_source
        if scroll_plan is not None:
            result["scroll"], changed = observe_scroll(before_tree, after_tree, scroll_plan)
            result["verification"] = "confirmed" if changed else "unconfirmed"
        return result

    def find(self, app: str, role: str, name: str | None = None) -> list[dict[str, Any]]:
        snapshot = self.snapshot(app)
        matches = []

        def visit(node: dict[str, Any]) -> None:
            if node["role"].lower() == role.lower() and (
                name is None
                or (node["name"] or "").casefold() == name.casefold()
            ):
                matches.append(node)
            for child in node["children"]:
                visit(child)

        for tree in snapshot["windows"]:
            visit(tree)
        return matches

    def get(self, ref: str, app: str | None = None) -> dict[str, Any]:
        apps = [self._resolve_app(app)] if app is not None else _call(self._xa11y.App.list)
        for native_app in apps:
            snapshot = self.snapshot(str(native_app.pid))
            for tree in snapshot["windows"]:
                found = self._find_by_ref(tree, ref)
                if found is not None:
                    return found
        raise BokkioError(
            f"Element ref does not match any current accessibility tree: {ref}. "
            "Take a new snapshot after the application UI changes."
        )

    def _resolve_app(self, app: str):
        value = app.strip()
        if value.isdigit():
            if self._platform == "windows" and value in self._app_bindings:
                return self._app_bindings[value]
            resolved = _call(self._xa11y.App.by_pid, int(value), timeout=0)
            if self._platform == "windows":
                # xa11y's synthesized App retains process creation identity;
                # as_element/children still take fresh native snapshots and
                # reject process reuse. Avoid desktop rediscovery on every
                # action, especially while this process owns a modal dialog.
                self._app_bindings[value] = resolved
            return resolved
        return _call(self._xa11y.App.by_name, value, timeout=0)

    def _app_info(self, app: Any) -> dict[str, Any]:
        return {
            "pid": app.pid,
            "name": app.name,
            "is_foreground": app.is_foreground,
            "role": "application",
        }

    def _app_identity(self, app: Any) -> list[Any]:
        return ["app", app.pid, app.name]

    def _app_tree(self, app: Any, live: dict[str, Any] | None = None) -> dict[str, Any]:
        identity = self._app_identity(app)
        element = _call(app.as_element)
        tree = self._walk(element, identity, [], parent_ref=None, occurrence=0, live=live)
        if self._platform == "windows":
            nodes = {n["ref"]: n for n in flatten([tree])}
            for node in nodes.values():
                if node["role"] != "scroll_bar":
                    continue
                scope = nodes.get(node["parent"])
                while scope is not None and "scroll" not in scope["platform_data"]:
                    scope = nodes.get(scope["parent"])
                coordinate = axis(node)
                if scope is not None and coordinate and scope["platform_data"]["scroll"][coordinate]["scrollable"]:
                    node["actions"] = sorted(set(node["actions"]) | {"scroll"})
        return tree

    def _window_nodes(self, app_tree: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        def visit(node):
            if node["role"] in {"window", "dialog"}:
                result.append(node)
                return
            for child in node["children"]:
                visit(child)
        visit(app_tree)
        return result

    def _select_windows(
        self, windows: list[dict[str, Any]], selector: str | None
    ) -> list[dict[str, Any]]:
        if selector is None:
            return windows
        exact = [window for window in windows if selector == window["ref"]
                 or selector == window["platform_data"].get("native_stable_id")]
        if exact:
            return exact
        exact = [window for window in windows if selector.casefold() == (window["name"] or "").casefold()]
        if exact:
            return exact
        matches = []
        if selector.isdigit():
            index = int(selector)
            if 0 <= index < len(windows):
                matches.append(windows[index])
        else:
            matches.extend(
                window
                for window in windows
                if selector == window["ref"]
                or selector.casefold() in (window["name"] or "").casefold()
                or selector == window["platform_data"].get("native_stable_id")
            )
        if not matches:
            raise BokkioError(f"Window not found: {selector}")
        return matches

    def _walk(
        self,
        element: Any,
        identity: list[Any],
        signature_path: list[list[Any]],
        parent_ref: str | None,
        occurrence: int,
        live: dict[str, Any] | None = None,
        stable_label: bool = False,
        native_identity: str | None = None,
        ambiguous_identity: bool = False,
        native_window: int | None = None,
    ) -> dict[str, Any]:
        if len(signature_path) >= 64:
            raise BokkioError("Accessibility tree exceeds 64 levels; provider may contain a cycle")
        role = self._role(element)
        stable = _call(lambda: element.stable_id)
        if self._platform == "windows" and role in {"window", "dialog"} and stable and stable.startswith("hwnd:"):
            native_window = int(stable[5:], 0)
        name = _call(lambda: element.name)
        if (self._platform == "macos" and parent_ref is not None and role == "application"
                and name == identity[2] and _call(lambda: getattr(element, "pid", identity[1])) == identity[1]):
            raise BokkioError("Invalid macOS Accessibility tree: application node nested below its root")
        part = path_signature(role, None if stable_label else name, occurrence if native_identity is None else 0)
        if native_identity is not None:
            part.append(native_identity)
        next_path = signature_path + [part]
        ref = stable_hash(identity + next_path)
        if live is not None:
            live[ref] = element
        child_refs = []
        children = []
        counts: dict[tuple[str, str | None], int] = {}
        child_elements = [
            (child, self._role(child), _call(lambda: child.name))
            for child in _call(element.children)
        ]
        role_counts = Counter(role for _, role, _ in child_elements)
        native_ids = [_call(lambda: child.stable_id) for child, _, _ in child_elements]
        native_counts = Counter(native_ids)
        signature_counts = Counter((child_role, child_name) for _, child_role, child_name in child_elements)
        for (child, child_role, child_name), native_id in zip(child_elements, native_ids):
            signature = (child_role, child_name)
            child_occurrence = counts.get(signature, 0)
            counts[signature] = child_occurrence + 1
            # A single passive label is a value of its parent, not an action identity.
            # Keep names in interactive identities so changed controls invalidate refs.
            stable_label = (
                child_role == "static_text" and role_counts[child_role] == 1
                and not any(a.casefold() in {"press", "axpress", "click", "invoke"}
                            for a in _call(lambda: child.actions))
            )
            hwnd_identity = (native_id if self._platform == "windows" and native_id
                             and native_id.startswith("hwnd:") and native_counts[native_id] == 1 else None)
            node = self._walk(child, identity, next_path, ref, child_occurrence, live,
                              stable_label=stable_label,
                              native_identity=hwnd_identity,
                              native_window=native_window,
                              ambiguous_identity=ambiguous_identity or (
                                  signature_counts[signature] > 1 and hwnd_identity is None))
            children.append(node)
            child_refs.append(node["ref"])
        node = self._node(
            role=role,
            name=name,
            value=_call(lambda: element.value),
            bounds=self._bounds(_call(lambda: element.bounds)),
            parent=parent_ref,
            children=children,
            identity=identity,
            signature_path=next_path,
            raw=self._safe_raw(element),
            child_refs=child_refs,
            element=element,
            native_window=native_window,
        )
        if ambiguous_identity:
            node["platform_data"]["ambiguous_ref_identity"] = True
        needs_toggle_state = 'toggle' in [a.casefold() for a in node['platform_data'].get('actions', [])]
        if ambiguous_identity or needs_toggle_state:
            if (native_window is not None and self._native is not None
                    and hasattr(self._native,'action_capabilities') and hasattr(self._native,'perform_action')
                    and set(node['actions']) & {'click','expand','collapse','select'}):
                try:
                    capability = self._native.action_capabilities(element, native_window)
                    if capability and capability.get('runtime_id'):
                        data=node['platform_data']
                        data.update(action_runtime_id=capability['runtime_id'], action_scope_hwnd=native_window,
                                    verified_native_actions=sorted(set(node['actions']) & set(capability['actions'])))
                        node['state'].update(capability.get('state',{}))
                except Exception as error:
                    node['platform_data']['action_identity_error']=str(error)
        return node

    def _node(
        self,
        role: str,
        name: str | None,
        value: str | None,
        bounds: dict[str, int] | None,
        parent: str | None,
        children: list[dict[str, Any]],
        identity: list[Any],
        signature_path: list[list[Any]],
        raw: dict[str, Any],
        child_refs: list[str] | None = None,
        element: Any | None = None,
        native_window: int | None = None,
    ) -> dict[str, Any]:
        state = self._state(element) if element is not None else {}
        ref = stable_hash(identity + signature_path)
        platform_data = dict(raw)
        platform_data["description"] = (
            _call(lambda: element.description) if element is not None else None
        )
        native_actions = _call(lambda: element.actions) if element is not None else []
        platform_data["actions"] = native_actions
        actions = sorted({
            NORMALIZED_ACTIONS[action.casefold()]
            for action in native_actions if action.casefold() in NORMALIZED_ACTIONS
        })
        if role == "radio_button" and "click" in actions and "select" not in actions:
            actions.append("select")
            actions.sort()
        platform_data["native_stable_id"] = (
            _call(lambda: element.stable_id) if element is not None else None
        )
        if self._native is not None and (role in {"text_field", "text_area"} or "set_value" in actions) and role != "scroll_bar":
            try:
                pattern = (self._native.scoped_value(element, native_window) if hasattr(self._native, "scoped_value") else self._native.value(element))
                if pattern and pattern.get("available"):
                    value = pattern["value"]
                    state["editable"] = not pattern["readonly"]
                    platform_data["value_source"] = pattern["source"]
                    platform_data["value_scope_hwnd"] = native_window
                    if pattern.get("runtime_id"):
                        platform_data["value_runtime_id"] = pattern["runtime_id"]
                    if pattern["readonly"]:
                        actions = [a for a in actions if a not in {"type", "set_value"}]
                    elif role in {"text_field", "text_area"}:
                        actions = sorted(set(actions) | {"type", "set_value"})
                else:
                    state["editable"] = False if pattern is not None else None
                    actions = [a for a in actions if a not in {"type", "set_value"}]
            except Exception as error:
                platform_data["value_read_error"] = str(error)
                state["editable"] = None
                actions = [a for a in actions if a not in {"type", "set_value"}]
        if state.get("editable") and role in {"text_field", "text_area"}:
            actions = sorted(set(actions) | {"type", "set_value"})
        if role == "combo_box":
            editors = [n for n in flatten(children) if n["role"] == "text_field"
                       and n["name"] == name and n["value"] == value and "set_value" in n["actions"]]
            if len(editors) == 1:
                actions = [a for a in actions if a not in {"type", "set_value"}]
                platform_data["text_write_target"] = editors[0]["ref"]
        if state.get("focusable"):
            actions = sorted(set(actions) | {"focus"})
        # xa11y's macOS select() writes AXSelected for these native roles.
        if self._platform == "macos" and role in {"row", "list_item", "tree_item"} and state.get("selected") is not None:
            actions = sorted(set(actions) | {"select"})
        if self._native is not None and role in {"group", "list", "table", "tree", "text_area", "scroll_area", "pane"}:
            try:
                scroll = self._native.scroll_state(element)
                if scroll is not None:
                    platform_data["scroll"] = scroll
                    if any(scroll[a]["scrollable"] for a in ("x", "y")):
                        actions = sorted(set(actions) | {"scroll"})
            except Exception as error:
                platform_data["scroll_read_error"] = str(error)
        node = {
            "ref": ref,
            "platform": self._platform,
            "role": role,
            "name": name,
            "value": value,
            "state": state,
            "bounds": bounds,
            "parent": parent,
            "children": children if children else (child_refs or []),
            "actions": actions,
            "platform_data": platform_data,
        }
        if role == "scroll_bar":
            node["actions"] = [a for a in node["actions"] if a != "set_value"]
            platform_data["numeric_value"] = _call(lambda: element.numeric_value)
            numeric = platform_data["numeric_value"]
            if self._platform == "macos" and numeric is not None and math.isfinite(numeric) and 0 <= numeric <= 1 and axis(node):
                node["actions"] = sorted(set(node["actions"]) | {"scroll"})
        return node

    def _role(self, element):
        role = _call(lambda: element.role)
        if self._platform == "windows" and role == "web_area":
            raw = self._safe_raw(element)
            if raw.get("control_type_id") == 50030 and raw.get("class_name", "").casefold() in {"edit", "richedit", "richeditd2dpt"}:
                return "text_area"
        return role

    def _state(self, element: Any) -> dict[str, Any]:
        return {
            "enabled": _call(lambda: element.enabled),
            "visible": _call(lambda: element.visible),
            "focused": _call(lambda: element.focused),
            "active": _call(lambda: element.active),
            "selected": _call(lambda: element.selected),
            "editable": _call(lambda: element.editable),
            "focusable": _call(lambda: element.focusable),
            "checked": _call(lambda: element.checked),
            "expanded": _call(lambda: element.expanded),
            "minimized": _call(lambda: element.minimized),
            "maximized": _call(lambda: element.maximized),
            "fullscreen": _call(lambda: element.fullscreen),
        }

    def _bounds(self, bounds: Any) -> dict[str, int] | None:
        if bounds is None:
            return None
        return {"x": bounds.x, "y": bounds.y, "width": bounds.width, "height": bounds.height}

    def _safe_raw(self, element: Any) -> dict[str, Any]:
        try:
            return dict(_call(lambda: element.raw))
        except Exception as error:
            return {"read_error": str(error)}

    def _find_by_ref(self, node: dict[str, Any], ref: str) -> dict[str, Any] | None:
        if node["ref"] == ref:
            return node
        for child in node["children"]:
            found = self._find_by_ref(child, ref)
            if found is not None:
                return found
        return None
