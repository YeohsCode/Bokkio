import copy
import json
import os
import threading

import pytest
from bokkio.desktop_decision import DesktopDecisionRuntime, provider_from_environment
from bokkio.execution_log import chat_trace, ingest_choice
from bokkio.local_runtime import LocalRuntime
from bokkio.model import BokkioError, BokkioStaleSnapshot
from bokkio.sdk import Client
from test_runtime_workflow import Desktop
from test_decision import Provider
from test_execution_log import notification


@pytest.fixture
def setup(tmp_path):
    class Native(Desktop):
        def snapshot(self, app, window=None):
            result = super().snapshot(app, window)
            result['windows'][0]['platform'] = 'macos'
            return result
        def perform(self, app, action, **args):
            from bokkio.model import tree_digest
            if tree_digest(self.snapshot(app)['windows']) != args['expected_snapshot']:
                raise BokkioStaleSnapshot('Changed')
            return super().perform(app, action, **args)
    desktop = Native()
    runtime = LocalRuntime(tmp_path/'state', desktop, lambda _: 'birth')
    client = Client(runtime);client.open(apps=['Lab'], task_id='task')
    provider = Provider(choice='set_value')
    provider.model='test-Jev';provider.source='offline'
    bridge = DesktopDecisionRuntime(runtime, lambda: provider)
    args = {'app':'Lab','window':'Lab Window','goal':'Set Input to the allowed value','allowed_values':['中文 Jev']}
    return bridge,client,desktop,provider,args


def test_jev_selects_then_runtime_dispatches_and_reads_back_once(setup):
    bridge,client,desktop,provider,args=setup
    result=bridge.call('desktop.step',args,session_id=client.session_id,operation_id='step')
    assert result['status']=='verified',result
    assert desktop.value=='中文 Jev' and desktop.clicks==1
    assert result['result']['readback']['result']['nodes'][1]['value']=='中文 Jev'
    assert provider.questions['next']['criteria'].keys()=={'focus','set_value'}
    assert bridge.call('desktop.step',args,session_id=client.session_id,operation_id='step')==result
    assert desktop.clicks==1
    events=client.runtime.store.query()
    assert len([e for e in events if e['kind']=='decision.requested'])==1
    assert len([e for e in events if e['kind']=='decision.selected'])==1
    action=[e for e in events if e['kind']=='request.received' and e['data']['tool']=='desktop.act'][0]
    assert action['data']['parent_operation']=='step'
    assert bridge.call('desktop.step',{**args,'goal':'Other'},session_id=client.session_id,operation_id='step')['status']=='denied'
    assert desktop.clicks==1


def test_ui_change_during_jev_rejects_before_dispatch(setup):
    bridge,client,desktop,provider,args=setup
    ask=provider.ask
    def mutate(*a):
        result=ask(*a);desktop.value='changed by user';return result
    provider.ask=mutate
    result=bridge.call('desktop.step',args,session_id=client.session_id)
    assert result['status']=='failed' and result['dispatched'] is False and desktop.clicks==0
    assert 'UI changed' in result['error']


def test_slow_decision_refreshes_expired_observation_without_redispatch(setup):
    bridge,client,desktop,provider,args=setup;ask=provider.ask
    def expire(*a):
        result=ask(*a)
        with client.runtime.store.connect() as db:
            rows=db.execute('SELECT id,payload FROM observations').fetchall()
            for row in rows:
                data=json.loads(row['payload']);data['time']=0
                db.execute('UPDATE observations SET payload=? WHERE id=?',(json.dumps(data),row['id']))
        return result
    provider.ask=expire
    result=bridge.call('desktop.step',args,session_id=client.session_id)
    assert result['status']=='verified' and desktop.clicks==1


def test_cancel_during_jev_never_dispatches(setup):
    bridge,client,desktop,provider,args=setup;ask=provider.ask
    def cancel(*a):
        result=ask(*a);client.call('session.close');return result
    provider.ask=cancel
    result=bridge.call('desktop.step',args,session_id=client.session_id)
    assert result['status']=='failed' and result['dispatched'] is False and desktop.clicks==0


@pytest.mark.parametrize('mode',['low_confidence','unavailable','invalid'])
def test_jev_failures_never_fall_back_to_harness_or_dispatch(setup,mode):
    bridge,client,desktop,provider,args=setup
    if mode=='low_confidence':provider.confidence=.1
    elif mode=='unavailable':provider.ask=lambda *_:(_ for _ in ()).throw(BokkioError('Jev unavailable'))
    else:provider.ask=lambda *_:{'answers':{}}
    result=bridge.call('desktop.step',args,session_id=client.session_id)
    assert result['status']=='failed' and not result['dispatched'] and desktop.clicks==0
    assert client.runtime.store.query(kind='decision.failed')


def test_concurrent_same_operation_does_not_repeat_jev_or_action(setup):
    bridge,client,desktop,provider,args=setup
    entered=threading.Event();release=threading.Event();ask=provider.ask;results=[]
    def wait(*a):entered.set();assert release.wait(5);return ask(*a)
    provider.ask=wait
    thread=threading.Thread(target=lambda:results.append(bridge.call('desktop.step',args,session_id=client.session_id,operation_id='same')))
    thread.start();assert entered.wait(5)
    cached=bridge.call('desktop.step',args,session_id=client.session_id,operation_id='same')
    assert cached['status']=='completion_unknown'
    release.set();thread.join(5)
    assert results[0]['status']=='verified' and desktop.clicks==1


