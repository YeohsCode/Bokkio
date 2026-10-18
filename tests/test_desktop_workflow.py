import copy,os
import pytest
from test_runtime_workflow import setup,document,installed_path
from bokkio.runtime_workflow import SCHEMA_V2,validate_document,find_target
from bokkio.anchored_input import prepare_target
from bokkio.model import BokkioActionRefused
from bokkio.local_runtime import LocalRuntime
from bokkio.sdk import Client

def v2(setup):
    desktop,client,runner,doc,library=setup
    doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc=library.save(doc,doc['sha256']);return desktop,client,runner,doc,library

def test_parameters_freeze_and_verify(setup):
    desktop,client,runner,doc,library=v2(setup)
    doc['parameters']={'text':{'type':'string','default':'初始'}};doc['steps'][0]['arguments']['value']='${text}';doc['steps'][0]['verify'][0]['equals']='${text}'
    doc=library.save(doc,doc['sha256']);run=runner.start(doc,parameters={'text':'中文替换'})
    assert run['workflow_sha256']==doc['sha256'] and run['bound_sha256']!=doc['sha256']
    assert runner.run(run['id'])['status']=='completed' and desktop.value=='中文替换'
    assert doc['steps'][0]['arguments']['value']=='${text}'

def test_breakpoint_single_continue_repeat(setup):
    desktop,_,runner,doc,library=v2(setup);first=doc['steps'][0];first['breakpoint']=True
    second=copy.deepcopy(first);second.update(id='second',breakpoint=False);doc['steps'].append(second);doc=library.save(doc,doc['sha256'])
    run=runner.start(doc,repeat=2,single=True);result=runner.run(run['id']);assert result['status']=='paused' and desktop.clicks==0
    result=runner.resume(run['id']);assert result['status']=='paused' and desktop.clicks==1 and result['index']==1
    result['single']=False;runner._save(result);result=runner.resume(run['id']);assert result['status']=='paused' and result['cycle']==2 and desktop.clicks==2
    assert runner.resume(run['id'])['status']=='completed' and desktop.clicks==4

def test_disabled_final_step_and_condition_repeat(setup):
    desktop,_,runner,doc,library=v2(setup)
    step=copy.deepcopy(doc['steps'][0]);step.update(id='check',kind='check',action='check',arguments={},verify=[{'role':'text_field','name':'Input','field':'present','equals':True}]);doc['steps'].append(step)
    disabled=copy.deepcopy(step);disabled.update(id='disabled',enabled=False);doc['steps'].append(disabled);doc=library.save(doc,doc['sha256'])
    r=runner.run(runner.start(doc,repeat=3)['id']);assert r['status']=='completed' and desktop.clicks==3 and len(r['steps'])==9

def test_anchor_follows_window_and_ref_change(setup):
    desktop,*_=setup;before=desktop.snapshot(str(os.getpid()));desktop.x=900;desktop.ref='new';fresh=desktop.snapshot(str(os.getpid()))
    target,request=prepare_target(before,fresh,{'app':str(os.getpid()),'ref':'input','action':'click','x':.25,'y':.75})
    assert target['ref']=='new' and request['x']==925 and request['y']==25
    desktop.duplicate=True
    with pytest.raises(BokkioActionRefused):prepare_target(before,desktop.snapshot(str(os.getpid())),{'app':str(os.getpid()),'ref':'input','action':'click'})

def test_local_direct_and_birth_identity(setup,tmp_path):
    desktop,*_=setup;runtime=LocalRuntime(tmp_path/'direct',desktop,lambda p:'birth');client=Client(runtime);client.open()
    observed=client.call('desktop.observe',{'app':str(os.getpid()),'window':'Lab Window'})
    result=client.call('desktop.act',{'app':str(os.getpid()),'window':'Lab Window','observation_id':observed['result']['observation_id'],'ref':'input','action':'set_value','value':'direct'})
    assert result['status']=='verified' and desktop.value=='direct' and runtime.store.approvals()==[]
    runtime.birth_probe=lambda p:'different';r=client.call('desktop.observe',{'app':str(os.getpid()),'window':'Lab Window'});assert r['status']=='denied'

