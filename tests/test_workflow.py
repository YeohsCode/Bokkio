import copy
import json
from pathlib import Path
import pytest
from bokkio.workflow import (Recorder,WorkflowReplay,from_agent_trace,make_workflow,
                             repair_version,resolve,selector_for,validate_workflow)
from bokkio.model import BokkioError,tree_digest
from test_cli import backend_with_button,Element


def setup():
    backend,window,button=backend_with_button()
    text=Element('text_field','Search',value='');text.actions=['set_value','type_text'];text.editable=True
    row=Element('list_item','Second');row.actions=['select']
    window.children_values.extend([text,row]);text.parent_value=window;row.parent_value=window
    return backend,window,button,text,row


def record():
    backend,window,button,text,row=setup()
    r=Recorder(backend,{'editor':'TextEdit'})
    r.perform('editor','type',intent='Insert text',role='text_field',name='Search',value='hello',expected_value='hello')
    r.perform('editor','click',intent='Press Save',role='button',name='Save',verify=[{'role':'button','name':'Save','field':'value','equals':'pressed'}])
    r.perform('editor','select',intent='Select Second',role='list_item',name='Second')
    return backend,window,button,text,row,r,r.export('Test workflow')


def test_record_and_replay_three_times_without_models():
    backend,_,button,text,row,r,w=record()
    assert len(r.events)==3
    for _ in range(3):
        text.value='';button.value=None;row.selected=False
        result=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
        assert result['status']=='completed'
        assert text.value=='hello' and row.selected and button.value=='pressed'
        assert all(s['selector']['lane']=='exact_ref' and len(s['observations'])>=2 for s in result['steps'])


def test_pid_and_ref_change_uses_semantic_context():
    _,_,_,_,_,_,w=record()
    backend,_,button,text,row=setup()
    backend._resolve_app('TextEdit').pid=999
    report=WorkflowReplay(backend,timeout=0).run(w,{'editor':'999'})
    assert report['status']=='completed'
    assert all(s['selector']['lane']=='role_name_context' for s in report['steps'])


def test_ambiguous_duplicate_rejects_even_if_recorded_ref_exists():
    backend,window,_,_,_,_,w=record()
    duplicate=Element('text_field','Search',value='');duplicate.actions=['type_text'];duplicate.editable=True
    window.children_values.append(duplicate);duplicate.parent_value=window
    report=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
    assert report['status']=='failed' and not report['steps'][0]['dispatched']
    assert report['steps'][0]['error']['error']=='ambiguous_element'


def test_same_name_different_parent_cannot_steal_target():
    backend,window,_,text,_,_,w=record()
    group=Element('group','Other',children=[text]);group.parent_value=window
    window.children_values=[n for n in window.children_values if n is not text]+[group]
    result=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
    assert result['status']=='failed' and not result['steps'][0]['dispatched']


def test_failed_dispatch_never_repeated_and_marks_unknown_completion():
    backend,_,_,text,_,_,w=record();calls=[];text.value=''
    def broken(*a,**kw):calls.append(kw);raise BokkioError('Provider failed after possible effect')
    backend.perform=broken
    result=WorkflowReplay(backend).run(w,{'editor':'TextEdit'})
    assert len(calls)==1 and result['steps'][0]['completion_unknown']


def test_tamper_and_binding_rejected_before_native_reads():
    backend,_,_,_,_,_,w=record()
    bad=copy.deepcopy(w);bad['steps'][0]['arguments']['value']='other'
    with pytest.raises(BokkioError,match='hash'):WorkflowReplay(backend).run(bad,{'editor':'TextEdit'})
    with pytest.raises(BokkioError,match='Bind'):WorkflowReplay(backend).run(w,{'editor':'TextEdit','other':'Finder'})


def test_pause_and_cancel_before_dispatch():
    backend,_,_,_,_,_,w=record()
    for signal,status in [('pause','paused'),('cancel','cancelled')]:
        report=WorkflowReplay(backend,control=lambda:signal).run(w,{'editor':'TextEdit'})
        assert report['status']==status and not report['steps'][0]['dispatched']


def test_type_seed_failure_stops_before_dispatch():
    backend,_,_,text,_,_,w=record()
    text.value='wrong seed'
    report=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
    assert report['status']=='failed' and len(report['steps'])==1
    assert not report['steps'][0]['dispatched']


