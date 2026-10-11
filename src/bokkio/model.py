from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


class BokkioError(RuntimeError):
    pass


class BokkioLookupError(BokkioError):
    def __init__(self, code: str, selector: dict[str, Any], candidates: list[dict[str, Any]]):
        self.code = code
        self.selector = selector
        self.candidates = [
            {key: node.get(key) for key in ("ref", "role", "name", "parent")}
            for node in candidates[:10]
        ]
        super().__init__(f"{code}: {selector}; candidates={self.candidates}")

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "selector": self.selector, "candidates": self.candidates}


class BokkioActionError(BokkioError):
    pass


class BokkioCompletionUnknown(BokkioActionError):
    """A native call started; its business effect needs manual inspection."""


class BokkioStaleSnapshot(BokkioActionError):
    """The decision was refused before any native dispatch."""


def native_error_details(error):
    """Keep structured native failure facts through adapter error wrappers."""
    seen = set()
    for _ in range(8):
        if error is None or id(error) in seen:
            return None
        seen.add(id(error))
        if isinstance(getattr(error, "code", None), str) and isinstance(getattr(error, "details", None), dict):
            return {"code": error.code, "details": error.details}
        error = error.__cause__
    return None


class BokkioPermissionError(BokkioError):
    MESSAGE = (
        "macOS Accessibility permission is required. "
        "Grant it to the host application or resolved Python binary in "
        "System Settings > Privacy & Security > Accessibility, then restart "
        "the terminal and retry. macOS may also require Screen Recording to "
        "read window content."
    )

    @classmethod
    def from_platform(cls, error: Exception) -> "BokkioPermissionError":
        result = cls(cls.MESSAGE)
        result.__cause__ = error
        return result


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def path_signature(role: str, name: str | None, occurrence: int) -> list[Any]:
    return [role, name, occurrence]


def tree_digest(trees: Any) -> str:
    """Bind semantic state; freshly resolved Mac menu handles are ephemeral.

    Menu labels, paths, capabilities and states remain bound. Their CFHash is
    an in-process dispatch handle, independently revalidated by MacAX.perform,
    and can change on every observation of an otherwise identical command.
    """
    def semantic(value):
        if isinstance(value,list):return [semantic(v) for v in value]
        if isinstance(value,dict):
            result={k:semantic(v) for k,v in value.items()}
            data=result.get('platform_data')
            if result.get('platform')=='macos' and isinstance(data,dict):
                # Help text is not part of the decision's normalized UI state.
                # Office updates unnamed status-button descriptions during
                # background proofing, with identical identity/capabilities.
                data.pop('AXHelp',None)
                if result.get('role')=='button' and not result.get('name'):
                    data.pop('AXDescription',None);data.pop('description',None)
            if (result.get('platform')=='macos' and isinstance(data,dict)
                    and data.get('native_menu_attribute')):
                data.pop('ax_native_identity',None)
            return result
        return value
    return stable_hash(semantic(trees))


@dataclass(frozen=True)
class RefResolver:
    """Resolves a ref by regenerating deterministic structural identities."""

    nodes: Any

    def get(self, ref: str) -> dict[str, Any] | None:
        if not ref:
            raise BokkioError("Element ref must not be empty")
        found = _find_ref(self.nodes, ref)
        if found is None:
            raise BokkioError(
                f"Element ref does not match the current snapshot: {ref}. "
                "Take a new snapshot after the application UI changes."
            )
        return found


def _find_ref(nodes: Any, ref: str) -> dict[str, Any] | None:
    if isinstance(nodes, dict):
        if nodes.get("ref") == ref:
            return nodes
        for child in nodes.get("children") or []:
            found = _find_ref(child, ref)
            if found is not None:
                return found
    elif isinstance(nodes, list):
        for child in nodes:
            found = _find_ref(child, ref)
            if found is not None:
                return found
    return None
