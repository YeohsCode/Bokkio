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
