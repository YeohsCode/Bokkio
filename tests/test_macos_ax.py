from types import SimpleNamespace
import pytest
from bokkio.macos_ax import MacAX
from bokkio.model import BokkioActionError
from bokkio.decision import options
from bokkio.xa11y_backend import Xa11yBackend
from test_cli import App,Element,FakeXa11y


def native_call(actions,error=0):
    native=MacAX.__new__(MacAX);native._owned=[]
    calls=[]
    native._targets={'target':(123,456,actions,10)}
    native._string=lambda text:text
    native.cf=SimpleNamespace(CFRelease=lambda p:None)
    native.ax=SimpleNamespace(AXUIElementPerformAction=lambda element,key:calls.append(key) or error)
    node={'ref':'target','platform_data':{'ax_native_identity':456,'mac_verified_actions':['click','submit','expand']}}
    return native,node,calls


def test_confirm_is_dispatched_once_without_press_retry():
    native,node,calls=native_call(['AXConfirm'])
    assert native.perform(node,'click')['action_source']=='AXConfirm'
    assert calls==['AXConfirm']
    native,node,calls=native_call(['AXPress','AXConfirm'])
    assert native.perform(node,'click')['action_source']=='AXPress'
    assert calls==['AXPress']


def test_expired_capability_read_stops_before_native_ipc(monkeypatch):
    from bokkio import macos_ax
    from bokkio.model import BokkioError
    native=MacAX.__new__(MacAX);native._owned=[];native._deadline=1
    native.ax=SimpleNamespace(AXUIElementSetMessagingTimeout=lambda *a:pytest.fail('expired read must stop'))
    monkeypatch.setattr(macos_ax.time,'monotonic',lambda:2)
    with pytest.raises(BokkioError,match='time budget'):native._attr(123,'AXTitle')


def test_numeric_ax_value_refuses_string_setter_before_dispatch():
    native,node,calls=native_call(['AXConfirm']);node['platform_data']['mac_verified_actions']=['set_value']
    native._attr=lambda *args:789
    native.cf.CFGetTypeID=lambda value:2;native.cf.CFNumberGetTypeID=lambda:2
    native.ax.AXUIElementSetAttributeValue=lambda *args:pytest.fail('numeric type must not be overwritten')
    with pytest.raises(BokkioActionError,match='change their native type'):native.perform(node,'set_value','1.15')
    assert calls==[]


def test_post_input_observation_failure_is_unknown_without_second_press(monkeypatch):
    from bokkio.model import BokkioError,BokkioCompletionUnknown
    from bokkio.selector import flatten
    button=Element('button','Save');button.actions=['press'];window=Element('window','Owned')
    window.children_values=[button];module=FakeXa11y();module.current=App(window)
    backend=Xa11yBackend(module=module,platform='macos');app=str(module.current.pid)
    monkeypatch.setattr(backend,'_resolve_app',lambda _:module.current)
    snapshot=backend.snapshot(app)
    ref=next(n['ref'] for n in flatten(snapshot['windows']) if n['name']=='Save')
    original=backend._app_tree;reads=[];presses=[]
    def tree(*args,**kwargs):
        reads.append(True)
        if len(reads)>1:raise BokkioError('AXWindows temporarily unreachable')
        return original(*args,**kwargs)
    monkeypatch.setattr(backend,'_app_tree',tree);monkeypatch.setattr(button,'press',lambda:presses.append(True))
    with pytest.raises(BokkioCompletionUnknown,match='fresh native observation failed'):
        backend.perform(app,'click',ref=ref)
    assert presses==[True] and len(reads)==2


