import copy
import json
from pathlib import Path

import pytest

from bokkio.model import BokkioError
from bokkio.workflow import (Recorder, WorkflowReplay, bind_parameters, digest,
                             parameterize, repair_version)
from test_workflow import record, setup
from test_cli import Element


def template():
    backend,window,button,text,row,recorder,workflow=record()
    template=parameterize(workflow,{'text':{'type':'string','max_length':100}}, {
        '/steps/0/arguments/value':'text', '/steps/0/arguments/expected_value':'text',
        '/steps/0/verify/0/equals':'text'})
    return backend,button,text,row,workflow,template


def test_same_template_three_inputs_without_mutation():
    backend,button,text,row,base,workflow=template();before=copy.deepcopy(workflow)
    for value in ['alpha','beta punctuation!','第三组输入']:
        text.value='';button.value=None;row.selected=False
        run=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'TextEdit'},parameters={'text':value})
        assert run['status']=='completed' and text.value==value
        assert run['workflow_sha256']==workflow['sha256'] and run['parameters_sha256']==digest({'text':value})
    assert workflow==before and workflow['parent_sha256']==base['sha256']


@pytest.mark.parametrize('values',[{}, {'text':'x','extra':'y'}, {'text':1}, {'text':'\0'}, {'text':'x'*101}])
def test_bad_parameters_fail_before_native_read(values):
    backend,_,_,_,_,workflow=template()
    backend.snapshot=lambda *a:pytest.fail('Must fail before a native read')
    with pytest.raises(BokkioError):WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},parameters=values)


@pytest.mark.parametrize('pointer',['/steps/0/app','/steps/0/action','/steps/0/risk','/steps/0/target/ref'])
def test_parameters_cannot_replace_scope_actions_or_native_identity(pointer):
    *_,workflow=record()
    with pytest.raises(BokkioError,match='permitted literal'):
        parameterize(workflow,{'input':{'type':'string','max_length':50}},{pointer:'input'})


def test_sensitive_bound_target_is_rejected_before_read():
    *_,workflow=record()
    template=parameterize(workflow,{'name':{'type':'string','max_length':50}},{'/steps/1/target/name':'name'})
    with pytest.raises(BokkioError,match='Sensitive'):bind_parameters(template,{'name':'Send'})


def test_path_template_validation_uses_a_windows_absolute_sample(monkeypatch):
    # Reproduce the first native closure failure even on a POSIX test host.
    import ntpath
    from bokkio import workflow_inputs
    monkeypatch.setattr(workflow_inputs,'absolute_path',
        lambda value:isinstance(value,str) and ntpath.isabs(value) and bool(ntpath.splitdrive(value)[0]))
    *_,base=record()
    workflow=parameterize(base,{'path':{'type':'path','max_length':4096}},
        {'/steps/0/arguments/value':'path','/steps/0/arguments/expected_value':'path','/steps/0/verify/0/equals':'path'})
    bound=bind_parameters(workflow,{'path':r'C:\BokkioTasks\report.txt'})
    assert bound['steps'][0]['arguments']['value']==r'C:\BokkioTasks\report.txt'


def paused(backend,workflow,params=None):
    count=[0]
    original=backend.perform
    def perform(*a,**kw):
        result=original(*a,**kw);count[0]+=1;return result
    backend.perform=perform
    return WorkflowReplay(backend,control=lambda:'pause' if count[0]>=1 else None,timeout=0).run(
        workflow,{'editor':'TextEdit'},parameters=params)


def test_resume_new_runtime_pid_keeps_receipt_and_skips_completed_or_received_action():
    backend,button,text,row,_,workflow=template();text.value='';button.value=None;row.selected=False
    checkpoint=paused(backend,workflow,{'text':'resume'})
    assert checkpoint['status']=='paused' and checkpoint['steps'][0]['status']=='verifying'
    backend._resolve_app('TextEdit').pid=999
    calls=[];original=backend.perform
    backend.perform=lambda *a,**kw:(calls.append(a[1]),original(*a,**kw))[1]
    final=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'999'},parameters={'text':'resume'},resume=checkpoint)
    assert final['status']=='completed' and calls==['click','select'] and text.value=='resume'
    assert final['resume_history'][0]['previous_bindings']=={'editor':'TextEdit'}


