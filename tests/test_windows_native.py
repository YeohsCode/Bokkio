import pytest
from bokkio.model import BokkioActionError, BokkioLookupError
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend
from test_cli import App, Element, FakeXa11y


class Native:
    def value(self, element):
        return {"available": True, "value": element.value or "", "readonly": element.name == "Read only", "source": "UIA.ValuePattern"}

    def scroll_state(self, element):
        from copy import deepcopy
        return deepcopy(getattr(element, "scroll", None))

    def scroll(self, element, axis, position):
        old = element.scroll[axis]["position"]
        element.scroll[axis]["position"] = position
        label = element.children_values[0]
        setattr(label.bounds, axis, getattr(label.bounds, axis) - round((position - old) * 100))


def backend(children, native=None):
    module = FakeXa11y()
    module.current = App(Element("window", "Fixture", children=children))
    b = Xa11yBackend(module, platform="windows", native=native)
    b._resolve_app = lambda _: module.current
    return b


def test_disabled_dialog_blocks_its_advertised_enabled_button():
    button=Element('button','Save')
    dialog=Element('dialog','Save As',children=[button]);dialog.enabled=False
    b=backend([dialog])
    with pytest.raises(BokkioActionError,match='modal dialog'):
        b.perform('app','click',role='button',name='Save')
    assert button.value is None


@pytest.mark.parametrize('readonly', [False, True])
def test_classic_dialog_edit_uses_verified_native_replacement(readonly):
    from types import SimpleNamespace
    from bokkio.windows_uia import WindowsUIA
    from bokkio.model import BokkioError
    helper=object.__new__(WindowsUIA);writes=[];pattern_writes=[]
    native=SimpleNamespace(CurrentClassName='Edit',CurrentProcessId=100,CurrentNativeWindowHandle=101,
                           GetRuntimeId=lambda:[1])
    helper._element=lambda *_:native
    helper._pattern=lambda *_:SimpleNamespace(CurrentIsReadOnly=readonly,SetValue=pattern_writes.append)
    helper.automation=SimpleNamespace(ElementFromHandle=lambda _:SimpleNamespace(CurrentClassName='#32770'))
    def replace(hwnd, scope, value, check):
        check();writes.append((hwnd,scope,value))
    helper._replace_dialog_edit=replace
    element=SimpleNamespace(pid=100)
    if readonly:
        with pytest.raises(BokkioError,match='writable'):
            helper.set_value(element,'result.txt',200,expected_runtime_id=[1])
        assert not writes
    else:
        assert helper.set_value(element,'result.txt',200,expected_runtime_id=[1])=={'write_source':'Win32.EM_REPLACESEL'}
        assert writes==[(101,200,'result.txt')]
        native.CurrentProcessId=101
        with pytest.raises(BokkioError,match='identity changed'):
            helper.set_value(element,'other.txt',200,expected_runtime_id=[1])
        assert len(writes)==1
    assert not pattern_writes


@pytest.mark.parametrize('inside', [False, True])
def test_dialog_messages_reject_other_windows_and_stop_on_selection_timeout(monkeypatch, inside):
    import ctypes
    from types import SimpleNamespace
    from bokkio.windows_uia import WindowsUIA
    from bokkio.model import BokkioError
    calls=[]
    def send(*args):
        calls.append(args[1]);return 0
    def child(*args):return inside
    monkeypatch.setattr(ctypes,'WinDLL',lambda *_args,**_kwargs:SimpleNamespace(IsChild=child,SendMessageTimeoutW=send),raising=False)
    helper=object.__new__(WindowsUIA)
    with pytest.raises(BokkioError,match='selection timed out' if inside else 'outside its observed dialog'):
        helper._replace_dialog_edit(101,200,'output.txt',lambda:None)
    assert calls==([0xB1] if inside else [])


def test_empty_document_value_and_readonly_capabilities():
    editor = Element("web_area", "Text Editor")
    editor.raw = {"control_type_id": 50030, "class_name": "Edit"}
    editor.actions = ["set_value", "focus"]
    readonly = Element("text_field", "Read only", "fixed")
    readonly.actions = ["set_value", "type_text"]
    b = backend([editor, readonly], Native())
    node = b.find("app", "text_area")[0]
    assert node["value"] == "" and node["state"]["editable"]
    assert "type" in node["actions"]
    assert b.perform("app", "set_value", ref=node["ref"], value="")["verification"] == "confirmed"
    with pytest.raises(BokkioActionError, match="not advertised"):
        b.perform("app", "set_value", role="text_field", name="Read only", value="modified")
    assert readonly.value == "fixed"