def test_native_sibling_labels_name_only_uniquely_bound_fields():
    from bokkio.model import stable_hash
    def node(role,name,x,y,width=100,bound=False):
        return {'ref':stable_hash([role,name,x,y]),'role':role,'name':name,'children':[],
                'bounds':{'x':x,'y':y,'width':width,'height':20},
                'platform_data':{'mac_unique_identity':bound},'actions':[]}
    label=node('static_text','Latin text font:',0,0)
    field=node('combo_box',None,0,26,bound=True)
    unbound=node('combo_box',None,120,26)
    root={'children':[label,field,node('static_text','Size:',120,0),unbound]}
    MacAX._label_fields(root)
    assert field['name']=='Latin text font:' and field['actions']==[]
    assert unbound['name'] is None
    duplicate=node('combo_box',None,0,26,bound=True);duplicate['ref']='duplicate'
    field['name']=None;root['children'].append(duplicate)
    MacAX._label_fields(root)
    assert field['name'] is None and duplicate['name'] is None


def test_hidden_menu_command_requires_unique_native_binding_and_enabled_state():
    node={'ref':'menu','platform':'macos','role':'menu_item','name':'Font...','value':None,
          'state':{'visible':False,'enabled':True},'children':[],'actions':['click'],
          'platform_data':{'native_menu_command':True,'mac_unique_identity':True,'mac_verified_actions':['click']}}
    assert len(options({'windows':[node]},[]))==2
    node['platform_data']['mac_unique_identity']=False
    assert len(options({'windows':[node]},[]))==1
    node['platform_data']['mac_unique_identity']=True;node['state']['enabled']=False
    assert len(options({'windows':[node]},[]))==1


def test_ephemeral_menu_handles_do_not_invalidate_identical_semantic_state():
    import copy
    from bokkio.model import tree_digest
    node={'platform':'macos','role':'menu_item','name':'Left of Screen','value':None,'children':[],
          'state':{'enabled':True},'platform_data':{'native_menu_attribute':True,'ax_native_identity':123}}
    other=copy.deepcopy(node);other['platform_data']['ax_native_identity']=456
    assert tree_digest([node])==tree_digest([other])
    assert node['platform_data']['ax_native_identity']==123
    other['state']['enabled']=False
    assert tree_digest([node])!=tree_digest([other])
    other=copy.deepcopy(node);other['name']='Different command'
    assert tree_digest([node])!=tree_digest([other])
    other=copy.deepcopy(node);other['platform_data']['native_menu_attribute']=False
    assert tree_digest([node])!=tree_digest([other])


def test_attribute_menu_dispatch_uses_bound_native_object_without_xa11y_alias():
    from bokkio.selector import flatten
    window=Element('window','Owned');module=FakeXa11y();module.current=App(window)
    calls=[]
    class Native:
        def annotate(self,tree,pid):
            item={'ref':'native-menu','role':'menu_item','name':'Format','value':None,'bounds':None,
                  'children':[],'parent':tree['ref'],'state':{'enabled':True,'visible':True},
                  'actions':['click'],'platform':'macos',
                  'platform_data':{'mac_unique_identity':True,'mac_verified_actions':['click']}}
            tree['children'].append(item);return tree
        def perform(self,node,action,value):
            calls.append((node['ref'],action));return {'action_source':'AXPress'}
    backend=Xa11yBackend(module,platform='macos',native=Native());backend._resolve_app=lambda app:module.current
    result=backend.perform('100','click',ref='native-menu')
    assert calls==[('native-menu','click')] and result['action_source']=='AXPress'


def test_native_error_and_stale_binding_never_try_another_action():
    native,node,calls=native_call(['AXConfirm'],error=-25205)
    with pytest.raises(BokkioActionError,match='completion requires fresh'):native.perform(node,'click')
    assert calls==['AXConfirm']
    node['platform_data']['ax_native_identity']=999
    with pytest.raises(BokkioActionError,match='no longer bound'):native.perform(node,'click')
    assert calls==['AXConfirm']