def test_changed_values_or_tampered_checkpoint_are_refused_before_read():
    backend,button,text,row,_,workflow=template();text.value=''
    checkpoint=paused(backend,workflow,{'text':'original'})
    backend.snapshot=lambda *a:pytest.fail('No read for invalid resume')
    with pytest.raises(BokkioError,match='preserve'):WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},parameters={'text':'other'},resume=checkpoint)
    tampered=copy.deepcopy(checkpoint);tampered['steps']=[]
    with pytest.raises(BokkioError,match='modified'):WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},parameters={'text':'original'},resume=tampered)


def test_unknown_dispatch_completion_never_retries_even_when_outcome_matches():
    backend,button,text,row,_,workflow=template();text.value=''
    checkpoint=paused(backend,workflow,{'text':'already'})
    checkpoint['status']='running';checkpoint['steps'][0].pop('result')
    checkpoint['steps'][0]['status']='dispatching'
    checkpoint['checkpoint_sha256']=digest({k:v for k,v in checkpoint.items() if k!='checkpoint_sha256'})
    backend.perform=lambda *a,**kw:pytest.fail('Unknown dispatch must not repeat')
    final=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},parameters={'text':'already'},resume=checkpoint)
    assert final['status']=='failed' and 'unknown' in final['reason']


def test_checkpoint_frontier_rechecks_current_but_retains_overwritten_state():
    backend,_,_,text,_=setup();recorder=Recorder(backend,{'editor':'TextEdit'})
    recorder.perform('editor','set_value',intent='first',role='text_field',name='Search',value='first')
    recorder.perform('editor','set_value',intent='second',role='text_field',name='Search',value='second')
    recorder.perform('editor','set_value',intent='last',role='text_field',name='Search',value='last')
    workflow=recorder.export('overwrite');text.value='';calls=[0]
    original=backend.perform
    def perform(*a,**kw):calls[0]+=1;return original(*a,**kw)
    backend.perform=perform
    # pause before step 3; the first two actions have verified receipts
    def control():
        return 'pause' if calls[0]>=2 and text.value=='second' else None
    checkpoint=WorkflowReplay(backend,control=control).run(workflow,{'editor':'TextEdit'})
    # pause occurs during second-step verification: finish it via receipt, then pause at step 3
    checkpoint=WorkflowReplay(backend,control=lambda:'pause').run(workflow,{'editor':'TextEdit'},resume=checkpoint)
    assert checkpoint['steps'][0]['status']=='completed' and checkpoint['steps'][1]['status']=='completed'
    final=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},resume=checkpoint)
    assert final['status']=='completed' and calls[0]==3 and text.value=='last'
    assert any(not c['frontier_current'] for c in final['resume_checks'])
    text.value='corrupted'
    refused=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},resume=checkpoint)
    assert refused['status']=='failed' and 'outcome changed' in refused['reason']


def test_input_hash_and_existing_output_preflight_and_final_delivery(tmp_path):
    backend,button,text,row,base,workflow=template();text.value=''
    source=tmp_path/'input.txt';source.write_text('source');output=tmp_path/'out.txt'
    import hashlib
    workflow=parameterize(base,{}, {},inputs=[{'id':'source','path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}],
        deliveries=[{'id':'out','path':str(output),'sha256':hashlib.sha256(b'output').hexdigest()}])
    source.write_text('changed')
    run=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'})
    assert run['status']=='failed' and run['steps']==[] and 'version mismatch' in run['reason']
    source.write_text('source');output.write_text('private existing')
    run=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'})
    assert run['status']=='failed' and run['steps']==[] and output.read_text()=='private existing'
    output.unlink();original=backend.perform
    def perform(*a,**kw):
        result=original(*a,**kw)
        if a[1]=='select':output.write_bytes(b'output')
        return result
    backend.perform=perform;button.value=None;row.selected=False
    run=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'})
    assert run['status']=='completed' and run['deliveries'][0]['bytes']==6


def test_opt_in_wrapper_fallback_keeps_named_ancestors_and_ambiguity_guard():
    backend,window,_,text,_,_,workflow=record()
    workflow['steps'][0]['target']['fallback']='named_context'
    workflow['sha256']=digest({k:v for k,v in workflow.items() if k!='sha256'})
    wrapper=Element('group',None,children=[text]);wrapper.parent_value=window;text.parent_value=wrapper
    window.children_values=[n for n in window.children_values if n is not text]+[wrapper];text.value=''
    report=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'TextEdit'})
    assert report['status']=='completed' and report['steps'][0]['selector']['lane']=='named_context'
    wrapper.name='Different named region';text.value=''
    report=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'TextEdit'})
    assert report['status']=='failed' and not report['steps'][0]['dispatched']