def test_reject_invalid_parameter_and_flag(setup):
    _,_,runner,doc,_=v2(setup)
    with pytest.raises(ValueError):runner.start(doc,parameters={'missing':'bad'})
    doc['steps'][0]['enabled']='yes'
    with pytest.raises(ValueError):validate_document(doc)


def test_archived_workflow_restores_history(setup):
    _,_,_,doc,library=setup
    library.archive(doc['id'],doc['sha256'])
    assert library.list()==[] and library.archived()[0]['id']==doc['id']
    restored=library.restore(doc['id'],doc['sha256'])
    assert restored==doc and library.revisions(doc['id'])==[1]


def test_parameter_values_do_not_bind_app_identity(setup):
    _,_,runner,doc,library=v2(setup)
    doc['parameters']={'app':{'type':'string','default':'changed'}}
    doc['apps']['lab']['name']='Lab'
    r=runner.start(doc,parameters={'app':'different'})
    assert r['workflow']['apps']==doc['apps']


def test_local_session_accepts_application_name_case(setup,tmp_path):
    desktop,*_=setup;runtime=LocalRuntime(tmp_path/'case',desktop,lambda p:'birth');client=Client(runtime)
    opened=client.open(apps=['LAB'])
    assert opened['status']=='completed'
    assert runtime._session(client.session_id)['bindings'][str(os.getpid())]['name']=='Lab'


def test_record_canvas_focus_is_not_substituted_for_mouse_click(setup):
    from bokkio.manual_recording import ManualRecorder
    desktop,client,*_=setup
    original=desktop.snapshot
    def snapshot(*args,**kwargs):
        value=original(*args,**kwargs);canvas=value['windows'][0]['children'][0];canvas.update(role='custom',name='Canvas',actions=['focus']);canvas['platform_data']={};canvas['bounds']={'x':10,'y':20,'width':100,'height':60};return value
    desktop.snapshot=snapshot
    client.open(apps=['Lab'])
    recorder=ManualRecorder(client,[{'pid':os.getpid(),'name':'Lab'}])
    recorder.ingest({'pid':os.getpid(),'kind':'click','role':'custom','name':'Canvas','window':'Lab Window','x':40,'y':35})
    step=recorder.preview()['document']['steps'][0]
    assert step['kind']=='input' and step['action']=='click' and step['target']['point']=={'x':.3,'y':.25}


def test_global_recording_registers_new_apps_without_late_snapshot(setup):
    from bokkio.manual_recording import ManualRecorder
    desktop,client,*_=setup
    rec=ManualRecorder(client,[],all_apps=True,excluded_pids={99})
    def event(pid,path,kind='click',**extra):
        return {'captured':True,'pid':pid,'app':{'name':path.rsplit('/',1)[-1],'path':path},'kind':kind,
                'window':'Before click','window_identity':'ax:1','role':'AXButton','name':'Open',
                'ancestors':[{'role':'AXWindow','name':'Before click'}],
                'bounds':{'x':10,'y':20,'width':40,'height':30},'x':20,'y':35,**extra}
    # The dialog no longer exists when Python consumes its click. No observation may run.
    desktop.snapshot=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('late target lookup'))
    rec.ingest(event(99,installed_path('Bokkio')))
    rec.ingest(event(10,installed_path('First')))
    rec.ingest(event(20,installed_path('Second')))
    rec.ingest(event(21,installed_path('First')))
    doc=rec.preview()['document'];assert len(doc['apps'])==2
    assert [s['app'] for s in doc['steps']]==['app1','app2','app1']
    assert all(s['kind']=='input' and s['target']['point']=={'x':.25,'y':.5} for s in doc['steps'])
    validate_document(doc)