def test_failed_native_read_remains_unknown():
    class Failed(Native):
        def value(self, _): raise RuntimeError("provider unavailable")
    b = backend([Element("text_field", "Empty")], Failed())
    node = b.find("app", "text_field")[0]
    assert node["value"] is None
    assert node["platform_data"]["value_read_error"] == "provider unavailable"
    assert not ({"set_value", "type"} & set(node["actions"]))


@pytest.mark.parametrize("pattern", [None, {"available": False}])
def test_unproven_value_pattern_does_not_inherit_provider_editable_guess(pattern):
    class Unproven(Native):
        def value(self, element): return pattern
    prop = Element("text_field", "Name", "file.txt")
    prop.editable = True
    prop.actions = ["set_value"]
    b = backend([prop], Unproven())
    node = b.find("app", "text_field")[0]
    assert not ({"set_value", "type"} & set(node["actions"]))
    with pytest.raises(BokkioActionError, match="not advertised"):
        b.perform("app", "set_value", ref=node["ref"], value="unexpected")
    assert prop.value == "file.txt"


def test_value_probe_and_write_use_the_observed_window_scope():
    seen = []
    class Scoped(Native):
        def scoped_value(self, element, hwnd):
            seen.append(("read", hwnd))
            return self.value(element)
        def set_value(self, element, value, hwnd):
            seen.append(("write", hwnd)); element.value = value
    prop = Element("text_field", "File name:", "")
    b = backend([prop], Scoped())
    b._resolve_app("app").window.stable_id = "hwnd:0x1234"
    node = b.find("app", "text_field")[0]
    assert node["platform_data"]["value_scope_hwnd"] == 0x1234
    assert b.perform("app", "set_value", ref=node["ref"], value="output.txt")["verification"] == "confirmed"
    assert ("write", 0x1234) in seen


def test_editable_combo_routes_text_choices_to_its_single_editor():
    editor=Element('text_field','File name:',''); editor.editable=True
    combo=Element('combo_box','File name:','',children=[editor]); combo.actions=['set_value','expand']
    b=backend([combo],Native())
    wrapper=b.find('app','combo_box')[0]
    child=b.find('app','text_field')[0]
    assert 'set_value' not in wrapper['actions'] and 'expand' in wrapper['actions']
    assert wrapper['platform_data']['text_write_target']==child['ref']
    assert 'set_value' in child['actions']


def test_pid_binding_avoids_rediscovery_but_observes_fresh_window_contents():
    current=App(Element('window','Fixture',children=[Element('button','Before')]))
    calls=[]
    class Apps:
        @staticmethod
        def by_pid(pid,timeout): calls.append(pid); return current
    class Module: App=Apps
    b=Xa11yBackend(Module,platform='windows')
    assert b.snapshot('100')['windows']
    current.window.children_values=[Element('button','After')]
    assert any(n['name']=='After' for n in flatten(b.snapshot('100')['windows']))
    assert calls==[100]


def test_ambiguous_wrapper_only_allows_identity_checked_native_value_write():
    from bokkio.decision import options
    class Scoped(Native):
        def scoped_value(self, element, hwnd):
            return {**self.value(element), 'runtime_id':[42,1]}
        def set_value(self, element, value, hwnd, expected_runtime_id):
            assert expected_runtime_id==[42,1]
            element.value=value
    fields=[Element('text_field','Search',''),Element('text_field','Search','')]
    for f in fields:f.actions=['set_value','focus'];f.focusable=True
    b=backend(fields,Scoped());s=b.snapshot('app')
    choices=options(s,['*.png'])
    writes=[c for c in choices.values() if c['action']=='set_value']
    assert len(writes)==1
    assert not any(c['action'] in {'focus','type'} for c in choices.values())
    from bokkio.model import tree_digest
    b.perform('app','set_value',ref=writes[0]['ref'],value='*.png',expected_snapshot=tree_digest(s['windows']))


