import json
from types import SimpleNamespace
import pytest

from scripts import evaluate_runtime_business as runner


def test_preflight_waits_for_exact_new_pid_registration(monkeypatch,tmp_path):
    seen=[]
    def runtime(state,policy):
        seen.append(policy)
        return SimpleNamespace()
    class Client:
        opens=0
        def __init__(self,runtime):pass
        def open(self):
            type(self).opens+=1
            if self.opens==1:raise RuntimeError('owned PID not registered yet')
        def call(self,tool,args=None):
            if tool=='session.close':return {}
            assert args['app']=='901'
            return {'status':'completed','result':{'nodes':[{'role':'window','name':'Owned'}]}}
    monkeypatch.setattr(runner,'Runtime',runtime)
    monkeypatch.setattr(runner,'Client',Client)
    monkeypatch.setattr(runner.time,'sleep',lambda _:None)
    case={'apps':[{'name':'TextEdit','pid':901,'gui_owned_process':True,'gui_process_started':True,'windows':['Owned']}]}
    assert runner.preflight(case,tmp_path,'gui')['ready']
    assert seen[0]['apps']==['901'] and Client.opens==2


def test_capture_records_are_not_native_source_window_evidence():
    observations=[{'window':'Owned','metadata':{'pid':901}},
                  {'window':'Owned','snapshot':{'app':{'name':'Finder'}}}]
    assert runner.source_window_observed(observations,'Finder','Owned')
    assert not runner.source_window_observed(observations,'Finder','Other')
    assert not runner.source_window_observed(observations[:1],'Finder','Owned')


def test_manual_completion_signal_must_be_successful(tmp_path):
    for status,expected in [('failed',False),('completed',True),('waiting',False)]:
        (tmp_path/'complete.json').write_text(json.dumps({'status':status}))
        assert runner.caller_finished(tmp_path,'codex-current')[0] is expected


@pytest.mark.parametrize('writes,steps,expected',[(61,0,'core_dispatch_budget'),(0,41,'model_turn_budget')])
def test_terminal_actor_cannot_hide_budget_excess(tmp_path,writes,steps,expected):
    from bokkio.runtime import Runtime
    runtime=Runtime(tmp_path/'state')
    for _ in range(writes):runtime.store.emit('request.received',data={'tool':'desktop.act'})
    if steps:
        log=tmp_path/'dsh-home/sessions/session/events.jsonl';log.parent.mkdir(parents=True)
        log.write_text((' {"type":"step/start"}\n')*steps)
    # The caller has already ended before supervision sees it. Limits still
    # belong to the result contract, even though no process remains to stop.
    (tmp_path/'complete.json').write_text('{"status":"completed"}')
    _,reason,_=runner.supervise(None,{},tmp_path,runtime,1)
    assert reason==expected
