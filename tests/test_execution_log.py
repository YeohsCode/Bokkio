import copy,json,os,time
from bokkio.execution_log import ingest_choice,chat_trace,workflow_trace,ARCHITECTURE
from bokkio.runtime_workflow import WorkflowLibrary
from bokkio.execution_context import parent_operation,workflow_step
from test_runtime_workflow import setup


def notification(kind,data,seq=1):return {'kind':'notification','data':{'method':'session.event','payload':{'event':{'type':kind,'data':data,'time':1000,'seq':seq}}}}

def test_current_desktop_architecture_does_not_claim_jev(tmp_path):
    assert ARCHITECTURE['jev_active'] is False
    job={'id':'a'*32,'prompt':'read editor','status':'running','events':[]}
    tree=chat_trace(job,tmp_path)
    assert tree['children']==[] and tree['architecture']['selection'].startswith('Jev') and tree['architecture']['jev_active'] is False


def test_returned_failure_is_not_rendered_as_success_and_result_can_arrive_first(tmp_path):
    job={'id':'a'*32,'prompt':'read editor','status':'failed','events':[]}
    result={'status':'denied','operation_id':'op','dispatched':False}
    ingest_choice(job,notification('tool/result',{'message':{'source':{'callId':'call'},'content':[{'type':'text','text':json.dumps(result)}]}}))
    ingest_choice(job,notification('tool/call',{'callId':'call','name':'mcp__bokkio__desktop_act_hash','arguments':json.dumps({'arguments':{'app':'Lab','value':'private text'}})}))
    tree=chat_trace(job,tmp_path);choice=tree['children'][0]
    assert choice['status']=='denied' and choice['children'][0]['status']=='denied'
    assert 'private text' not in json.dumps(tree) and len(tree['children'])==1


def test_runtime_links_by_operation_id_and_task_not_by_adjacent_time(setup):
    desktop,client,_,doc,_=setup;cid='a'*32
    client.open(apps=['Lab'],task_id=cid)
    r=client.call('desktop.windows',{'app':str(os.getpid())});oid=r['operation_id']
    job={'id':cid,'prompt':'read editor','status':'running','events':[]}
    ingest_choice(job,notification('tool/call',{'callId':'call','name':'mcp__bokkio__desktop_windows_hash','arguments':'{}'}))
    before=chat_trace(job,client.runtime.store.root)
    assert before['children'][0]['children']==[]
    assert any(n['status']=='unlinked' for n in before['children'])
    ingest_choice(job,notification('tool/result',{'message':{'source':{'callId':'call'},'content':[{'text':json.dumps(r)}]}}))
    after=chat_trace(job,client.runtime.store.root)
    assert after['children'][0]['children'][0]['operation_id']==oid
    unrelated=chat_trace({**job,'id':'b'*32},client.runtime.store.root)
    assert not any(n.get('events') for choice in unrelated['children'] for n in choice['children'])


def test_workflow_tree_contains_real_driver_receipts_and_preserves_failed_check(setup):
    desktop,client,runner,doc,_=setup;doc=copy.deepcopy(doc);doc['steps'][0]['verify'][0]['equals']='wrong';doc['steps'][0]['timeout']=.01
    run=runner.run(runner.start(doc)['id']);assert run['status']=='failed' and desktop.clicks==1
    tree=workflow_trace(run,client.runtime.store.root)
    assert tree['engine']=='固定 Workflow' and tree['architecture']['jev_active'] is False
    step=tree['children'][0];assert step['status']=='failed' and step['verification']=='failed'
    assert any(n['title']=='desktop.act' and n['status']=='verified' for n in step['children'])
    assert workflow_step.get() is None and parent_operation.get() is None


def test_async_workflow_keeps_parent_operation_across_thread(setup):
    desktop,client,_,doc,_=setup;runtime=client.runtime
    library=WorkflowLibrary(runtime.store.root/'workflows');library.save({k:v for k,v in doc.items() if k!='sha256'})
    runtime.policy['workflows']=[doc['id']]
    with runtime.store.connect() as db:
        scope=runtime._session(client.session_id);scope['workflows']=[doc['id']];db.execute('UPDATE sessions SET policy=? WHERE id=?',(json.dumps(scope),client.session_id))
    r=client.call('workflow.run',{'workflow_id':doc['id']});assert r['status']=='completed'
    runtime._workflow_threads[r['result']['run_id']].join(5)
    events=runtime.store.query(kind='request.received')
    actions=[e for e in events if e['data']['tool']=='desktop.act']
    assert len(actions)==1 and actions[0]['data']['parent_operation']==r['operation_id']
    assert actions[0]['data']['workflow_step']['run_id']==r['result']['run_id']
    assert parent_operation.get() is None


def test_choices_survive_raw_notification_window_and_cancelled_job_updates_group(setup):
    _,client,*_=setup;cid='a'*32
    client.open(apps=['Lab'],task_id=cid)
    result=client.call('desktop.windows',{'app':str(os.getpid())});oid=result['operation_id']
    job={'id':cid,'prompt':'owned job','status':'cancelled','events':[]}
    ingest_choice(job,notification('tool/call',{'callId':'call','name':'mcp__bokkio__code_run_hash','arguments':'{}'}))
    ingest_choice(job,notification('tool/result',{'message':{'source':{'callId':'call'},'content':[{'text':json.dumps({**result,'status':'queued'})}]}}))
    with client.runtime.store.connect() as db:
        db.execute('UPDATE operations SET status=?,result=? WHERE id=?',('cancelled',json.dumps({**result,'status':'cancelled','dispatched':True}),oid))
    # Raw header/delta events can roll out of the UI's notification window.
    job['events']=[notification('step/start',{}) for _ in range(1000)]
    tree=chat_trace(job,client.runtime.store.root)
    assert tree['children'][0]['status']=='cancelled' and tree['counts']['choices']==1
    assert tree['children'][0]['returned_status']=='queued'


def test_cached_operation_references_do_not_invent_duplicate_dispatch(setup):
    _,client,*_=setup;cid='a'*32
    client.open(apps=['Lab'],task_id=cid)
    r=client.call('desktop.windows',{'app':str(os.getpid())})
    again=client.call('desktop.windows',{'app':str(os.getpid())},r['operation_id'])
    job={'id':cid,'prompt':'read editor','status':'completed','events':[]}
    for cid2,result in [('first',r),('second',again)]:
        ingest_choice(job,notification('tool/call',{'callId':cid2,'name':'mcp__bokkio__desktop_windows_hash','arguments':'{}'}))
        ingest_choice(job,notification('tool/result',{'message':{'source':{'callId':cid2},'content':[{'text':json.dumps(result)}]}}))
    tree=chat_trace(job,client.runtime.store.root)
    choices=[n for n in tree['children'] if n.get('call_id')]
    assert len(choices)==2 and all(n['children'][0]['reused_operation'] for n in choices)
    assert len(client.runtime.store.query(operation_id=r['operation_id'],kind='execution.intent'))==1


def test_stopped_sdk_choice_without_result_is_not_left_running(tmp_path):
    job={'id':'a'*32,'prompt':'owned cancelled task','status':'cancelled','events':[]}
    ingest_choice(job,notification('tool/call',{'callId':'unfinished','name':'mcp__bokkio__desktop_act_hash','arguments':'{}'}))
    tree=chat_trace(job,tmp_path)
    assert tree['children'][0]['status']=='cancelled' and tree['children'][0]['children']==[]