def test_repair_preserves_original_and_requires_failed_version():
    backend,_,_,text,_,_,w=record();original=copy.deepcopy(w)
    text.value='wrong'
    report=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
    repaired=repair_version(w,report,w['steps'],'Restore seed before replay')
    assert w==original and repaired['revision']==2 and repaired['parent_sha256']==w['sha256']
    with pytest.raises(BokkioError):repair_version(w,{**report,'workflow_sha256':'other'},w['steps'],'fix')


def test_trace_compiler_pairs_native_receipts_and_current_revision():
    backend,_,_,text,_=setup();before=backend.snapshot('TextEdit')
    node=next(n for n in __import__('bokkio.selector',fromlist=['flatten']).flatten(before['windows']) if n['name']=='Search')
    result=backend.perform('TextEdit','set_value',ref=node['ref'],value='compiled')
    checks=[{'condition':{'role':'text_field','name':'Search','field':'value','equals':'compiled'},'passed':True}]
    decision={'action':'set_value','ref':node['ref'],'value':'compiled','snapshot_id':tree_digest(before['windows'])}
    trace={'status':'completed','events':[
        {'kind':'observation','snapshot':before}, {'kind':'decision','decision':decision},
        {'kind':'action','subtask':{'app':'TextEdit','goal':'Set Search','risk':'local_write'},'result':result},
        {'kind':'outcome','snapshot':backend.snapshot('TextEdit'),'passed':True,'checks':checks}]}
    w=from_agent_trace(trace,'compiled',{'TextEdit':'editor'})
    text.value=''
    assert WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})['status']=='completed'
    with pytest.raises(BokkioError,match='completed'):from_agent_trace({**trace,'status':'blocked'},'bad',{'TextEdit':'editor'})
    bad=copy.deepcopy(trace);bad['events'][1]['decision']['ref']='wrong'
    with pytest.raises(BokkioError,match='identity'):from_agent_trace(bad,'bad',{'TextEdit':'editor'})


def test_schema_rejects_shell_sensitive_and_forward_dependency():
    *_,w=record()
    for field,value in [('action','shell'),('risk','external'),('depends_on',['future'])]:
        steps=copy.deepcopy(w['steps']);steps[0][field]=value
        with pytest.raises(BokkioError):make_workflow('bad',steps,'test')
    steps=copy.deepcopy(w['steps']);steps[0]['target']['name']='Send'
    with pytest.raises(BokkioError,match='Sensitive'):make_workflow('bad',steps,'test')


def test_wait_missing_target_uses_bounded_observation_retries():
    backend,_,_,_,_,_,w=record();original=backend.snapshot;calls=[]
    def late(app):
        snapshot=original(app);calls.append(app)
        if len(calls)==1:snapshot['windows'][0]['children'][0]['children']=[]
        return snapshot
    backend.snapshot=late
    report=WorkflowReplay(backend,timeout=0.1,poll_interval=0.01).run(w,{'editor':'TextEdit'})
    assert report['status']=='failed' # prior recording's hello seed fails exact type readback
    assert len(report['steps'][0]['observations'])>=3


def test_record_click_without_verification_rejected_before_effect():
    backend,_,button,_,_=setup();recorder=Recorder(backend,{'editor':'TextEdit'})
    with pytest.raises(BokkioError,match='explicit business verification'):
        recorder.perform('editor','click',intent='Save',role='button',name='Save')
    assert button.value is None


def test_postcondition_wait_observes_without_repeating_dispatch():
    backend,_,button,text,_,_,w=record();text.value='';button.value=None
    backend.supports_action_observation=False  # exercise providers without bundled observations
    original=backend.perform;calls=[];snapshot=backend.snapshot;remaining=[0]
    def perform(*args,**kw):
        calls.append(args[1]);result=original(*args,**kw)
        if args[1]=='click':button.value=None;remaining[0]=2
        return result
    def delayed(app):
        if remaining[0]:
            remaining[0]-=1
            if not remaining[0]:button.value='pressed'
        return snapshot(app)
    backend.perform=perform;backend.snapshot=delayed
    report=WorkflowReplay(backend,timeout=0.1,poll_interval=0.01).run(w,{'editor':'TextEdit'})
    assert report['status']=='completed' and calls==['type','click','select']
    assert len(report['steps'][1]['observations'])==3