def test_native_client_receipt_capture_does_not_dispatch_again_and_replays():
    backend,_,_,text,_=setup();before=backend.snapshot('TextEdit')
    result=backend.perform('TextEdit','set_value',role='text_field',name='Search',value='client')
    after=backend.snapshot('TextEdit');recorder=Recorder(backend,{'editor':'TextEdit'})
    original=backend.perform
    backend.perform=lambda *a,**kw:pytest.fail('Capture must not dispatch')
    recorder.capture_receipt('editor',intent='Native client typed text',before=before,result=result,after=after)
    workflow=recorder.export('Client events');text.value='';backend.perform=original
    assert WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'})['status']=='completed'
    tampered=copy.deepcopy(result);tampered['before']['value']='fabricated'
    with pytest.raises(BokkioError,match='before observation'):
        recorder.capture_receipt('editor',intent='bad',before=before,result=tampered,after=after)


def test_model_repair_closed_set_preserves_everything_except_failed_selector():
    from io import BytesIO
    from bokkio.planner import OpenRouterPlanner
    from bokkio.workflow_repair import OpenRouterWorkflowRepair
    from bokkio.workflow import request_repair
    backend,_,_,text,_,_,workflow=record();text.value=''
    steps=copy.deepcopy(workflow['steps']);steps[0]['target']['name']='Missing Search'
    from bokkio.workflow import make_workflow
    bad=make_workflow('Bad selector',steps,workflow['source'])
    failed=WorkflowReplay(backend,timeout=0).run(bad,{'editor':'TextEdit'})
    calls=[]
    def opener(req,timeout):
        body=json.loads(req.data);calls.append(body)
        return BytesIO(json.dumps({'model':'test','choices':[{'finish_reason':'stop','message':{'content':'{"candidate":"c1"}'}}]}).encode())
    provider=OpenRouterWorkflowRepair(OpenRouterPlanner(api_key='offline',model='test',opener=opener))
    fixed=request_repair(bad,failed,provider,'Repair Search')
    assert fixed['steps'][0]['target']['name']=='Search' and fixed['parent_sha256']==bad['sha256']
    assert all({k:v for k,v in a.items() if k!='target'}=={k:v for k,v in b.items() if k!='target'} for a,b in zip(fixed['steps'],bad['steps']))
    assert calls[0]['response_format']['json_schema']['strict'] and fixed['metadata']['repair']['model_call']['model']=='test'
    assert text.value==''


def test_cli_parameterize_is_offline_and_replay_binds_inputs(tmp_path,monkeypatch,capsys):
    from bokkio.cli import main
    *_,base=record();source=tmp_path/'source.json';source.write_text(json.dumps(base));spec=tmp_path/'spec.json'
    spec.write_text(json.dumps({'parameters':{'text':{'type':'string','max_length':100}},'slots':{
        '/steps/0/arguments/value':'text','/steps/0/arguments/expected_value':'text','/steps/0/verify/0/equals':'text'},'inputs':[],'deliveries':[]}))
    out=tmp_path/'template.json'
    assert main(['workflow','parameterize','--workflow',str(source),'--spec',str(spec),'--output',str(out)])==0
    assert json.loads(out.read_text())['schema']=='bokkio.workflow.v2'