def test_native_recorded_edits_keep_distinct_controls_and_skip_app_switch(setup):
    from bokkio.manual_recording import ManualRecorder
    _,client,*_=setup;rec=ManualRecorder(client,[],all_apps=True)
    event={'captured':True,'pid':1,'app':{'name':'Editor','path':installed_path('Editor')},'kind':'edit','role':'AXTextArea','name':'',
           'window':'Doc','ancestors':[{'role':'AXScrollArea','name':''},{'role':'AXWindow','name':'Doc'}],'identifier':'first','value':'one'}
    rec.ingest(event);rec.ingest({**event,'value':'two'});rec.ingest({**event,'identifier':'second','value':'three'})
    rec.ingest({**event,'kind':'key','key':'Command+Tab'})
    steps=rec.doc['steps'];assert len(steps)==2 and steps[0]['arguments']['value']=='two'
    assert steps[0]['target']['role']=='text_area' and steps[0]['target']['name'] is None
    assert steps[0]['target']['ancestors'][0]=={'role':'group','name':None}
    validate_document(rec.doc)


def test_native_capture_rebinds_against_driver_role_normalization(setup):
    from bokkio.manual_recording import ManualRecorder
    _,client,*_=setup;rec=ManualRecorder(client,[],all_apps=True)
    rec.ingest({'captured':True,'pid':1,'app':{'name':'Editor','path':installed_path('Editor')},'kind':'edit','role':'AXTextArea','name':'',
                'window':'Doc','ancestors':[{'role':'AXScrollArea','name':''},{'role':'AXWindow','name':'Doc'}],'identifier':'editor','value':'demo'})
    # xa11y normalizes AXScrollArea to group, rather than scroll_area.
    nodes=[{'ref':'win','role':'window','name':'Doc','parent':None,'platform_data':{'ax_role':'AXWindow'}},
           {'ref':'scroll','role':'group','name':None,'parent':'win','platform_data':{'ax_role':'AXScrollArea'}},
           {'ref':'editor','role':'text_area','name':None,'parent':'scroll','platform_data':{'ax_role':'AXTextArea','ax_identifier':'editor'}}]
    assert find_target({'windows':nodes},rec.doc['steps'][0]['target'],'__input__')['ref']=='editor'
    nodes[1]['platform_data']['ax_role']='AXGroup'
    with pytest.raises(ValueError,match='unavailable or ambiguous'):find_target({'windows':nodes},rec.doc['steps'][0]['target'],'__input__')


def test_captured_drag_uses_containing_window_for_destination(setup):
    from bokkio.manual_recording import ManualRecorder
    _,client,*_=setup;rec=ManualRecorder(client,[],all_apps=True)
    event={'captured':True,'pid':1,'app':{'name':'Lab','path':installed_path('Lab')},'kind':'drag','role':'AXButton','name':'Item',
           'window':'Doc','ancestors':[{'role':'AXWindow','name':'Doc'}],'bounds':{'x':20,'y':30,'width':20,'height':20},
           'window_target':{'role':'AXWindow','name':'Doc','ancestors':[],'bounds':{'x':10,'y':20,'width':500,'height':300}},
           'x':30,'y':40,'end_x':300,'end_y':200}
    rec.ingest(event);step=rec.doc['steps'][0]
    assert step['target']['role']=='window' and step['target']['point']=={'x':.04,'y':20/300}
    assert step['arguments']['end_x']==.58 and step['arguments']['end_y']==.6
    validate_document(rec.doc)
    with pytest.raises(ValueError,match='outside'):rec.ingest({**event,'end_x':999})


def test_cancelled_session_race_is_not_reported_as_replay_failure(setup,monkeypatch):
    desktop,_,runner,doc,_=v2(setup);run=runner.start(doc)
    def stopped_before_observation(*args):
        runner.cancel(run['id'])
        raise ValueError('Session unavailable, expired or owned by another OS user')
    monkeypatch.setattr(runner,'_context_step',stopped_before_observation)
    result=runner.run(run['id'])
    assert result['status']=='cancelled' and desktop.clicks==0
    assert 'error' not in result