def test_native_selection_uses_utf16_and_reads_selected_text():
    text=Element('text_area','Content','A😀B title');text.editable=True
    window=Element('window','Owned',children=[text]);module=FakeXa11y();module.current=App(window)
    calls=[]
    def select(start,end):
        calls.append((start,end));text.selected_literal='😀B'
    text.select_text=select
    class Native:
        def annotate(self,tree,pid):
            from bokkio.selector import flatten
            for n in flatten([tree]):
                if n['role']=='text_area':
                    n['actions'].append('select_text')
                    n['platform_data'].update(mac_unique_identity=True,mac_verified_actions=['select_text'])
                    n['state']['selected_text']=getattr(text,'selected_literal','')
            return tree
        def perform(self,*args):pytest.fail('range dispatch must use live xa11y object')
    backend=Xa11yBackend(module,platform='macos',native=Native());backend._resolve_app=lambda app:module.current
    result=backend.perform('100','select_text',role='text_area',name='Content',value='😀B')
    assert calls==[(1,4)] and result['verification']=='confirmed'
    text.value='repeat repeat'
    with pytest.raises(BokkioActionError,match='one exact'):backend.perform('100','select_text',role='text_area',name='Content',value='repeat')
    assert calls==[(1,4)]
    text.enabled=False
    text.value='A😀B title'
    assert backend.perform('100','select_text',role='text_area',name='Content',value='😀B')['verification']=='confirmed'
    assert calls==[(1,4),(1,4)]
    with pytest.raises(BokkioActionError,match='disabled'):backend.perform('100','set_value',role='text_area',name='Content',value='changed')
    assert text.value=='A😀B title'


def test_ambiguous_mac_target_needs_unique_native_identity():
    node={'ref':'x','platform':'macos','role':'combo_box','name':'Address','value':'A1','state':{'enabled':True,'visible':True},
          'children':[],'actions':['set_value','submit'],'platform_data':{'ambiguous_ref_identity':True,'mac_verified_actions':['set_value','submit']}}
    snapshot={'windows':[node]}
    assert len(options(snapshot,['D1:D6']))==1
    node['platform_data']['mac_unique_identity']=True
    assert {c['action'] for c in options(snapshot,['D1:D6']).values()}=={'done','set_value','submit'}
    node['state']['enabled']=False
    assert len(options(snapshot,['D1:D6']))==1


def test_success_validation_rejects_invented_role_or_parent():
    from bokkio.planner import validate_plan
    from bokkio.model import BokkioError
    observations={'100':{'windows':[{'name':'Owned'}],'nodes':[{'role':'combo_box','name':'name box','parent_name':'Owned','state':{},'actions':['set_value','submit']}]}}
    step={'id':'address','app':'100','window':None,'goal':'Enter range','risk':'local_write','allowed_values':['D:D'],
          'success':[{'role':'text_field','name':'name box','field':'value','equals':'D:D'}]}
    plan={'goal':'Format','steps':[step]}
    with pytest.raises(BokkioError,match='role differs'):validate_plan(plan,['100'],observations)
    step['success'][0].update(role='combo_box',parent_name='invented')
    with pytest.raises(BokkioError,match='parent_name differs'):validate_plan(plan,['100'],observations)
    step['success'][0]['parent_name']=None
    assert validate_plan(plan,['100'],observations)==plan


def test_small_planning_tree_keeps_editor_beside_generic_save_match():
    from bokkio.agent import planner_observation
    editor=Element('text_area','Page content','Synthetic document');editor.editable=True
    save=Element('button','Save');window=Element('window','Owned',children=[editor,save])
    module=FakeXa11y();module.current=App(window)
    backend=Xa11yBackend(module);backend._resolve_app=lambda app:module.current
    observed=planner_observation('Format the document and Save',backend.snapshot('100'),[{'name':'Owned'}])
    assert observed['observation_scope']['strategy']=='full'
    assert any(n['name']=='Page content' for n in observed['nodes'])


def test_planner_sees_proven_mac_actions_even_with_structural_ambiguity():
    from bokkio.agent import planner_observation
    from bokkio.selector import flatten
    editor=Element('text_area','Content','Owned');editor.enabled=False
    window=Element('window','Owned',children=[editor]);module=FakeXa11y();module.current=App(window)
    backend=Xa11yBackend(module);backend._resolve_app=lambda app:module.current
    snapshot=backend.snapshot('100');node=next(n for n in flatten(snapshot['windows']) if n['name']=='Content')
    node['platform_data'].update(ambiguous_ref_identity=True,mac_unique_identity=True,mac_verified_actions=['select_text'])
    node['actions']=['set_value','select_text','focus']
    observed=planner_observation('Select text',snapshot,[{'name':'Owned'}])
    assert next(n for n in observed['nodes'] if n['name']=='Content')['actions']==['select_text']