def test_ambiguous_ancestor_allows_only_verified_direct_native_action():
    from bokkio.decision import options
    from bokkio.model import tree_digest
    calls=[]
    class Direct(Native):
        def action_capabilities(self, element, hwnd):
            return {'runtime_id':[42,1], 'actions':['expand'], 'state':{}}
        def perform_action(self, element, action, hwnd, identity):
            assert action=='expand' and hwnd==0x100 and identity==[42,1]
            element.expanded=True; calls.append(action)
            return {'action_source':'UIA.ExpandCollapsePattern'}
    buttons=[Element('button','View'),Element('button','View')]
    for button in buttons:
        button.actions=['expand','focus']; button.expanded=False
        button.expand=lambda:pytest.fail('must use verified native dispatch')
    groups=[Element('group',None,children=[button]) for button in buttons]
    b=backend(groups,Direct()); b._resolve_app('app').window.stable_id='hwnd:0x100'
    snapshot=b.snapshot('app'); choices=options(snapshot,[])
    expansions=[c for c in choices.values() if c['action']=='expand']
    assert len(expansions)==1 and not any(c['action']=='focus' for c in choices.values())
    result=b.perform('app','expand',ref=expansions[0]['ref'],expected_snapshot=tree_digest(snapshot['windows']))
    assert calls==['expand'] and result['action_source']=='UIA.ExpandCollapsePattern'


def test_nonambiguous_toggle_menu_reads_native_state_and_dispatches_verified_toggle():
    from bokkio.agent import verify_conditions
    class Toggle(Native):
        def action_capabilities(self, element, hwnd):
            return {'runtime_id':[42,1],'actions':['click'],'state':{'checked':element.native_checked}}
        def perform_action(self, element, action, hwnd, identity):
            element.native_checked=not element.native_checked
            return {'action_source':'UIA.TogglePattern'}
    menu=Element('menu_item','File name extensions');menu.actions=['press','toggle']
    menu.checked=None;menu.native_checked=True
    b=backend([menu],Toggle());b._resolve_app('app').window.stable_id='hwnd:0x100'
    node=b.find('app','menu_item')[0]
    assert node['state']['checked'] is True
    result=b.perform('app','click',ref=node['ref'])
    assert result['action_source']=='UIA.TogglePattern'
    check={'role':'menu_item','name':'File name extensions','field':'checked','equals':False}
    assert verify_conditions(b.snapshot('app'),[check])[0]


@pytest.mark.parametrize('changed,enabled,available', [(True,True,True),(False,False,True),(False,True,False),(False,True,True)])
def test_direct_native_action_rechecks_identity_enabled_and_pattern(changed, enabled, available):
    from types import SimpleNamespace
    from bokkio.windows_uia import WindowsUIA
    from bokkio.model import BokkioError
    calls=[]; helper=object.__new__(WindowsUIA)
    helper._element=lambda *_:SimpleNamespace(GetRuntimeId=lambda:[2 if changed else 1],CurrentIsEnabled=enabled)
    helper._pattern=lambda *_:SimpleNamespace(Expand=lambda:calls.append('expand')) if available else None
    if changed or not enabled or not available:
        with pytest.raises(BokkioError):helper.perform_action(None,'expand',100,[1])
        assert not calls
    else:
        assert helper.perform_action(None,'expand',100,[1])=={'action_source':'UIA.ExpandCollapsePattern'}
        assert calls==['expand']


def test_value_alias_verification_requires_same_native_identity_and_readback():
    from bokkio.agent import verify_conditions
    fields=[Element('text_field','Search','*.png'),Element('text_field','Search','*.png')]
    b=backend(fields,Native());s=b.snapshot('app')
    check={'role':'text_field','name':'Search','field':'value','equals':'*.png'}
    assert not verify_conditions(s,[check])[0]
    for n in flatten(s['windows']):
        if n['name']=='Search':n['platform_data'].update(value_runtime_id=[42,1],value_scope_hwnd=100)
    assert verify_conditions(s,[check])[0]
    aliases=[n for n in flatten(s['windows']) if n['name']=='Search']
    aliases[1]['value']='other'
    assert not verify_conditions(s,[check])[0]


