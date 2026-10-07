import copy
import json
from io import BytesIO
import pytest
from bokkio.agent import DesktopAgent, file_control, verify_conditions, planner_observation
from bokkio.model import BokkioError
from bokkio.planner import OpenRouterPlanner, validate_plan
from test_cli import backend_with_button
from test_decision import Provider


def plan(risk="local_write"):
    return {"goal": "Click Save", "steps": [{"id": "save", "app": "TextEdit", "window": "Untitled", "goal": "Click Save", "allowed_values": [], "risk": risk,
        "success": [{"role": "button", "name": "Save", "field": "value", "equals": "pressed"}]}]}


class Planner:
    def __init__(self, result=None): self.result, self.calls = result or plan(), []
    def plan(self, goal, observations, progress=None):
        self.calls.append(progress)
        return copy.deepcopy(self.result), {"model": "offline"}


def test_required_command_cannot_be_skipped_by_an_already_true_predicate(tmp_path):
    backend,window,button=backend_with_button()
    button.value='pressed'
    calls=[]
    original=button.press
    def press():
        calls.append('native_command');original()
    button.press=press
    p=plan();p['steps'][0]['requires_action']=True
    result=DesktopAgent(backend,Planner(p),Provider(satisfied=1.0)).run('Click Save',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='completed' and result['actions']==1 and calls==['native_command']
    assert next(e['subtask'] for e in result['events'] if e['kind']=='action')==p['steps'][0]
    p['steps'][0]['requires_action']='yes'
    with pytest.raises(BokkioError,match='requires_action'):
        validate_plan(p,['TextEdit'])
    from bokkio.planner import plan_schema
    schema=plan_schema({'TextEdit':{'windows':[{'name':'Untitled'}]}})
    variant=schema['properties']['steps']['items']['anyOf'][0]
    assert variant['properties']['requires_action']=={'type':'boolean'}
    assert 'requires_action' in variant['required']


@pytest.mark.parametrize("reject_duplicate",[False,True])
def test_rename_editor_triggers_a_fresh_plan_instead_of_reinvoking_rename(tmp_path,reject_duplicate):
    from test_cli import Element
    backend,window,button=backend_with_button();button.name='Rename'
    editor=Element('text_field','Name','old.txt');editor.editable=True;editor.actions=['set_value']
    button.press=lambda:window.children_values.append(editor)
    opening={'id':'rename','app':'TextEdit','window':None,'goal':'Click Rename','allowed_values':[],
             'requires_action':True,'risk':'local_write',
             'success':[{'role':'text_field','name':'Name','field':'present','equals':True}]}
    writing={'id':'name','app':'TextEdit','window':None,'goal':'Set Name to new.txt','allowed_values':['new.txt'],
             'risk':'local_write','success':[{'role':'text_field','name':'Name','field':'value','equals':'new.txt'}]}
    class RenamePlanner(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            if progress is None:steps=[opening];continuing=True
            else:
                assert progress['native_inline_editor_opened']=='Rename'
                assert progress['new_editors'][0]['name']=='Name'
                if reject_duplicate and len(self.calls)==2:
                    return {'goal':goal,'steps':[opening],'continue_after_steps':True},{}
                steps=[writing];continuing=False
            return {'goal':goal,'steps':steps,'continue_after_steps':continuing},{}
    planner=RenamePlanner()
    trace=DesktopAgent(backend,planner,Provider()).run('Rename',['TextEdit'],tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['actions']==2 and trace['phases']==1
    assert editor.value=='new.txt' and len(planner.calls)==(3 if reject_duplicate else 2)
    assert trace['replans']==int(reject_duplicate)
    assert any(e.get('reason')=='native_inline_editor_opened' for e in trace['events'])


@pytest.mark.parametrize('sources', ['C:\\Task\\a.txt',['relative.txt'],['\\a.txt'],['C:\\Task\\a\0.txt']])
def test_source_constraints_require_full_paths(sources):
    backend,_,_=backend_with_button()
    with pytest.raises(BokkioError,match='absolute file paths'):
        DesktopAgent(backend,Planner(),Provider(),required_sources=sources)


def test_editor_write_is_rejected_before_any_required_source_is_acquired(tmp_path):
    from test_cli import Element
    backend,window,_=backend_with_button()
    editor=Element('text_area','Text Editor','');editor.editable=True;editor.actions=['set_value']
    window.children_values=[editor];editor.parent_value=window
    p={'goal':'Count', 'steps':[{'id':'write','app':'TextEdit','window':None,'goal':'Set Text Editor to 0',
        'allowed_values':['0'],'risk':'local_write',
        'success':[{'role':'text_area','name':'Text Editor','field':'value','equals':'0'}]}]}
    result=DesktopAgent(backend,Planner(p),Provider(),required_sources=[r'C:\Task\source.txt'],max_replans=0).run(
        'Count',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='blocked' and result['actions']==0 and editor.value==''
    assert 'Read the required sources' in result['events'][-1]['reason']


def test_native_source_guard_repairs_same_name_from_wrong_directory_and_binds_resume(tmp_path):
    from test_windows_native import backend as windows_backend, Native
    from test_cli import Element
    source=r'C:\Task\source.txt'
    field=Element('text_field','File name:','source.txt')
    open_button=Element('button','Open')
    dialog=Element('dialog','Open',children=[field,open_button])
    dialog.raw={'class_name':'#32770'};dialog.stable_id='hwnd:0x200'
    editor=Element('text_area','Text Editor','');editor.actions=['set_value'];editor.editable=True
    backend=windows_backend([dialog,editor],Native());window=backend._resolve_app('TextEdit').window
    def load():
        window.name='source - Notepad';window.children_values=[editor];editor.parent_value=window
        editor.value='example example'
    open_button.press=load
    def step(id,goal,role,name,field_name,value,values=()):
        return {'id':id,'app':'TextEdit','window':None,'goal':goal,'allowed_values':list(values),
                'risk':'local_write','success':[{'role':role,'name':name,'field':field_name,'equals':value}]}
    opening=step('open','Click Open','dialog','Open','present',False)
    class SourcePlanner(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            assert progress['required_sources']==[source]
            if len(self.calls)==1:
                steps=[opening];continuing=True
            elif len(self.calls)==2:
                assert 'full required source path' in progress['error']
                steps=[step('path','Set File name to the full source path','text_field','File name:','value',source,[source]),opening]
                continuing=True
            else:
                assert progress['missing_native_sources']==[]
                assert observations['TextEdit']['text_facts'][0]['word_counts']['example']['whole_word_case_sensitive']==2
                assert progress['native_sources'][0]['text_facts'][0]['word_counts']['example']['whole_word_case_sensitive']==2
                steps=[step('count','Set Text Editor to 2','text_area','Text Editor','value','2',['2'])]
                continuing=False
            return {'goal':goal,'steps':steps,'continue_after_steps':continuing},{}
    planner=SourcePlanner();path=tmp_path/'trace.json'
    result=DesktopAgent(backend,planner,Provider(),required_sources=[source]).run('Count the word "example"',['TextEdit'],path)
    assert result['status']=='completed' and result['actions']==3 and result['replans']==1
    assert editor.value=='2' and result['requirements'][0]['required_sources']==[source]
    acquired=[e for e in result['events'] if e['kind']=='source_acquired']
    assert len(acquired)==1 and acquired[0]['path']==source
    assert next(e for e in result['events'] if e['kind']=='error')['error'].startswith('Before native Open')
    with pytest.raises(BokkioError,match='source constraints'):
        DesktopAgent(backend,Planner(),Provider()).run('Count the word "example"',['TextEdit'],path,resume=path)
    # Even a current output equal to the new predicate cannot replace rereading
    # the required source for the new requirement revision.
    p={'goal':'Recount','steps':[step('count','Set Text Editor to 2','text_area','Text Editor','value','2',['2'])]}
    amended=DesktopAgent(backend,Planner(p),Provider(),required_sources=[source],max_replans=0).run(
        'Recount',['TextEdit'],path,resume=path,amend_reason='New source version')
    assert amended['status']=='blocked' and amended['goal_revision']==2
    assert amended['events'][-2]['evidence']['missing_native_sources']==[source]


@pytest.mark.parametrize('phase_budget,status',[(0,'blocked'),(1,'completed')])
def test_native_menu_toggle_refreshes_plan_before_using_changed_source(phase_budget,status,tmp_path):
    from test_cli import Element
    backend,window,_=backend_with_button()
    toggle=Element('menu_item','Extensions');toggle.actions=['press','toggle'];toggle.checked=False
    label=Element('static_text','Data','hidden')
    editor=Element('text_area','Text Editor','');editor.editable=True;editor.actions=['set_value']
    window.children_values=[toggle,label,editor]
    for child in window.children_values:child.parent_value=window
    def change():
        toggle.checked=True;label.value='full.png';window.children_values=[label,editor]
    toggle.press=change
    toggle_step={'id':'toggle','app':'TextEdit','window':None,'goal':'Click Extensions','allowed_values':[],
                 'risk':'local_write','success':[{'role':'menu_item','name':'Extensions','field':'present','equals':False}]}
    def write(value):
        return {'id':'write','app':'TextEdit','window':None,'goal':'Set Text Editor to the observed data',
                'allowed_values':[value],'risk':'local_write',
                'success':[{'role':'text_area','name':'Text Editor','field':'value','equals':value}]}
    class Changing(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            if progress is None:steps=[toggle_step,write('hidden')]
            else:
                assert progress['native_menu_changed']=='Extensions'
                value=next(n['value'] for n in observations['TextEdit']['nodes'] if n['name']=='Data')
                steps=[write(value)]
            return {'goal':goal,'steps':steps},{}
    result=DesktopAgent(backend,Changing(),Provider(),max_phases=phase_budget).run('Report the data',['TextEdit'],tmp_path/'trace.json')
    assert result['status']==status and editor.value==('full.png' if phase_budget else '')
    assert result['phases']==phase_budget


def test_explicit_amendment_replans_from_fresh_native_state_and_scopes_old_receipts(tmp_path):
    backend, window, button = backend_with_button()
    from test_cli import Element
    other = Element('button', 'Other'); other.parent_value = window
    window.children_values.append(other)
    p = plan(); last = copy.deepcopy(p['steps'][0]); last['id'] = 'last'
    last['goal'] = 'Click Other'; last['success'][0]['name'] = 'Other'
    p['steps'].append(last)
    planner = Planner(p); path = tmp_path/'trace.json'
    first = DesktopAgent(backend, planner, Provider()).run('Original request', ['TextEdit'], path)
    assert first['status'] == 'completed' and first['actions'] == 2
    history = copy.deepcopy(first['events'])
    button.value = other.value = 'changed'
    final = DesktopAgent(backend, planner, Provider()).run(
        'Revised request', ['TextEdit'], path, resume=path, amend_reason='User changed requirements')
    assert final['status'] == 'completed' and final['actions'] == 4
    assert final['goal_revision'] == 2 and final['events'][:len(history)] == history
    assert planner.calls[-1]['requirement_change']['previous_goal'] == 'Original request'
    assert not any(e['kind'] == 'subtask_retained' and e['goal_revision'] == 2 for e in final['events'])
    assert [r['goal'] for r in final['requirements']] == ['Original request', 'Revised request']
    assert button.value == other.value == 'pressed'


@pytest.mark.parametrize('status,reason,new_goal', [
    ('running','change','New'), ('failed','change','New'), ('cancelled','change','New'),
    ('paused','','New'), ('paused','change','Click Save'),
])
def test_invalid_amendment_cannot_overwrite_checkpoint_or_dispatch(tmp_path, status, reason, new_goal):
    backend, _, button = backend_with_button(); path = tmp_path/'trace.json'
    p = {'goal':'Click Save', 'apps':['TextEdit'], 'events':[], 'completed_steps':[],
         'actions':0, 'replans':0, 'status':status}
    path.write_text(json.dumps(p)); before = path.read_bytes()
    with pytest.raises(BokkioError, match='Requirement amendment'):
        DesktopAgent(backend, Planner(), Provider()).run(new_goal, ['TextEdit'], path, resume=path, amend_reason=reason)
    assert path.read_bytes() == before and button.value is None


def test_amendment_cannot_expand_app_scope_or_reset_action_budget(tmp_path):
    backend, _, button = backend_with_button(); path=tmp_path/'trace.json'
    agent=DesktopAgent(backend, Planner(), Provider(), max_actions=1)
    agent.run('Click Save', ['TextEdit'], path)
    with pytest.raises(BokkioError, match='allowlist'):
        agent.run('New request', ['TextEdit','Other'], path, resume=path, amend_reason='change')
    button.value='changed'
    result=agent.run('New request', ['TextEdit'], path, resume=path, amend_reason='change')
    assert result['status']=='blocked' and result['actions']==1 and button.value=='changed'


def test_artifact_revision_keeps_prior_verified_delivery(tmp_path):
    backend, _, button=backend_with_button(); path=tmp_path/'trace.json'
    evidence={'required_files':[{'path':'first.txt','sha256':'first'}]}
    agent=DesktopAgent(backend, Planner(), Provider(), final_verifier=lambda _:(True, copy.deepcopy(evidence)))
    agent.run('First output', ['TextEdit'], path)
    evidence['required_files'][0]={'path':'second.txt','sha256':'second'}
    result=agent.run('Second output', ['TextEdit'], path, resume=path, amend_reason='Version 2')
    assert [v['goal_revision'] for v in result['artifact_versions']]==[1,2]
    assert result['artifact_versions'][0]['evidence']['required_files'][0]['sha256']=='first'
    again=agent.run('Second output', ['TextEdit'], path, resume=path)
    assert again['status']=='completed' and again['artifact_versions']==result['artifact_versions']


def test_cli_required_file_records_bytes_and_digest(tmp_path, monkeypatch):
    import bokkio.planner, bokkio.jev, hashlib
    from bokkio.cli import build_parser, execute
    monkeypatch.setattr(bokkio.planner,'OpenRouterPlanner',lambda **_:Planner())
    monkeypatch.setattr(bokkio.jev,'JevProvider',Provider)
    artifact=tmp_path/'output.txt'; artifact.write_bytes(b'persisted output')
    backend, _, _=backend_with_button()
    args=build_parser().parse_args(['run','--goal','Click Save','--allow-app','TextEdit',
                                   '--trace',str(tmp_path/'trace.json'),'--require-file',str(artifact)])
    result=execute(args,backend)
    info=result['artifact_versions'][0]['evidence']['required_files'][0]
    assert info['bytes']==16 and info['sha256']==hashlib.sha256(artifact.read_bytes()).hexdigest()


def test_word_facts_are_computed_only_from_visible_native_editor_values():
    import hashlib
    from test_cli import Element
    backend, window, _ = backend_with_button()
    editor=Element('text_area','Text Editor','example Example examples example.'); window.children_values=[editor]
    observed=planner_observation('Count the word "example"',backend.snapshot('TextEdit'),backend.windows('TextEdit'))
    assert observed['text_facts'][0]['word_counts']['example']=={
        'exact_substring':3,'whole_word_case_sensitive':2,'whole_word_case_insensitive':3}
    assert observed['text_facts'][0]['native_text_sha256']==hashlib.sha256(editor.value.encode()).hexdigest()
    assert observed['text_facts'][0]['characters']==len(editor.value)
    editor.value=''
    assert not planner_observation('Count the word "example"',backend.snapshot('TextEdit'),backend.windows('TextEdit'))['text_facts']
    editor.value='example'
    assert not planner_observation('Open "largefile.txt"',backend.snapshot('TextEdit'),backend.windows('TextEdit'))['text_facts']


def test_missing_deliverable_replans_after_ui_steps_succeed(tmp_path):
    backend, _, _ = backend_with_button()
    artifact = tmp_path / 'output.txt'
    class Repair(Planner):
        def plan(self, goal, observations, progress=None):
            if progress:
                assert progress['final_verification']['exists'] is False
                artifact.write_text('saved')
            return super().plan(goal, observations, progress)
    planner = Repair()
    trace = DesktopAgent(backend, planner, Provider(), final_verifier=lambda _: (
        artifact.is_file(), {'exists':artifact.is_file()})).run('Click Save', ['TextEdit'], tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['replans']==1
    assert [e['passed'] for e in trace['events'] if e['kind']=='delivery_verification']==[False, True]


def test_missing_deliverable_cannot_complete_after_budget(tmp_path):
    backend, _, _ = backend_with_button()
    trace = DesktopAgent(backend, Planner(), Provider(), max_replans=0,
                         final_verifier=lambda _: (False, {'exists':False})).run(
        'Click Save', ['TextEdit'], tmp_path/'trace.json')
    assert trace['status']=='blocked'
    assert trace['events'][-1]['reason']=='Final delivery is not verified'


def test_cli_required_file_is_verified_and_bound_to_resume_goal(tmp_path, monkeypatch):
    import bokkio.planner
    import bokkio.jev
    from bokkio.cli import build_parser,execute
    monkeypatch.setattr(bokkio.planner,'OpenRouterPlanner',lambda **_:Planner())
    monkeypatch.setattr(bokkio.jev,'JevProvider',Provider)
    backend, _, _=backend_with_button()
    path=tmp_path/'trace.json';artifact=tmp_path/'missing.txt'
    base=['run','--goal','Click Save','--allow-app','TextEdit','--trace',str(path),'--max-replans','0']
    args=build_parser().parse_args(base+['--require-file',str(artifact)])
    trace=execute(args,backend)
    assert trace['status']=='blocked'
    required=json.loads(trace['goal'].split('Required deliverable files: ')[1])
    assert required==[str(artifact.resolve())]
    with pytest.raises(BokkioError,match='goal and app allowlist'):
        execute(build_parser().parse_args(base+['--resume',str(path)]),backend)


@pytest.mark.parametrize('result', [None, (True,), ('yes', {}), (True, None)])
def test_invalid_final_verifier_fails_without_claiming_completion(tmp_path, result):
    backend, _, button = backend_with_button(); button.value = 'pressed'
    trace = DesktopAgent(backend, Planner(), Provider(), final_verifier=lambda _: result).run(
        'Click Save', ['TextEdit'], tmp_path/'trace.json')
    assert trace['status']=='failed' and trace['actions']==0


def test_pause_during_final_verifier_wins_over_completion(tmp_path):
    backend, _, button = backend_with_button(); button.value = 'pressed'
    signal = [None]
    def verify(_):
        signal[0]='pause'
        return True, {'exists':True}
    trace = DesktopAgent(backend, Planner(), Provider(), final_verifier=verify,
                         control=lambda:signal[0]).run('Click Save', ['TextEdit'], tmp_path/'trace.json')
    assert trace['status']=='paused'


def test_presence_checks_require_unique_exact_target():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    check = {'role':'dialog','name':'Save As','field':'present','equals':True}
    assert not verify_conditions(backend.snapshot('TextEdit'), [check])[0]
    window.children_values.append(Element('dialog','Save As'))
    assert verify_conditions(backend.snapshot('TextEdit'), [check])[0]
    check['equals']=False
    assert not verify_conditions(backend.snapshot('TextEdit'), [check])[0]
    window.children_values.append(Element('dialog','Save As'))
    check['equals']=True
    assert not verify_conditions(backend.snapshot('TextEdit'), [check])[0]


def test_checked_condition_uses_observed_native_state_and_requires_boolean():
    backend, _, button=backend_with_button()
    button.checked=False
    p=plan(); p['steps'][0]['success'][0].update(field='checked',equals=True)
    validate_plan(p,['TextEdit'])
    assert not verify_conditions(backend.snapshot('TextEdit'),p['steps'][0]['success'])[0]
    button.checked=True
    assert verify_conditions(backend.snapshot('TextEdit'),p['steps'][0]['success'])[0]
    p['steps'][0]['success'][0]['equals']='true'
    with pytest.raises(BokkioError,match='boolean'):
        validate_plan(p,['TextEdit'])


def test_editor_line_endings_are_equivalent_but_contradictory_checks_are_rejected():
    from test_cli import Element
    backend, window, _=backend_with_button()
    editor=Element('text_area','Text Editor','one\r\ntwo'); editor.parent_value=window
    window.children_values=[editor]
    check={'role':'text_area','name':'Text Editor','field':'value','equals':'one\ntwo'}
    assert verify_conditions(backend.snapshot('TextEdit'),[check])[0]
    editor.value='one\ntoo'
    assert not verify_conditions(backend.snapshot('TextEdit'),[check])[0]
    p=plan(); p['steps'][0]['success']=[check,dict(check,equals='one\r\ntwo')]
    with pytest.raises(BokkioError,match='conjunctive'):
        validate_plan(p,['TextEdit'])


@pytest.mark.parametrize('budget,expected', [(0,'blocked'), (1,'completed')])
def test_invalid_dialog_phase_is_rejected_and_repaired_before_action(tmp_path, budget, expected):
    backend, _, _=backend_with_button()
    class Phases(Planner):
        def plan(self, goal, observations, progress=None):
            self.calls.append(progress)
            p=plan()
            if len(self.calls)==1:
                p['continue_after_steps']=True
            elif len(self.calls)==2:
                p['steps'][0]['success']=[{'role':'dialog','name':'Save As','field':'present','equals':False}]
            else:
                assert progress['phase_completed'] and 'window=null' in progress['error']
            return p, {}
    planner=Phases()
    result=DesktopAgent(backend,planner,Provider(),max_replans=budget).run('Click Save',['TextEdit'],tmp_path/'trace.json')
    assert result['status']==expected and result['actions']==1
    assert len(planner.calls)==2+budget and result['replans']==budget
    assert any(e.get('stage')=='plan_validation' for e in result['events'])


def test_new_source_is_observed_before_planning_a_derived_output(tmp_path):
    from test_cli import Element
    backend, window, _ = backend_with_button()
    body = Element("text_area", "Text Editor", "not loaded"); body.editable = True
    load = Element("button", "Load")
    def open_source():
        load.value = "pressed"; body.value = "example example"
    load.press = open_source
    window.children_values = [load, body]
    calls = []
    class Phased:
        def plan(self, goal, observations, progress=None):
            calls.append(progress)
            if progress is None:
                return {"goal":goal, "continue_after_steps":True, "steps":[{
                    "id":"read", "app":"TextEdit", "window":None, "goal":"Click Load to read the source",
                    "risk":"read", "allowed_values":[], "success":[{"role":"button","name":"Load","field":"value","equals":"pressed"}]}]}, {}
            text = next(n['value'] for n in observations['TextEdit']['nodes'] if n['name']=='Text Editor')
            assert text == "example example"
            count = str(text.count('example'))
            return {"goal":goal,"continue_after_steps":False,"steps":[{
                "id":"write", "app":"TextEdit", "window":None, "goal":"Set Text Editor to the derived count",
                "risk":"local_write", "allowed_values":[count], "success":[{"role":"text_area","name":"Text Editor","field":"value","equals":count}]}]}, {}
    class Actions(Provider):
        def ask(self, state, questions):
            self.choice = "set_value" if "set_value" in questions['next']['criteria'] else "click"
            return super().ask(state, questions)
    trace = DesktopAgent(backend, Phased(), Actions()).run("Count example", ["TextEdit"], tmp_path/'trace.json')
    assert trace['status']=='completed' and trace['actions']==2 and trace['phases']==1 and trace['replans']==0
    assert body.value=='2' and calls[1]['phase_completed']
    assert calls[1]['completed_subtasks'][0]['id']=='read'


def test_phase_budget_and_resume_do_not_mark_partial_goal_complete(tmp_path):
    p = plan(); p['continue_after_steps'] = True
    backend, _, button = backend_with_button()
    button.value = 'pressed'
    planner = Planner(p)
    path = tmp_path/'phase.json'
    trace = DesktopAgent(backend, planner, Provider(), max_phases=1).run('Click Save', ['TextEdit'], path)
    assert trace['status']=='blocked' and trace['phases']==1 and trace['actions']==0
    assert trace['events'][-1]['reason']=='Phase continuation budget exhausted'
    before = len(planner.calls)
    resumed = DesktopAgent(backend, planner, Provider(), max_phases=1).run('Click Save', ['TextEdit'], path, resume=path)
    assert resumed['status']=='blocked' and resumed['phases']==1 and len(planner.calls)==before


def test_verified_loop_and_resume_observe_existing_success(tmp_path):
    backend, _, button = backend_with_button()
    planner = Planner(); output = tmp_path / "trace.json"
    agent = DesktopAgent(backend, planner, Provider())
    result = agent.run("Click Save", ["TextEdit"], output)
    assert result["status"] == "completed" and result["actions"] == 1
    assert result["completed_steps"] == ["save"] and button.value == "pressed"
    assert {e["kind"] for e in result["events"]} >= {"plan", "decision", "action", "observation", "outcome"}
    resumed = agent.run("Click Save", ["TextEdit"], output, resume=output)
    assert resumed["status"] == "completed" and resumed["actions"] == 1
    assert len(planner.calls) == 1


@pytest.mark.parametrize("control,status", [("pause", "paused"), ("cancel", "cancelled")])
def test_control_during_model_call_stops_before_dispatch(tmp_path, control, status):
    backend, _, button = backend_with_button(); signal = [None]
    class Interrupting(Provider):
        def ask(self, state, questions):
            response = super().ask(state, questions); signal[0] = control
            return response
    result = DesktopAgent(backend, Planner(), Interrupting(), control=lambda: signal[0]).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == status and button.value is None
    assert result["actions"] == 0


def test_low_confidence_replans_once_then_blocks(tmp_path):
    backend, _, button = backend_with_button(); planner = Planner()
    result = DesktopAgent(backend, planner, Provider(confidence=0.1)).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "blocked" and result["replans"] == 1
    assert result["actions"] == 0 and len(planner.calls) == 2 and button.value is None
    assert planner.calls[1]["failed_step"]["id"] == "save"


def test_model_done_does_not_override_native_outcome(tmp_path):
    backend, _, button = backend_with_button()
    result = DesktopAgent(backend, Planner(), Provider(choice="done", satisfied=1), max_replans=0).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "blocked" and button.value is None
    assert "outside the current options" in result["events"][-1]["reason"]


def test_action_budget_covers_actions_without_outcome_progress(tmp_path):
    backend, _, button = backend_with_button()
    impossible = plan(); impossible["steps"][0]["success"][0]["equals"] = "never"
    result = DesktopAgent(backend, Planner(impossible), Provider(), max_actions=2).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "blocked" and result["actions"] == 2


@pytest.mark.parametrize("risk", ["external", "destructive"])
def test_sensitive_steps_stop_before_decisions(tmp_path, risk):
    backend, _, button = backend_with_button()
    result = DesktopAgent(backend, Planner(plan(risk)), Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "blocked" and result["actions"] == 0 and button.value is None


def test_sensitive_target_blocks_even_if_planner_calls_it_local(tmp_path):
    backend, _, button = backend_with_button(); button.name = "Send"
    p = plan(); p["steps"][0]["goal"] = "Click Send"; p["steps"][0]["success"][0]["name"] = "Send"
    result = DesktopAgent(backend, Planner(p), Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "blocked" and result["actions"] == 0 and button.value is None


@pytest.mark.parametrize("mutation", ["app", "ref", "checks", "risk", "state"])
def test_untrusted_plans_cannot_expand_scope_or_invent_actions(mutation):
    p = plan(); s = p["steps"][0]
    if mutation == "app": s["app"] = "Unapproved"
    if mutation == "ref": s["ref"] = "invented"
    if mutation == "checks": s["success"] = []
    if mutation == "risk": s["risk"] = "unknown"
    if mutation == "state": s["success"][0].update(field="focused", equals="true")
    with pytest.raises(BokkioError): validate_plan(p, ["TextEdit"])


def test_ambiguous_value_verification_is_not_completion():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values.append(Element("button", "Save", "pressed"))
    snapshot = backend.snapshot("TextEdit")
    assert not verify_conditions(snapshot, plan()["steps"][0]["success"])[0]


def test_parent_name_distinguishes_repeated_file_properties_without_relaxing_uniqueness():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element("list_item", name, children=[Element("text_field", "Size", value)])
                              for name, value in [("small.txt", "1 KB"), ("testing.bin", "14,649 KB")]]
    check = {"role": "text_field", "name": "Size", "field": "value", "equals": "14,649 KB"}
    assert not verify_conditions(backend.snapshot("TextEdit"), [check])[0]
    check["parent_name"] = "testing.bin"
    assert verify_conditions(backend.snapshot("TextEdit"), [check])[0]
    check["parent_name"] = "small.txt"
    assert not verify_conditions(backend.snapshot("TextEdit"), [check])[0]
    check["parent_name"] = "testing.bin"
    window.children_values.append(Element("list_item", "testing.bin", children=[Element("text_field", "Size", "14,649 KB")]))
    assert not verify_conditions(backend.snapshot("TextEdit"), [check])[0]


def test_transport_json_contract_and_secret_redaction():
    seen = {}
    def opener(request, timeout):
        seen.update(json.loads(request.data))
        return BytesIO(json.dumps({"model": "offline", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan())}}], "usage": {"prompt_tokens": 1}}).encode())
    planner = OpenRouterPlanner(api_key="offline-secret", model="offline", opener=opener)
    result, metadata = planner.plan("Click Save", {"TextEdit": {}}, {"error": "retry"})
    assert result == plan() and seen["response_format"]["type"] == "json_schema"
    assert seen["response_format"]["json_schema"]["schema"]["properties"]["steps"]["items"]["anyOf"][0]["properties"]["app"]["enum"] == ["TextEdit"]
    assert seen["response_format"]["json_schema"]["schema"]["properties"]["steps"]["maxItems"] == 3
    assert "continue_after_steps" in seen["response_format"]["json_schema"]["schema"]["required"]
    checks = seen["response_format"]["json_schema"]["schema"]["properties"]["steps"]["items"]["anyOf"][0]["properties"]["success"]["items"]["anyOf"]
    presence = next(c for c in checks if c['properties']['field']['enum']==['present'])
    assert presence['properties']['name']=={'type':'string','minLength':1}
    assert presence['properties']['equals']=={'type':'boolean'}
    assert "offline-secret" not in json.dumps(metadata)
    assert json.loads(seen["messages"][1]["content"])["progress"] == {"error": "retry"}
    assert seen["max_tokens"] == 8000


def test_planner_reasoning_effort_is_sent_and_incomplete_output_still_rejected(monkeypatch):
    monkeypatch.setenv("BOKKIO_PLANNER_REASONING_EFFORT", "high")
    seen = {}
    def opener(request, timeout):
        seen.update(json.loads(request.data))
        return BytesIO(json.dumps({"choices": [{"finish_reason": "length", "message": {"content": ""}}]}).encode())
    planner = OpenRouterPlanner(api_key="offline-secret", model="offline", opener=opener, reasoning_effort="low")
    with pytest.raises(BokkioError, match="did not finish"):
        planner.plan("Click Save", {"TextEdit": {}})
    assert seen["reasoning"] == {"effort": "low"}
    assert seen["max_tokens"] == 8000


def test_invalid_planner_reasoning_effort_rejected():
    with pytest.raises(BokkioError, match="reasoning effort"):
        OpenRouterPlanner(api_key="offline-secret", model="offline", reasoning_effort="unbounded")


def test_truncated_planner_output_is_never_accepted():
    def opener(request, timeout):
        return BytesIO(json.dumps({"choices": [{"finish_reason": "length", "message": {"content": json.dumps(plan())}}]}).encode())
    planner = OpenRouterPlanner(api_key="offline-secret", model="offline", opener=opener)
    with pytest.raises(BokkioError, match="did not finish"):
        planner.plan("Click Save", {"TextEdit": {}})


def test_file_control_and_resume_scope(tmp_path):
    path = tmp_path / "control.json"; read = file_control(path)
    assert read() is None
    path.write_text('{"action":"pause"}'); assert read() == "pause"
    path.write_text('[]')
    with pytest.raises(BokkioError): read()
    backend, _, _ = backend_with_button(); output = tmp_path / "trace.json"
    agent = DesktopAgent(backend, Planner(), Provider())
    agent.run("Click Save", ["TextEdit"], output, plan_only=True)
    with pytest.raises(BokkioError, match="allowlist"):
        agent.run("Click Save", ["Other"], output, resume=output)


def test_stale_observation_replans_from_new_native_state(tmp_path):
    backend, _, button = backend_with_button(); planner = Planner()
    class Changing(Provider):
        changed = False
        def ask(self, state, questions):
            response = super().ask(state, questions)
            if not self.changed:
                button.value = "external change"; self.changed = True
            return response
    result = DesktopAgent(backend, planner, Changing()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "completed" and result["replans"] == 1
    assert "Snapshot changed" in planner.calls[1]["error"]
    assert len([e for e in result["events"] if e["kind"] == "action"]) == 1


def test_pause_checkpoint_can_resume_before_dispatch(tmp_path):
    backend, _, button = backend_with_button(); signal = ["pause"]
    planner = Planner(); output = tmp_path / "trace.json"
    agent = DesktopAgent(backend, planner, Provider(), control=lambda: signal[0])
    paused = agent.run("Click Save", ["TextEdit"], output)
    assert paused["status"] == "paused" and not planner.calls
    # A pause before initial planning resumes by planning from current state.
    signal[0] = None
    resumed = agent.run("Click Save", ["TextEdit"], output, resume=output)
    assert resumed["status"] == "completed" and button.value == "pressed"


@pytest.mark.parametrize("field,value", [("field", []), ("risk", [])])
def test_malformed_plan_values_return_contract_errors(field, value):
    p = plan()
    if field == "field": p["steps"][0]["success"][0][field] = value
    else: p["steps"][0][field] = value
    with pytest.raises(BokkioError): validate_plan(p, ["TextEdit"])


def test_loop_routes_actions_across_explicit_apps(tmp_path):
    first, _, button1 = backend_with_button(); second, _, button2 = backend_with_button()
    class Multi:
        backends = {"App A": first, "App B": second}
        calls = []
        def snapshot(self, app, window=None): return self.backends[app].snapshot(app, window)
        def windows(self, app): return self.backends[app].windows(app)
        def perform(self, app, action, **kwargs):
            self.calls.append(app)
            return self.backends[app].perform(app, action, **kwargs)
    p = plan(); p["steps"][0]["app"] = "App A"
    another = copy.deepcopy(p["steps"][0]); another.update(id="second", app="App B"); p["steps"].append(another)
    backend = Multi()
    result = DesktopAgent(backend, Planner(p), Provider()).run("Click both", ["App A", "App B"], tmp_path / "trace.json")
    assert result["status"] == "completed" and backend.calls == ["App A", "App B"]
    assert button1.value == button2.value == "pressed"


def test_planner_windows_remain_bound_to_their_allowed_app():
    p = plan()
    observations = {"TextEdit": {"windows": [{"name": "Different window"}]}}
    with pytest.raises(BokkioError, match="does not belong"):
        validate_plan(p, ["TextEdit"], observations)


def test_invalid_initial_plan_gets_one_bounded_contract_repair(tmp_path):
    backend, _, button = backend_with_button()
    class Repairing(Planner):
        def plan(self, goal, observations, progress=None):
            self.calls.append(progress)
            result = plan()
            if len(self.calls) == 1: result["steps"][0]["id"] = 1
            return result, {"model": "offline"}
    planner = Repairing()
    result = DesktopAgent(backend, planner, Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert result["status"] == "completed" and result["replans"] == 1 and button.value == "pressed"
    assert "Subtask ids" in planner.calls[1]["error"]


def test_corrupt_checkpoint_is_a_contract_error(tmp_path):
    path = tmp_path / "broken.json"; path.write_text('{"goal":')
    backend, _, button = backend_with_button()
    with pytest.raises(BokkioError, match="checkpoint"):
        DesktopAgent(backend, Planner(), Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json", resume=path)
    assert button.value is None


def test_cli_blocked_status_is_nonzero_and_stdout_is_summary(tmp_path, monkeypatch, capsys):
    from bokkio import cli
    monkeypatch.setattr(cli, "Xa11yBackend", lambda: None)
    monkeypatch.setattr(cli, "execute", lambda *_: {"status": "blocked", "actions": 0, "replans": 1, "completed_steps": [],
                                                 "events": [{"reason": "low confidence"}], "private_snapshot": "large private data"})
    rc = cli.main(["run", "--goal", "Click Save", "--allow-app", "TextEdit", "--trace", str(tmp_path / "trace.json")])
    printed = capsys.readouterr().out
    assert rc == 1 and json.loads(printed)["reason"] == "low confidence"
    assert "private_snapshot" not in printed and "large private data" not in printed


def test_planner_observes_named_target_beyond_first_hundred_nodes():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Sample {i}") for i in range(1, 1001)] + [Element("static_text", "Ready")]
    for child in window.children_values: child.parent_value = window
    observations = DesktopAgent(backend, Planner(), Provider())._observations(["TextEdit"], "Click Sample 997")
    observed = observations["TextEdit"]
    assert observed["observation_scope"]["strategy"] == "exact_observed_names"
    assert {n["name"] for n in observed["nodes"]} >= {"Sample 997", "Ready", "Untitled"}
    assert "Sample 998" not in {n["name"] for n in observed["nodes"]}
    assert next(n for n in observed["nodes"] if n["name"] == "Sample 997")["window_name"] == "Untitled"
    assert observed["truncated_nodes"] == 999
    assert "ref" not in json.dumps(observed)


def test_planner_preserves_duplicate_targets_and_their_parent_context():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element("group", name, children=[Element("button", "Action")]) for name in ("Left", "Right")]
    for child in window.children_values: child.parent_value = window
    observed = DesktopAgent(backend, Planner(), Provider())._observations(["TextEdit"], "Click Action in Right")
    buttons = [n for n in observed["TextEdit"]["nodes"] if n["name"] == "Action"]
    assert len(buttons) == 2 and {n["parent_name"] for n in buttons} == {"Left", "Right"}


def test_planner_samples_all_windows_without_a_goal_name_match():
    from bokkio.agent import planner_observation
    from test_cli import Element
    backend, window, _ = backend_with_button()
    other = Element("window", "Second", children=[Element("button", f"Other {i}") for i in range(300)])
    window.children_values = [Element("button", f"Sample {i}") for i in range(1000)]
    for child in window.children_values: child.parent_value = window
    app = backend._resolve_app("TextEdit"); app.element.children_values.append(other); other.parent_value = app.element
    observed = planner_observation("Inspect the UI", backend.snapshot("TextEdit"), backend.windows("TextEdit"))
    assert len(observed["nodes"]) == 240
    assert observed["observation_scope"]["strategy"] == "balanced_windows"
    assert {n["name"] for n in observed["nodes"]} >= {"Sample 999", "Other 299", "Second", "Untitled"}
    assert {n["window_name"] for n in observed["nodes"] if n["role"] == "button"} == {"Second", "Untitled"}


def test_missing_window_triggers_bounded_replanning_from_current_windows(tmp_path):
    backend, window, button = backend_with_button(); original = backend.snapshot
    def snapshot(app, selected=None):
        if selected == "Untitled":
            window.name = "Renamed"
            raise BokkioError("Window not found: Untitled")
        return original(app, selected)
    backend.snapshot = snapshot
    class RenamingPlanner(Planner):
        def plan(self, goal, observations, progress=None):
            self.calls.append(progress); result = plan()
            result["steps"][0]["window"] = observations["TextEdit"]["windows"][0]["name"]
            return result, {"model": "offline"}
    planner = RenamingPlanner()
    trace = DesktopAgent(backend, planner, Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert trace["status"] == "completed" and trace["replans"] == 1 and trace["actions"] == 1
    assert button.value == "pressed" and planner.calls[1]["error"] == "Window not found: Untitled"


def test_repeated_native_changes_recover_with_two_replans(tmp_path):
    backend, _, button = backend_with_button(); planner = Planner()
    class Changing(Provider):
        remaining = 2
        def ask(self, state, questions):
            result = super().ask(state, questions)
            if self.remaining:
                button.value = str(self.remaining); self.remaining -= 1
            return result
    trace = DesktopAgent(backend, planner, Changing(), max_replans=2).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert trace["status"] == "completed" and trace["replans"] == 2 and trace["actions"] == 3
    assert len(planner.calls) == 3 and button.value == "pressed"


def test_checkpoint_retries_transient_windows_reader_lock(tmp_path, monkeypatch):
    from bokkio import agent
    source, target = tmp_path / "new", tmp_path / "old"
    source.write_text("new contents"); target.write_text("old contents")
    original = agent.os.replace; calls, delays = [], []
    def replace(src, dst):
        calls.append((src, dst))
        if len(calls) < 3:
            error = PermissionError("reader briefly holds file"); error.winerror = 32
            assert target.read_text() == "old contents"
            raise error
        original(src, dst)
    monkeypatch.setattr(agent.os, "replace", replace)
    monkeypatch.setattr(agent.time, "sleep", delays.append)
    agent.replace_checkpoint(source, target)
    assert len(calls) == 3 and delays == [0.05, 0.1]
    assert target.read_text() == "new contents" and not source.exists()


def test_checkpoint_permanent_lock_stops_before_any_native_action(tmp_path, monkeypatch):
    from bokkio import agent
    backend, _, button = backend_with_button(); calls, delays = [], []
    def replace(*args):
        calls.append(args); error = PermissionError("permanent lock"); error.winerror = 32; raise error
    monkeypatch.setattr(agent.os, "replace", replace)
    monkeypatch.setattr(agent.time, "sleep", delays.append)
    planner = Planner()
    # The first start checkpoint fails before planning or dispatch.
    with pytest.raises(BokkioError, match="private task trace"):
        DesktopAgent(backend, planner, Provider()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert len(calls) == 6 and len(delays) == 5 and button.value is None and not planner.calls
    assert not list(tmp_path.iterdir())


def test_checkpoint_failure_after_model_returns_failed_without_dispatch(tmp_path, monkeypatch):
    from bokkio import agent
    backend, _, button = backend_with_button()
    class ReadOnlyAfterModel(Provider):
        def ask(self, state, questions):
            response = super().ask(state, questions)
            def replace(*args): raise OSError("output unavailable")
            monkeypatch.setattr(agent.os, "replace", replace)
            return response
    trace = DesktopAgent(backend, Planner(), ReadOnlyAfterModel()).run("Click Save", ["TextEdit"], tmp_path / "trace.json")
    assert trace["status"] == "failed" and trace["actions"] == 0 and button.value is None
    assert trace["checkpoint_error"] == "Could not write private task trace"
    assert trace["events"][-1]["status"] == "failed"


def test_planner_keeps_submit_near_search_when_goal_omits_submit_name():
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element("text_field", "Search", ""), Element("button", "Submit"), Element("static_text", "Ready")]
    for child in window.children_values: child.parent_value = window
    observed = DesktopAgent(backend, Planner(), Provider())._observations(["TextEdit"], "Search for hello")
    assert {n["name"] for n in observed["TextEdit"]["nodes"]} >= {"Search", "Submit", "Ready"}


def test_replan_receives_verified_subtask_outcomes_not_just_ids(tmp_path):
    from test_cli import Element
    backend, window, _ = backend_with_button()
    other = Element("button", "Other"); other.parent_value = window; window.children_values.append(other)
    p = plan(); second = copy.deepcopy(p["steps"][0]); second.update(id="other", goal="Click Other")
    second["success"][0]["name"] = "Other"; p["steps"].append(second)
    planner = Planner(p)
    class ChangingOther(Provider):
        changed = False
        def ask(self, state, questions):
            response = super().ask(state, questions)
            if not self.changed and any(c.get("name") == "Other" for c in questions.get("click_target", {}).get("criteria", {}).values()):
                other.value = "changed"; self.changed = True
            return response
    trace = DesktopAgent(backend, planner, ChangingOther()).run("Click Save then Other", ["TextEdit"], tmp_path / "trace.json")
    assert trace["status"] == "completed" and trace["replans"] == 1
    completed = planner.calls[1]["completed_subtasks"]
    assert len(completed) == 1 and completed[0]["id"] == "save" and completed[0]["app"] == "TextEdit"
    assert completed[0]["success"] == p["steps"][0]["success"]


def test_resume_retains_overwritten_intermediate_steps_without_duplicate_writes(tmp_path):
    backend, _, button = backend_with_button()
    writes = []
    def append_record():
        writes.append(len(writes) + 1)
        button.value = str(writes[-1])
    button.press = append_record
    p = plan()
    p['steps'] = []
    for i in range(1, 4):
        step = copy.deepcopy(plan()['steps'][0])
        step.update(id=f'stage-{i}', goal=f'Append record {i}')
        step['success'][0]['equals'] = str(i)
        p['steps'].append(step)
    output = tmp_path / 'trace.json'
    signal = [True]
    planner = Planner(p)
    agent = DesktopAgent(backend, planner, Provider(), max_actions=4,
                         control=lambda: 'pause' if signal[0] and len(writes) == 2 else None)
    paused = agent.run('Append three records', ['TextEdit'], output)
    assert paused['status'] == 'paused' and writes == [1, 2]
    assert paused['completed_steps'] == ['stage-1', 'stage-2']
    signal[0] = False
    resumed = agent.run('Append three records', ['TextEdit'], output, resume=output)
    assert resumed['status'] == 'completed' and writes == [1, 2, 3]
    assert resumed['actions'] == 3 and len(planner.calls) == 1
    assert [e['step'] for e in resumed['events'] if e['kind'] == 'subtask_retained'] == ['stage-1', 'stage-2']


def test_reused_id_with_changed_subtask_is_not_retained(tmp_path):
    backend, _, button = backend_with_button()
    p = plan()
    first = copy.deepcopy(p['steps'][0])
    first.update(goal='Earlier work')
    last = copy.deepcopy(p['steps'][0]); last['id'] = 'last'
    p['steps'].append(last)
    # A historical receipt sharing an ID must not authorize skipping new work.
    checkpoint = {'goal': 'Click Save', 'apps': ['TextEdit'], 'plan': p,
                  'events': [{'kind': 'subtask_completed', 'step': 'save', 'subtask': first}],
                  'completed_steps': ['save'], 'actions': 0, 'replans': 0}
    output = tmp_path / 'trace.json'; output.write_text(json.dumps(checkpoint))
    result = DesktopAgent(backend, Planner(), Provider()).run('Click Save', ['TextEdit'], output, resume=output)
    assert result['status'] == 'completed' and result['actions'] == 1 and button.value == 'pressed'
    assert not any(e['kind'] == 'subtask_retained' for e in result['events'])


def test_completed_final_step_is_reobserved_on_resume(tmp_path):
    backend, _, button = backend_with_button()
    output = tmp_path / 'trace.json'; agent = DesktopAgent(backend, Planner(), Provider())
    agent.run('Click Save', ['TextEdit'], output)
    button.value = 'changed externally'
    resumed = agent.run('Click Save', ['TextEdit'], output, resume=output)
    assert resumed['status'] == 'completed' and resumed['actions'] == 2
    assert button.value == 'pressed'


def test_already_checked_menu_with_invented_parent_replans_without_toggling(tmp_path):
    from test_cli import Element
    backend,window,_=backend_with_button()
    toggle=Element('menu_item','Extensions');toggle.actions=['press','toggle'];toggle.checked=True
    toggle.parent_value=window;window.children_values=[toggle]
    clicks=[]
    def press():
        clicks.append(True);toggle.checked=False
    toggle.press=press
    p=plan();p['steps'][0].update(goal='Enable Extensions',window=None)
    p['steps'][0]['success']=[{'role':'menu_item','name':'Extensions','parent_name':'Show', 'field':'checked','equals':True}]
    class Repairing(Planner):
        def plan(self,goal,observations,progress=None):
            result,metadata=super().plan(goal,observations,progress)
            if progress:
                assert 'already matches' in progress['error']
                result['steps'][0]['success'][0]['parent_name']=None
            return result,metadata
    result=DesktopAgent(backend,Repairing(p),Provider()).run('Enable Extensions',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='completed' and result['actions']==0 and result['replans']==1
    assert toggle.checked is True and not clicks


def test_menu_checked_and_closed_conditions_need_separate_subtasks():
    p=plan();p['steps'][0]['success']=[
        {'role':'menu_item','name':'Extensions','field':'checked','equals':True},
        {'role':'menu_item','name':'Show','field':'expanded','equals':False}]
    with pytest.raises(BokkioError,match='separate subtasks'):
        validate_plan(p,['TextEdit'])


def test_native_ui_cycle_is_repaired_before_exhausting_actions(tmp_path):
    backend,_,button=backend_with_button();button.value='a'
    def toggle():button.value='b' if button.value=='a' else 'a'
    button.press=toggle
    p=plan();p['steps'][0]['success'][0]['equals']='unreachable'
    result=DesktopAgent(backend,Planner(p),Provider(),max_actions=10,max_replans=0).run(
        'Click Save',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='blocked' and result['actions']==2
    assert 'earlier state' in result['events'][-1]['reason']


def test_address_submit_replans_after_native_window_changes_with_stale_entry_predicate(tmp_path,monkeypatch):
    from bokkio.decision import Decision
    from test_cli import Element
    backend,window,_=backend_with_button()
    address=Element('text_field','Address Bar',r'C:\Task\Desktop')
    address.editable=True;address.actions=['set_value'];window.children_values=[address]
    initial={'id':'navigate','app':'TextEdit','window':None,'goal':'Submit address bar',
             'allowed_values':[],'requires_action':True,'risk':'read',
             'success':[{'role':'text_field','name':'Address Bar','field':'value','equals':r'C:\Task\Desktop'},
                        {'role':'window','name':'Start','field':'present','equals':True}]}
    class NavigationPlanner(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            if progress is None:return {'goal':goal,'steps':[initial]},{}
            assert progress['native_address_submitted']=='Address Bar'
            assert progress['navigation_result']=={'submitted_address':r'C:\Task\Desktop','window_names':['Desktop'],'command_dispatched':True}
            step={**initial,'requires_action':False,'success':[{'role':'window','name':'Desktop','field':'present','equals':True}]}
            return {'goal':goal,'steps':[step]},{}
    def decide(*args,**kwargs):
        from bokkio.selector import flatten
        ref=next(n['ref'] for n in flatten(args[2]['windows']) if n['name']=='Address Bar')
        return Decision('submit',ref,None,1.0,'unused'),{}
    calls=[]
    def execute(*args):
        calls.append('Enter');window.name='Desktop';address.value=''
        return {'tree_changed':True}
    monkeypatch.setattr('bokkio.agent.decide',decide)
    monkeypatch.setattr('bokkio.agent.execute_decision',execute)
    result=DesktopAgent(backend,NavigationPlanner(),Provider()).run('Navigate',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='completed' and result['actions']==1 and result['phases']==1
    assert calls==['Enter'] and any(e.get('reason')=='native_address_submitted' for e in result['events'])


def test_navigation_success_cannot_use_window_keyboard_focus():
    p=plan();p['steps'][0].update(window=None,goal='Submit the address to navigate to Documents folder')
    p['steps'][0]['success']=[{'role':'window','name':'Documents','field':'focused','equals':True}]
    with pytest.raises(BokkioError,match='keyboard focus cannot prove'):
        validate_plan(p,['TextEdit'])
    p['steps'][0]['success'][0].update(field='present')
    assert validate_plan(p,['TextEdit'])==p


def test_inline_editor_context_survives_a_runtime_error_and_rejects_reopening(tmp_path):
    from test_cli import Element
    backend,window,button=backend_with_button();button.name='Rename'
    field=Element('text_field','old.txt','old.txt');field.editable=True;field.actions=['set_value']
    field.raw={'class_name':'UIRenameTextElement'}
    window.children_values=[field,button]
    writing={'id':'write','app':'TextEdit','window':None,'goal':'Set old.txt to new.txt',
             'allowed_values':['new.txt'],'risk':'local_write',
             'success':[{'role':'text_field','name':'old.txt','field':'value','equals':'new.txt'}]}
    class Repairing(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            assert progress['native_inline_editor_opened']=='Rename'
            if len(self.calls)==2:
                bad={**writing,'goal':'Click Rename to open editor'}
                return {'goal':goal,'steps':[bad]},{}
            return {'goal':goal,'steps':[writing]},{}
    original=backend.perform;calls=[]
    def perform(*args,**kwargs):
        calls.append(args[1])
        if len(calls)==1:raise BokkioError('Native field temporarily unavailable')
        return original(*args,**kwargs)
    backend.perform=perform
    trace=DesktopAgent(backend,Repairing(),Provider(),max_replans=3).run('Rename',['TextEdit'],tmp_path/'trace.json')
    assert trace['status']=='completed' and field.value=='new.txt'
    assert calls==['set_value','set_value'] and trace['replans']==2
    assert any(e.get('stage')=='plan_validation' and 'already open' in e.get('error','') for e in trace['events'])


def test_ambiguous_checked_outcome_replans_before_dispatching_or_toggling_again(tmp_path):
    from test_cli import Element
    backend,window,_=backend_with_button()
    breadcrumb=Element('button','Notifications');breadcrumb.checked=None
    toggle=Element('button','Notifications');toggle.checked=False
    parent=Element('button','Show more settings',children=[toggle])
    toggle.parent_value=parent;parent.parent_value=window;breadcrumb.parent_value=window
    window.children_values=[breadcrumb,parent]
    p=plan();p['steps'][0]['success']=[{'role':'button','name':'Notifications','field':'checked','equals':False,'parent_name':None}]
    class RepairPlanner(Planner):
        def plan(self,goal,observations,progress=None):
            self.calls.append(progress)
            fixed=copy.deepcopy(p)
            if progress is not None:fixed['steps'][0]['success'][0]['parent_name']='Show more settings'
            return fixed,{}
    class NoCalls:
        def ask(self,*args):raise AssertionError('Already correct toggle must not be dispatched')
    planner=RepairPlanner()
    result=DesktopAgent(backend,planner,NoCalls()).run('Turn off notifications',['TextEdit'],tmp_path/'trace.json')
    assert result['status']=='completed' and result['actions']==0 and result['replans']==1
    assert 'ambiguous' in next(e['error'] for e in result['events'] if e['kind']=='error')