def test_cli_compile_and_repair_do_not_construct_native_provider(tmp_path):
    import gzip
    from bokkio.cli import main
    path=Path(__file__).parents[1]/'docs/evidence/2026-10-04-waa-pilot/waa-pilot-v8/1/trace.json.gz'
    trace=json.loads(gzip.decompress(path.read_bytes()));source=tmp_path/'trace.json'
    source.write_text(json.dumps(trace));out=tmp_path/'workflow.json'
    assert main(['workflow','compile','--trace',str(source),'--name','Draft','--bind',trace['apps'][0]+'=notepad','--output',str(out)])==0
    compiled=json.loads(out.read_text())
    assert len(compiled['steps'])==5 and compiled['source']=='completed_agent_trace'
    import os
    if os.name!='nt':assert not (out.stat().st_mode & 0o077)
    with pytest.raises(BokkioError):
        from_agent_trace({**trace,'goal_revision':2},'Other', {trace['apps'][0]:'notepad'})


def test_compiler_rejects_false_outcome_claim(tmp_path):
    import gzip
    path=Path(__file__).parents[1]/'docs/evidence/2026-10-04-waa-pilot/waa-pilot-v8/1/trace.json.gz'
    trace=json.loads(gzip.decompress(path.read_bytes()))
    outcome=next(e for e in trace['events'] if e['kind']=='outcome')
    outcome['checks'][0]['condition']['equals']='tampered'
    with pytest.raises(BokkioError,match='inconsistent'):
        from_agent_trace(trace,'Bad',{a:'notepad' for a in trace['apps']})


def test_optional_provider_repair_returns_version_without_dispatch():
    from bokkio.workflow import request_repair
    backend,_,_,text,_,_,w=record();text.value='wrong seed'
    report=WorkflowReplay(backend,timeout=0).run(w,{'editor':'TextEdit'})
    calls=[]
    class Provider:
        def repair(self,context):
            calls.append(context);return {'steps':copy.deepcopy(w['steps'])}
    repaired=request_repair(w,report,Provider(),'Repair seed context')
    assert repaired['revision']==2 and calls[0]['failed_step']=='s1'
    assert not report['steps'][0]['dispatched'] and text.value=='wrong seed'
    class BadProvider:
        def repair(self,context):
            steps=copy.deepcopy(w['steps']);steps[0]['app']='unauthorized';return {'steps':steps}
    with pytest.raises(BokkioError,match='scope'):request_repair(w,report,BadProvider(),'bad')


def test_nonempty_caret_dependent_type_is_rejected_before_dispatch():
    backend,_,_,text,_=setup();text.value='seed'
    recorder=Recorder(backend,{'editor':'TextEdit'})
    with pytest.raises(BokkioError,match='empty field'):
        recorder.perform('editor','type',intent='Insert at unknown caret',role='text_field',name='Search',value='x')
    assert text.value=='seed'


def test_invoke_alias_replays_advertised_click_capability():
    backend,_,button,_,_=setup()
    recorder=Recorder(backend,{'editor':'TextEdit'})
    recorder.perform('editor','invoke',intent='Invoke Save',role='button',name='Save',
                     verify=[{'role':'button','name':'Save','field':'value','equals':'pressed'}])
    workflow=recorder.export('Invoke alias');button.value=None
    report=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'TextEdit'})
    assert report['status']=='completed' and button.value=='pressed'


@pytest.mark.parametrize('action', ['focus','select','expand','collapse','type','set_value'])
def test_recording_no_effect_action_cannot_verify_its_own_wrong_state(action):
    backend,window,_,text,row=setup()
    target=row if action=='select' else text
    target.actions=['focus','select','expand','collapse','type_text','set_value']
    target.expanded=action=='collapse'
    method={'type':'type_text'}.get(action,action)
    setattr(target,method,lambda *args:None)
    recorder=Recorder(backend,{'editor':'TextEdit'})
    kwargs={'value':'requested'} if action in {'type','set_value'} else {}
    with pytest.raises(BokkioError,match='verification failed'):
        recorder.perform('editor',action,intent='Required state change',role=target.role,name=target.name,**kwargs)
    assert recorder.steps==[] and recorder.events[-1]['passed'] is False