def test_hwnd_refs_survive_duplicate_reorder_and_reject_rebuild():
    a, z = Element("button", "Duplicate"), Element("button", "Duplicate")
    a.stable_id, z.stable_id = "hwnd:0x11", "hwnd:0x22"
    b = backend([a, z]); window = b._resolve_app("app").window
    original = b.find("app", "button")
    window.children_values.reverse()
    b.perform("app", "click", ref=original[0]["ref"])
    assert a.value == "pressed" and z.value is None
    a.stable_id = "hwnd:0x33"
    with pytest.raises(BokkioLookupError) as error:
        b.perform("app", "click", ref=original[0]["ref"])
    assert error.value.code == "stale_ref"


@pytest.mark.parametrize("direction,coordinate", [("right", "x"), ("down", "y")])
def test_windows_scroll_uses_container_pattern_and_content_readback(direction, coordinate):
    content = Element("group", "Content", children=[Element("button", "Item")])
    content.scroll = {a: {"scrollable": True, "position": 0.0, "view_size": 0.3} for a in ("x", "y")}
    content.scroll["source"] = "UIA.ScrollPattern"
    b = backend([content], Native())
    result = b.perform("app", "scroll", role="button", name="Item", direction=direction)
    assert result["verification"] == "confirmed"
    assert result["scroll"]["axis"] == coordinate
    assert result["scroll"]["content_nodes_moved"] == 1
    # A lying position alone is insufficient to confirm content scrolling.
    b._native.scroll = lambda element, axis, position: element.scroll[axis].update(position=position)
    result = b.perform("app", "scroll", role="group", name="Content", direction=direction)
    assert result["verification"] == "unconfirmed"
    assert result["scroll"]["reason"] == "content_movement_unconfirmed"


def test_nested_windows_remain_in_tree_but_not_window_inventory():
    nested = Element("window", "Title bar")
    b = backend([nested]); snapshot = b.snapshot("app")
    assert [w["name"] for w in b.windows("app")] == ["Fixture"]
    assert any(n["name"] == "Title bar" for n in flatten(snapshot["windows"]))
    with pytest.raises(Exception, match="Window not found"):
        b.snapshot("app", "control_type")


def test_expand_collapse_verify_actual_state():
    item = Element("tree_item", "Parent"); item.expanded = False
    item.actions = ["expand", "collapse"]
    item.expand = lambda: setattr(item, "expanded", True)
    item.collapse = lambda: None
    b = backend([item])
    assert b.perform("app", "expand", role="tree_item", name="Parent")["verification"] == "confirmed"
    assert b.perform("app", "collapse", role="tree_item", name="Parent")["verification"] == "unconfirmed"


def test_provider_cycle_fails_with_bounded_error():
    cyclic = Element("group", "Cycle")
    cyclic.children_values = [cyclic]
    b = backend([cyclic])
    from bokkio.model import BokkioError
    with pytest.raises(BokkioError, match="64 levels"):
        b.snapshot("app")


def test_range_pattern_does_not_advertise_string_set_value():
    class RangeOnly(Native):
        def value(self, element): return {"available": False}
    slider = Element("slider", "Volume"); slider.actions = ["set_value"]
    b = backend([slider], RangeOnly())
    assert "set_value" not in b.find("app", "slider")[0]["actions"]
    with pytest.raises(BokkioActionError, match="not advertised"):
        b.perform("app", "set_value", role="slider", value="10")


def test_partial_virtual_tree_materialization_invalidates_disappeared_ref():
    class Materialized(Native):
        def scroll(self, element, axis, position):
            element.scroll[axis]["position"] = position
            element.children_values = [Element("list_item", "Row 11"), Element("list_item", "Row 12")]
    area = Element("list", "Virtual", children=[Element("list_item", "Row 1"), Element("list_item", "Row 2")])
    area.scroll = {"source": "UIA.ScrollPattern", "x": {"scrollable": False, "position": 0, "view_size": 1},
                   "y": {"scrollable": True, "position": 0, "view_size": 0.2}}
    b = backend([area], Materialized())
    old = b.find("app", "list_item", "Row 1")[0]["ref"]
    result = b.perform("app", "scroll", role="list", name="Virtual", direction="down")
    assert result["verification"] == "confirmed"
    assert result["scroll"]["content_refs_changed"] == 4
    with pytest.raises(BokkioLookupError) as error:
        b.perform("app", "select", ref=old)
    assert error.value.code == "stale_ref"