def test_unknown_native_completion_blocks_without_replanning(tmp_path):
    from bokkio.agent import DesktopAgent
    from bokkio.model import BokkioCompletionUnknown
    from test_agent import Planner,Provider
    from test_cli import backend_with_button
    backend,_,_=backend_with_button();calls=[]
    def perform(*args,**kwargs):
        calls.append(True);raise BokkioCompletionUnknown('AX call returned an error')
    backend.perform=perform;planner=Planner()
    trace=DesktopAgent(backend,planner,Provider()).run('Click Save',['TextEdit'],tmp_path/'trace.json')
    assert trace['status']=='blocked' and trace['replans']==0
    assert len(calls)==len(planner.calls)==1
    assert 'completion is unknown' in trace['events'][-1]['reason']


def test_unknown_completion_can_be_resolved_by_new_conditions_without_reposting(tmp_path):
    from bokkio.agent import DesktopAgent
    from bokkio.model import BokkioCompletionUnknown
    from test_agent import Planner,Provider
    from test_cli import backend_with_button
    backend,_,button=backend_with_button();calls=[]
    def perform(*args,**kwargs):
        calls.append(True);button.value='pressed';raise BokkioCompletionUnknown('Native receipt unavailable')
    backend.perform=perform
    trace=DesktopAgent(backend,Planner(),Provider()).run('Click Save',['TextEdit'],tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['actions']==1 and len(calls)==1 and trace['replans']==0
    assert any(e['kind']=='unknown_completion_observed' and e['resolved'] and not e['input_reposted'] for e in trace['events'])


def test_selection_receipt_can_be_saved_as_workflow():
    from bokkio.workflow import auto_checks,make_workflow
    node={'role':'text_area','name':'Content','state':{'selected_text':'literal'}}
    checks=auto_checks({'action':'select_text','after':node,'postcondition':{'expected':'literal'}})
    assert checks[0]['field']=='selected_text' and checks[0]['equals']=='literal'
    step={'id':'s1','app':'owned','intent':'Select literal','action':'select_text',
          'target':{'ref':'x','role':'text_area','name':'Content','ancestors':[{'role':'window','name':'Owned'}]},
          'arguments':{'value':'literal'},'wait':[],'verify':checks,'depends_on':[],'risk':'read'}
    assert make_workflow('Selection',[step],{})['steps'][0]['arguments']=={'value':'literal'}


def test_combo_value_is_not_completed_before_native_confirmation(tmp_path):
    from bokkio.agent import DesktopAgent
    from test_agent import Provider
    combo=Element('combo_box','Number Format','General');combo.actions=['set_value']
    window=Element('window','Owned',children=[combo]);module=FakeXa11y();module.current=App(window)
    committed=[]
    class Native:
        def annotate(self,tree,pid):
            from bokkio.selector import flatten
            for n in flatten([tree]):
                if n['name']=='Number Format':
                    n['actions']=['set_value','submit']
                    n['platform_data'].update(mac_unique_identity=True,mac_verified_actions=['set_value','submit'])
            return tree
        def perform(self,node,action,value):
            if action=='set_value':combo.value=value
            else:committed.append(combo.value)
            return {'action_source':'AXValue' if action=='set_value' else 'AXConfirm'}
    backend=Xa11yBackend(module,platform='macos',native=Native());backend._resolve_app=lambda app:module.current
    class Planner:
        def __init__(self):self.calls=[]
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            if progress:
                assert progress['native_combo_value_written']['name']=='Number Format'
                assert progress['completed_steps']==[]
                step={'id':'commit','app':'100','window':None,'goal':'Confirm Number Format with submit','allowed_values':[],'requires_action':True,
                      'risk':'local_write','success':[{'role':'combo_box','name':'Number Format','field':'focused','equals':False}]}
            else:
                step={'id':'set','app':'100','window':None,'goal':'Set Number Format to Currency','allowed_values':['Currency'],'requires_action':True,
                      'risk':'local_write','success':[{'role':'combo_box','name':'Number Format','field':'value','equals':'Currency'}]}
            return {'goal':goal,'steps':[step]},{}
    planner=Planner()
    # A closed-choice provider chooses the only advertised operation at each
    # stage; the submit stage has been bounded to the explicit native target.
    class Choice:
        def ask(self,state,questions):
            answers={}
            for name,q in questions.items():
                keys=list(q['criteria']);selected='set_value' if name=='next' and 'set_value' in keys else keys[0]
                answers[name]={'type':'noul','noul':0} if q['type']=='noul' else {'type':'choice','choice':selected,'confidence':1,'probabilities':{k:float(k==selected) for k in keys}}
            return {'answers':answers}
    trace=DesktopAgent(backend,planner,Choice()).run('Apply currency',['100'],tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['actions']==2
    assert committed==['Currency'] and len(planner.calls)==2


def test_office_stale_refresh_is_bounded_without_consuming_replan(tmp_path):
    from bokkio.agent import DesktopAgent
    from test_agent import Planner,Provider
    from test_cli import backend_with_button
    backend,_,button=backend_with_button();backend.supports_stale_refresh=True;planner=Planner()
    class Changing(Provider):
        changed=False
        def ask(self,state,questions):
            response=super().ask(state,questions)
            if not self.changed:button.value='external badge';self.changed=True
            return response
    trace=DesktopAgent(backend,planner,Changing()).run('Click Save',['TextEdit'],tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['replans']==0 and trace['actions']==2
    assert any(e['kind']=='stale_decision_rejected' and e['dispatched'] is False for e in trace['events'])


def test_selection_literal_binding_is_readonly_and_uses_observed_text(tmp_path):
    import copy
    from bokkio.agent import DesktopAgent
    text=Element('text_area','Content','before literal after');text.actions=[];text.editable=False
    window=Element('window','Owned',children=[text]);module=FakeXa11y();module.current=App(window)
    def select(start,end):text.chosen='literal'
    text.select_text=select
    class Native:
        def annotate(self,tree,pid):
            from bokkio.selector import flatten
            for n in flatten([tree]):
                if n['name']=='Content':
                    n['actions']=['select_text'];n['state']['selected_text']=getattr(text,'chosen','')
                    n['platform_data'].update(mac_unique_identity=True,mac_verified_actions=['select_text'])
            return tree
        def perform(self,*a):pytest.fail('only read-only selection is allowed')
    backend=Xa11yBackend(module,platform='macos',native=Native());backend._resolve_app=lambda app:module.current
    raw={'goal':'Select literal','steps':[{'id':'select','app':'100','window':None,'goal':'Select literal in Content','allowed_values':[],
            'requires_action':True,'risk':'read','success':[{'role':'text_area','name':'Content','field':'selected_text','equals':'literal'}]}]}
    class Planner:
        def plan(self,*args):return copy.deepcopy(raw),{}
    class Choice:
        def ask(self,state,questions):
            answers={}
            for name,q in questions.items():
                keys=list(q['criteria']);first=keys[0]
                answers[name]={'type':'noul','noul':0} if q['type']=='noul' else {'type':'choice','choice':first,'confidence':1,'probabilities':{k:float(k==first) for k in keys}}
            return {'answers':answers}
    trace=DesktopAgent(backend,Planner(),Choice()).run('Select literal',['100'],tmp_path/'trace.json')
    assert trace['status']=='completed' and text.value=='before literal after'
    assert trace['plan']['steps'][0]['allowed_values']==['literal']
    proposal=next(e['plan'] for e in trace['events'] if e['kind']=='plan_proposal')
    assert proposal['steps'][0]['allowed_values']==[]


@pytest.mark.parametrize('selection_error',[0,-25205])
def test_readonly_option_selects_then_confirms_owning_combo_once(monkeypatch,selection_error):
    from bokkio import macos_ax
    from bokkio.model import BokkioCompletionUnknown
    native,node,calls=native_call(['AXConfirm'])
    node['platform_data'].update(mac_verified_actions=['select'],mac_selection_source='AXSelected_then_combo_confirm')
    monkeypatch.setattr(macos_ax,'c',SimpleNamespace(c_void_p=SimpleNamespace(in_dll=lambda *a:SimpleNamespace(value=1))))
    native.ax.AXUIElementSetAttributeValue=lambda element,key,value:calls.append(('select',element,key)) or selection_error
    native._attr=lambda element,key:789
    native._text=lambda ptr:'AXComboBox'
    native._actions=lambda element:['AXConfirm']
    if selection_error:
        with pytest.raises(BokkioCompletionUnknown):native.perform(node,'select')
        assert calls==[('select',123,'AXSelected')]
    else:
        assert native.perform(node,'select')['action_source']=='AXSelected_then_owning_combo_AXConfirm'
        assert calls==[('select',123,'AXSelected'),'AXConfirm']


def test_snapshot_uses_fresh_native_foreground_instead_of_app_cache():
    module=FakeXa11y();module.current=App(Element('window','Owned'))
    class Native:
        def annotate(self,tree,pid):
            tree['platform_data']['ax_frontmost']=True
            return tree
    backend=Xa11yBackend(module,platform='macos',native=Native());backend._resolve_app=lambda app:module.current
    module.current.is_foreground=False
    assert backend.snapshot('100')['app']['is_foreground'] is True


def test_nested_macos_save_sheet_is_selectable_without_promoting_nested_windows():
    sheet=Element('dialog','Save');inner=Element('window','Title Bar')
    window=Element('window','Owned',children=[sheet,inner]);module=FakeXa11y();module.current=App(window)
    backend=Xa11yBackend(module,platform='macos');backend._resolve_app=lambda app:module.current
    assert [w['name'] for w in backend.snapshot('100','Save')['windows']]==['Save']
    with pytest.raises(Exception,match='Window not found'):backend.snapshot('100','Title Bar')


def test_semantic_digest_ignores_unnamed_status_help_but_binds_target_state():
    import copy
    from bokkio.model import tree_digest
    n={'platform':'macos','role':'button','name':'','value':None,'state':{'enabled':True},'bounds':{'x':1,'y':2,'width':3,'height':4},'actions':['click'],
       'platform_data':{'AXHelp':'old help','AXDescription':'proofing pending','description':'proofing pending','ax_native_identity':42}}
    original=tree_digest([n]);changed=copy.deepcopy(n);changed['platform_data'].update(AXHelp='new help',AXDescription='proofing ready',description='proofing ready')
    assert tree_digest([changed])==original
    for field,value in [('name','Language'),('bounds',{'x':10,'y':2,'width':3,'height':4}),('state',{'enabled':False})]:
        actual=copy.deepcopy(changed);actual[field]=value
        assert tree_digest([actual])!=original
    changed['platform_data']['ax_native_identity']=43
    assert tree_digest([changed])!=original


def test_readonly_text_selection_acquires_verified_focus_before_range():
    from bokkio.selector import flatten
    text=Element('text_area','Content','before literal after');text.actions=[];text.enabled=False;calls=[]
    text.focus=lambda:calls.append('focus')
    text.select_text=lambda start,end:calls.append(('range',start,end))
    window=Element('window','Owned',children=[text]);module=FakeXa11y();module.current=App(window)
    class Native:
        def perform(self,*args):pytest.fail('selection uses the bound live range')
        def annotate(self,tree,pid):
            for n in flatten([tree]):
                if n['name']=='Content':
                    n['actions']=['select_text'];n['platform_data'].update(mac_unique_identity=True,mac_verified_actions=['select_text'],ax_selection_focus_settable=True)
            return tree
    b=Xa11yBackend(module,platform='macos',native=Native());b._resolve_app=lambda app:module.current
    node=next(n for n in flatten(b.snapshot('100')['windows']) if n['name']=='Content')
    result=b.perform('100','select_text',ref=node['ref'],value='literal')
    assert calls==['focus',('range',7,14)] and text.value=='before literal after'
    assert result['action_source']=='AXFocused_then_AXSelectedTextRange'