def test_unknown_dispatch_preserved_and_never_repeated(setup,monkeypatch):
    bridge,client,desktop,provider,args=setup
    from bokkio.model import BokkioCompletionUnknown
    def unknown(*a,**k):desktop.clicks+=1;raise BokkioCompletionUnknown('lost native receipt')
    desktop.perform=unknown
    result=bridge.call('desktop.step',args,session_id=client.session_id,operation_id='unknown')
    assert result['status']=='completion_unknown' and result['dispatched']=='unknown'
    assert bridge.call('desktop.step',args,session_id=client.session_id,operation_id='unknown')==result
    assert desktop.clicks==1


def test_jev_log_streams_before_sdk_result_and_links_actual_receipts(setup):
    bridge,client,desktop,provider,args=setup
    result=bridge.call('desktop.step',args,session_id=client.session_id,operation_id='step')
    job={'id':'task','prompt':'edit Lab','status':'running','choices':{}}
    tree=chat_trace(job,client.runtime.store.root)
    selected=next(n for n in tree['children'] if n['engine']=='Jev')
    assert tree['architecture']['jev_active'] is True and tree['counts']['jev_calls']==1
    assert any(n['title']=='desktop.act' and n['status']=='verified' for n in selected['children'])
    ingest_choice(job,notification('tool/call',{'callId':'call','name':'mcp__bokkio__desktop_step_hash','arguments':'{}'}))
    ingest_choice(job,notification('tool/result',{'message':{'source':{'callId':'call'},'content':[{'text':json.dumps(result)}]}}))
    selected=next(n for n in chat_trace(job,client.runtime.store.root)['children'] if n['engine']=='Jev')
    assert selected['call_id']=='call' and selected['operation_id']=='step'


def test_input_keys_pass_through_jev_target_selection(setup,monkeypatch):
    bridge,client,desktop,provider,args=setup;provider.choice='input';calls=[]
    def input_call(method,*a,**kwargs):
        calls.append((method,a));return {'verification':{'status':'executed_not_business_verified'}}
    monkeypatch.setattr('bokkio.anchored_input.perform_anchored',lambda *a,**k:input_call('input',*a,**k))
    result=bridge.call('desktop.step',{**args,'goal':'Press Escape on Input','input':{'action':'key','key':'ESC'}},session_id=client.session_id)
    assert result['status']=='executed',result
    assert provider.questions['next']['criteria'].keys()=={'input'}
    assert calls and result['result']['decision']['action']=='key'


def test_chat_tools_use_jev_entry_but_runtime_and_workflows_keep_native_tools(setup):
    bridge,client,desktop,provider,args=setup
    assert {'desktop.act','desktop.input','desktop.pixel'}.isdisjoint(bridge.tools)
    from bokkio.runtime import TOOLS
    assert {'desktop.act','desktop.input','desktop.pixel'}<=TOOLS and 'desktop.step' not in TOOLS
    assert bridge.call('desktop.act',{},session_id=client.session_id)['status']=='denied'


def test_non_openrouter_planner_key_is_never_sent_to_jev(monkeypatch,tmp_path):
    for name in ('BOKKIO_JEV_API_KEY','OPENROUTER_API_KEY','TYPESAFE_API_KEY'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('BOKKIO_JEV_CONFIG',str(tmp_path/'missing.json'))
    monkeypatch.setenv('BOKKIO_PROVIDER_BASE_URL','https://other.example/v1');monkeypatch.setenv('BOKKIO_PROVIDER_KEY','not-for-jev')
    with pytest.raises(BokkioError,match='Configure a Jev key'):provider_from_environment()
    monkeypatch.setenv('BOKKIO_PROVIDER_BASE_URL','https://openrouter.ai/api/v1')
    provider=provider_from_environment();assert provider.source=='openrouter'


def test_jev_secret_not_written_in_settings(tmp_path):
    from bokkio.desktop_service import DesktopStudio
    studio=DesktopStudio(tmp_path/'service')
    value=studio.route('POST','/api/settings',{'jev_api_key':'test-private-secret'})
    assert value['has_jev_api_key'] is True and 'jev_api_key' not in value
    assert 'test-private-secret' not in studio.config_path.read_text()


def test_chat_capabilities_matches_exposed_decision_tools(setup):
    bridge,client,*_=setup
    result=bridge.call('capabilities')
    assert set(result['result']['tools'])==bridge.tools
    assert result['result']['decision_architecture']['native_selection']=='Jev'


def test_mcp_advertises_step_and_keeps_model_free_transport_separate(tmp_path):
    import asyncio,sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def run():
        params=StdioServerParameters(command=sys.executable,args=['-m','bokkio.desktop_decision','--state',str(tmp_path/'mcp')])
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as client:
                await client.initialize()
                tools={t.name:t for t in (await client.list_tools()).tools}
                assert 'desktop.step' in tools and 'desktop.act' not in tools
                args=tools['desktop.step'].inputSchema['properties']['arguments']
                assert set(args['required'])=={'app','window','goal'}
                assert 'ref' not in args['properties']
                result=await client.call_tool('capabilities',{})
                assert 'desktop.step' in result.structuredContent['result']['tools']
    asyncio.run(run())


def test_stopped_jev_call_does_not_stay_running_in_ui(setup):
    bridge,client,desktop,provider,args=setup
    result=bridge.call('desktop.step',args,session_id=client.session_id,operation_id='pending')
    with client.runtime.store.connect() as db:
        db.execute("UPDATE operations SET status='running',result=NULL WHERE id='pending'")
    tree=chat_trace({'id':'task','prompt':'cancelled','status':'cancelled','choices':{}},client.runtime.store.root)
    assert next(n for n in tree['children'] if n['engine']=='Jev')['status']=='cancelled'