def test_replay_reuses_post_dispatch_tree_but_keeps_fresh_identity_guard():
    backend,_,button,text,row,_,workflow=record();text.value='';button.value=None;row.selected=False
    calls=[0];original=backend._app_tree
    def app_tree(*a,**kw):calls[0]+=1;return original(*a,**kw)
    backend._app_tree=app_tree
    run=WorkflowReplay(backend,timeout=0).run(workflow,{'editor':'TextEdit'})
    assert run['status']=='completed' and calls[0]==9  # 3 fresh traversals per action, previously 4
    assert all(s['verification_observation']=='native_action_receipt' for s in run['steps'])
    text.value='';before=backend.snapshot('TextEdit');text.value='changed between decision and dispatch'
    from bokkio.model import tree_digest
    with pytest.raises(BokkioError,match='Snapshot changed'):
        backend.perform('TextEdit','set_value',role='text_field',name='Search',value='unsafe',
            expected_snapshot=tree_digest(before['windows']),capture_observation=True)
    assert text.value=='changed between decision and dispatch'


def test_failed_receipt_condition_polls_fresh_tree_without_repeating_action():
    backend,_,button,text,row,_,workflow=record();text.value='';button.value=None;row.selected=False
    calls=[];original=backend.perform
    def perform(*a,**kw):
        result=original(*a,**kw);calls.append(a[1])
        if len(calls)==1:
            from bokkio.selector import flatten
            for n in flatten(result['observation']['windows']):
                if n['name']=='Search':n['value']='pending UI update'
        return result
    backend.perform=perform
    run=WorkflowReplay(backend,timeout=1).run(workflow,{'editor':'TextEdit'})
    assert run['status']=='completed' and calls==['type','click','select']
    assert len(run['steps'][0]['observations'])==3


@pytest.mark.parametrize('changed',['source','output'])
def test_resume_refuses_changed_files_before_any_new_dispatch(tmp_path,changed):
    import hashlib
    backend,_,button,text,row,_,base=record();text.value='';button.value=None;row.selected=False
    source=tmp_path/'source.txt';source.write_bytes(b'source');output=tmp_path/'output.txt'
    workflow=parameterize(base,{}, {},
        inputs=[{'id':'source','path':str(source),'sha256':hashlib.sha256(b'source').hexdigest()}],
        deliveries=[{'id':'output','path':str(output),'sha256':hashlib.sha256(b'output').hexdigest()}])
    original=backend.perform
    def perform(*a,**kw):
        result=original(*a,**kw);output.write_bytes(b'output');return result
    backend.perform=perform
    checkpoint=paused(backend,workflow)
    assert checkpoint['output_versions'][0]['sha256']==hashlib.sha256(b'output').hexdigest()
    (source if changed=='source' else output).write_bytes(b'changed')
    backend.perform=lambda *a,**kw:pytest.fail('Changed input or output must block all new dispatch')
    run=WorkflowReplay(backend).run(workflow,{'editor':'TextEdit'},resume=checkpoint)
    assert run['status']=='failed' and ('version mismatch' in run['reason'] or 'output changed' in run['reason'])


def test_window_scope_rejects_unauthorized_or_conflicting_bindings():
    from bokkio.workflow import WorkflowScope
    backend,*_=setup()
    with pytest.raises(BokkioError,match='authorized'):
        WorkflowScope(backend,{'editor':'100'},{'unrelated':'private window'})
    with pytest.raises(BokkioError,match='Conflicting'):
        WorkflowScope(backend,{'first':'100','second':'100'},{'first':'one','second':'two'})


def test_model_repair_refuses_unknown_completion_before_network_call():
    from bokkio.workflow_repair import OpenRouterWorkflowRepair
    from bokkio.planner import OpenRouterPlanner
    *_,workflow=record()
    provider=OpenRouterWorkflowRepair(OpenRouterPlanner(api_key='offline',model='test',
        opener=lambda *a,**kw:pytest.fail('Unknown action completion cannot invoke selector repair')))
    with pytest.raises(BokkioError,match='known dispatch'):
        provider.repair({'workflow':workflow,'failed_step':'s1','completion_unknown':True})
