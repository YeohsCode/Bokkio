"""Small UIA supplement for ValuePattern readback and ScrollPattern.

xa11y supplies tree traversal and action dispatch. This module preserves empty
ValuePattern strings and exposes container scrolling absent from its API.
"""
from __future__ import annotations

import sys
from typing import Any

from .model import BokkioError


class WindowsUIA:
    def __init__(self):
        # Match xa11y's MTA before comtypes initializes the current thread.
        sys.coinit_flags = 0
        from comtypes.client import CreateObject, GetModule
        from comtypes import CLSCTX_INPROC_SERVER
        self.types = GetModule("UIAutomationCore.dll")
        self.automation = CreateObject(self.types.CUIAutomation8,
                                       interface=self.types.IUIAutomation,
                                       clsctx=CLSCTX_INPROC_SERVER)

    def _element(self, element: Any, scope_hwnd=None):
        stable = element.stable_id or ""
        if not stable.startswith("hwnd:"):
            if scope_hwnd is None:
                return None
            root = self.automation.ElementFromHandle(scope_hwnd)
            process_id = element.pid
            if root.CurrentProcessId != process_id:
                # Settings' CoreWindow is hosted inside ApplicationFrameHost.
                # xa11y reports the host PID for its descendants. Accept the
                # provider PID only while its Win32 top-level owner is that host.
                if (root.CurrentClassName != 'Windows.UI.Core.CoreWindow'
                        or self._root_process_id(scope_hwnd) != process_id):
                    raise BokkioError('Native scope is outside the observed application process')
                process_id = root.CurrentProcessId
            raw = element.raw
            # AutomationId is not globally unique. Resolve inside the observed
            # native window, with process/type/name/class and exact bounds.
            properties = [(self.types.UIA_ProcessIdPropertyId, process_id),
                          (self.types.UIA_ControlTypePropertyId, raw.get("control_type_id")),
                          (self.types.UIA_NamePropertyId, raw.get("uia_name", element.name or ""))]
            for key, prop in [("automation_id", self.types.UIA_AutomationIdPropertyId),
                              ("class_name", self.types.UIA_ClassNamePropertyId)]:
                if raw.get(key): properties.append((prop, raw[key]))
            if any(value is None for _, value in properties): return None
            condition = self.automation.CreatePropertyCondition(*properties[0])
            for prop, value in properties[1:]:
                condition = self.automation.CreateAndCondition(condition, self.automation.CreatePropertyCondition(prop, value))
            matches = root.FindAll(self.types.TreeScope_Subtree, condition)
            bounds = element.bounds
            candidates = []
            count = matches.Length
            if not 0 <= count <= 4096:
                raise BokkioError('UIA candidate collection exceeds the bounded native lookup')
            for i in range(count):
                candidate = matches.GetElement(i)
                # Use the VARIANT property transport (left, top, width, height).
                # The struct-return getter was the active frame in an ARM64
                # guest's x64-provider access violation. No alternate candidate
                # is accepted when the property is malformed or unavailable.
                rect = candidate.GetCurrentPropertyValue(self.types.UIA_BoundingRectanglePropertyId)
                import math
                if (not isinstance(rect, (tuple, list)) or len(rect) != 4
                        or any(type(v) not in {int, float} or not math.isfinite(v) for v in rect)):
                    raise BokkioError('UIA candidate has invalid bounding rectangle data')
                if bounds is not None and tuple(rect) == (bounds.x, bounds.y, bounds.width, bounds.height):
                    candidates.append(candidate)
            return candidates[0] if len(candidates) == 1 else None
        hwnd = int(stable[5:], 0)
        native = self.automation.ElementFromHandle(hwnd)
        if element.pid is not None and native.CurrentProcessId != element.pid:
            raise BokkioError("UIA HWND now belongs to another process")
        raw = element.raw
        if raw.get("control_type_id") != native.CurrentControlType:
            # An HWND can host a wrapper and a document with different types.
            condition = self.automation.CreatePropertyCondition(
                self.types.UIA_ControlTypePropertyId, raw["control_type_id"])
            matches = native.FindAll(self.types.TreeScope_Subtree, condition)
            candidates = [matches.GetElement(i) for i in range(matches.Length)]
            candidates = [n for n in candidates
                          if n.CurrentProcessId == native.CurrentProcessId
                          and n.CurrentClassName == raw.get("class_name")
                          and n.CurrentName == raw.get("uia_name", "")]
            if len(candidates) != 1:
                raise BokkioError("UIA HWND target is missing or ambiguous; take a new snapshot")
            native = candidates[0]
        if raw.get("class_name") and raw["class_name"] != native.CurrentClassName:
            raise BokkioError("UIA HWND class changed; take a new snapshot")
        return native

    def _root_process_id(self, hwnd):
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32')
        user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
        user.GetAncestor.restype=wintypes.HWND
        user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        pid=wintypes.DWORD()
        user.GetWindowThreadProcessId(user.GetAncestor(hwnd,2),ctypes.byref(pid))
        return pid.value

    def _pattern(self, native, kind):
        available = getattr(self.types, f"UIA_Is{kind}PatternAvailablePropertyId")
        if not native.GetCurrentPropertyValue(available):
            return None
        pointer = native.GetCurrentPattern(getattr(self.types, f"UIA_{kind}PatternId"))
        return pointer.QueryInterface(getattr(self.types, f"IUIAutomation{kind}Pattern"))

    def value(self, element):
        return self.scoped_value(element)

    def action_capabilities(self, element, scope_hwnd):
        native = self._element(element, scope_hwnd)
        if native is None: return None
        actions = []
        state = {}
        invoke = self._pattern(native, 'Invoke')
        toggle = self._pattern(native, 'Toggle')
        expand = self._pattern(native, 'ExpandCollapse')
        selection = self._pattern(native, 'SelectionItem')
        if invoke is not None or toggle is not None: actions.append('click')
        if toggle is not None:
            state['checked'] = {0:False, 1:True}.get(toggle.CurrentToggleState)
        if expand is not None and expand.CurrentExpandCollapseState != 3:
            actions.extend(['expand','collapse'])
            state['expanded'] = expand.CurrentExpandCollapseState in {1,2}
        if selection is not None:
            actions.append('select')
            state['selected']=bool(selection.CurrentIsSelected)
        return {'runtime_id':list(native.GetRuntimeId()), 'process_id':native.CurrentProcessId,
                'actions':actions, 'state':state}

    def perform_action(self, element, action, scope_hwnd, expected_runtime_id):
        native = self._element(element, scope_hwnd)
        if native is None or list(native.GetRuntimeId()) != expected_runtime_id:
            raise BokkioError('UIA action target identity changed; take a new snapshot')
        if not native.CurrentIsEnabled:
            raise BokkioError('UIA action target is disabled')
        kind, method = {'expand':('ExpandCollapse','Expand'), 'collapse':('ExpandCollapse','Collapse'),
                        'select':('SelectionItem','Select'), 'click':('Invoke','Invoke')}[action]
        pattern = self._pattern(native, kind)
        if action == 'click' and pattern is None:
            kind, method = 'Toggle', 'Toggle'
            pattern = self._pattern(native, kind)
        if pattern is None:
            raise BokkioError('Verified UIA action pattern is no longer available')
        if list(native.GetRuntimeId()) != expected_runtime_id:
            raise BokkioError('UIA action target identity changed before dispatch')
        getattr(pattern, method)()
        return {'action_source':'UIA.' + kind + 'Pattern'}

    def scoped_value(self, element, scope_hwnd=None):
        native = self._element(element, scope_hwnd)
        if native is None:
            return None
        pattern = self._pattern(native, "Value")
        if pattern is None:
            return {"available": False}
        return {"available": True, "value": pattern.CurrentValue,
                "readonly": bool(pattern.CurrentIsReadOnly), "source": "UIA.ValuePattern",
                "submit_available": bool(scope_hwnd is not None and not pattern.CurrentIsReadOnly
                    and native.CurrentIsKeyboardFocusable
                    and self.automation.ElementFromHandle(scope_hwnd).CurrentClassName in {'CabinetWClass','ExploreWClass'}
                    and native.CurrentClassName in {'TextBox','Edit','UIRenameTextElement'}),
                "runtime_id": list(native.GetRuntimeId())}

    def submit(self, element, scope_hwnd, expected_runtime_id, expected_value):
        """Commit an Explorer address/inline edit with one focus-bound Enter."""
        import ctypes
        from ctypes import wintypes
        root=self.automation.ElementFromHandle(scope_hwnd)
        if root.CurrentClassName not in {'CabinetWClass','ExploreWClass'} or root.CurrentProcessId!=element.pid:
            raise BokkioError('Enter submission requires the observed Explorer window')
        native=self._element(element,scope_hwnd)
        if native is None:raise BokkioError('Enter target is unavailable')
        pattern=self._pattern(native,'Value')
        if pattern is None or pattern.CurrentIsReadOnly or native.CurrentClassName not in {'TextBox','Edit','UIRenameTextElement'}:
            raise BokkioError('Enter target must be a writable Explorer edit')
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];user.GetAncestor.restype=wintypes.HWND
        user.GetForegroundWindow.restype=wintypes.HWND
        user.SetForegroundWindow.argtypes=[wintypes.HWND];user.SetForegroundWindow.restype=wintypes.BOOL
        top=user.GetAncestor(scope_hwnd,2)
        def identity():
            if (list(native.GetRuntimeId())!=expected_runtime_id or not native.CurrentIsEnabled
                    or native.CurrentProcessId!=element.pid or pattern.CurrentValue!=expected_value):
                raise BokkioError('Enter target identity/value changed before submission')
        identity()
        user.SetForegroundWindow(top)
        native.SetFocus()
        identity()
        focused=self.automation.GetFocusedElement()
        if (user.GetForegroundWindow()!=top or focused.CurrentProcessId!=element.pid
                or list(focused.GetRuntimeId())!=expected_runtime_id):
            raise BokkioError('Enter target is not the foreground focused native edit')
        class Keyboard(ctypes.Structure):
            _fields_=[('vk',wintypes.WORD),('scan',wintypes.WORD),('flags',wintypes.DWORD),
                      ('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class Mouse(ctypes.Structure):
            _fields_=[('x',wintypes.LONG),('y',wintypes.LONG),('data',wintypes.DWORD),
                      ('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class Payload(ctypes.Union):
            _fields_=[('keyboard',Keyboard),('mouse',Mouse)]
        class Input(ctypes.Structure):
            _fields_=[('kind',wintypes.DWORD),('payload',Payload)]
        events=(Input*2)()
        for i,flags in enumerate([0,2]):
            events[i].kind=1;events[i].payload.keyboard=Keyboard(13,0,flags,0,0)
        user.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(Input),ctypes.c_int]
        user.SendInput.restype=wintypes.UINT
        identity()
        if user.GetForegroundWindow()!=top or list(self.automation.GetFocusedElement().GetRuntimeId())!=expected_runtime_id:
            raise BokkioError('Foreground focus changed before Enter dispatch')
        sent=user.SendInput(2,events,ctypes.sizeof(Input))
        if sent!=2:
            if sent==1:user.SendInput(1,ctypes.byref(events[1]),ctypes.sizeof(Input))
            raise BokkioError('Enter dispatch was incomplete; completion must be observed')
        return {'action_source':'Win32.SendInput.VK_RETURN'}

    def set_value(self, element, value, scope_hwnd=None, expected_runtime_id=None):
        native = self._element(element, scope_hwnd)
        if native is None: raise BokkioError("Value target is missing or ambiguous in the native window")
        if expected_runtime_id is not None and list(native.GetRuntimeId()) != expected_runtime_id:
            raise BokkioError("UIA value target identity changed; take a new snapshot")
        pattern = self._pattern(native, "Value")
        if pattern is None or pattern.CurrentIsReadOnly:
            raise BokkioError("Target has no writable UIA ValuePattern")
        if scope_hwnd is not None and native.CurrentClassName == "Edit" and self.automation.ElementFromHandle(scope_hwnd).CurrentClassName == "#32770":
            # This provider's ValuePattern readback changes without committing
            # the classic dialog's filename. Edit messages emit the native text
            # change notifications; they are confined to the verified control.
            def check_identity():
                if native.CurrentProcessId != element.pid or (expected_runtime_id is not None and list(native.GetRuntimeId()) != expected_runtime_id):
                    raise BokkioError("Native dialog edit identity changed before replacement")
            self._replace_dialog_edit(native.CurrentNativeWindowHandle, scope_hwnd, value, check_identity)
            return {"write_source":"Win32.EM_REPLACESEL"}
        pattern.SetValue(value)
        return {"write_source":"UIA.ValuePattern"}

    def _replace_dialog_edit(self, hwnd, scope_hwnd, value, check_identity):
        import ctypes
        from ctypes import wintypes
        if not hwnd or '\0' in value:
            raise BokkioError("Native dialog edit needs a valid HWND and text without NUL")
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
        user.IsChild.restype = wintypes.BOOL
        if not user.IsChild(scope_hwnd, hwnd):
            raise BokkioError("Native edit is outside its observed dialog")
        send = user.SendMessageTimeoutW
        send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                         wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
        send.restype = wintypes.LPARAM
        result = ctypes.c_size_t()
        check_identity()
        if not send(hwnd, 0xB1, 0, -1, 2, 5000, ctypes.byref(result)):
            raise BokkioError("Native edit selection timed out; observe before retrying")
        check_identity()
        text = ctypes.create_unicode_buffer(value)
        if not send(hwnd, 0xC2, 1, ctypes.cast(text, ctypes.c_void_p).value, 2, 5000, ctypes.byref(result)):
            raise BokkioError("Native edit replacement timed out; completion is unknown")

    def scroll_state(self, element):
        native = self._element(element)
        if native is None:
            return None
        pattern = self._pattern(native, "Scroll")
        if pattern is None:
            return None
        return {"source": "UIA.ScrollPattern", "x": {
            "scrollable": bool(pattern.CurrentHorizontallyScrollable),
            "position": pattern.CurrentHorizontalScrollPercent / 100,
            "view_size": pattern.CurrentHorizontalViewSize / 100}, "y": {
            "scrollable": bool(pattern.CurrentVerticallyScrollable),
            "position": pattern.CurrentVerticalScrollPercent / 100,
            "view_size": pattern.CurrentVerticalViewSize / 100}}

    def scroll(self, element, axis: str, position: float):
        native = self._element(element)
        if native is None:
            raise BokkioError("Scroll container has no native HWND")
        pattern = self._pattern(native, "Scroll")
        if pattern is None:
            raise BokkioError("ScrollPattern is no longer available")
        pattern.SetScrollPercent(position * 100 if axis == "x" else -1,
                                 position * 100 if axis == "y" else -1)
