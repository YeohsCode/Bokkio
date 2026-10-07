import copy
import pytest

from bokkio.agent import DesktopAgent
from bokkio.arena import NativeArenaAgent, WAAAgentAdapter, WAAEnvironmentBridge
from bokkio.model import BokkioError
from test_agent import Planner
from test_cli import backend_with_button
from test_decision import Provider


def test_runner_must_dispatch_and_cannot_change_or_replay_action(tmp_path):
    backend, _, button = backend_with_button()
    arena = NativeArenaAgent(lambda: backend,
        lambda gated: DesktopAgent(gated, Planner(), Provider()),
        ['TextEdit'], tmp_path/'trace.json', timeout=5)
    try:
        action, = arena.predict('Click Save', {})
        assert button.value != 'pressed'
        with pytest.raises(BokkioError, match='pending'):
            arena.predict('Click Save', {})
        altered = copy.deepcopy(action)
        altered['action'] = 'delete'
        with pytest.raises(BokkioError, match='altered'):
            arena.step(altered)
        assert button.value != 'pressed'
        receipt = arena.step(action)
        assert receipt['passed'] and button.value == 'pressed'
        with pytest.raises(BokkioError, match='replayed'):
            arena.step(action)
        assert arena.predict('Click Save', {}) == ['DONE']
        assert arena.predict('Click Save', {}) == ['DONE']
        assert len(arena.steps) == arena.trace['actions'] == 1
        assert sum(e['kind']=='action' for e in arena.trace['events']) == 1
    finally:
        arena.close()


def test_reset_cancels_undispatched_action(tmp_path):
    backend, _, button = backend_with_button()
    arena = NativeArenaAgent(lambda: backend,
        lambda gated: DesktopAgent(gated, Planner(), Provider()),
        ['TextEdit'], tmp_path/'trace.json', timeout=5)
    old, = arena.predict('Click Save', {})
    arena.reset()
    assert button.value != 'pressed'
    with pytest.raises(BokkioError):
        arena.step(old)
    new, = arena.predict('Click Save', {})
    assert old['token'] != new['token']
    arena.step(new)
    assert arena.predict('Click Save', {}) == ['DONE']
    arena.close()


def test_failed_dispatch_is_one_step_and_recovery_remains_in_worker(tmp_path):
    class Backend:
        calls=0
        def perform(self, app, action, **kwargs):
            self.calls+=1
            if self.calls==1:raise BokkioError('stale snapshot')
            return {'native_receipt':self.calls}
    backend=Backend()
    class Agent:
        def __init__(self,gated):self.backend=gated
        def run(self,*args):
            try:self.backend.perform('7','click',ref=1)
            except BokkioError:pass
            self.backend.perform('7','click',ref=2)
            return {'status':'completed'}
    arena=NativeArenaAgent(lambda:backend,Agent,['7'],tmp_path/'trace.json',timeout=5)
    first,=arena.predict('Recover',{})
    assert backend.calls==0
    receipt=arena.step(first)
    assert not receipt['passed'] and receipt['error']=='stale snapshot'
    second,=arena.predict('Recover',{})
    assert backend.calls==1
    assert arena.step(second)['passed']
    assert arena.predict('Recover',{})==['DONE']
    assert backend.calls==len(arena.steps)==2
    arena.close()


def test_planner_window_allowlist_uses_the_same_snapshot(tmp_path):
    backend, window, _=backend_with_button()
    original=backend.snapshot
    calls=[]
    def snapshot(*args,**kwargs):
        calls.append(args)
        return original(*args,**kwargs)
    backend.snapshot=snapshot
    def changed_windows(app):
        raise AssertionError('Second traversal could expose a different native state')
    backend.windows=changed_windows
    arena=DesktopAgent(backend,Planner(),Provider())
    result=arena.run('Click Save',['TextEdit'],tmp_path/'trace.json',plan_only=True)
    assert result['status']=='planned' and len(calls)==1
    observed=next(e['observations']['TextEdit'] for e in result['events'] if e['kind']=='planner_observations')
    assert observed['windows']==[{'name':'Untitled'}]


def test_actual_waa_runner_contract_and_environment_dispatch(tmp_path):
    from types import SimpleNamespace
    backend,_,button=backend_with_button()
    def native():return NativeArenaAgent(lambda:backend,
        lambda gated:DesktopAgent(gated,Planner(),Provider()),['TextEdit'],tmp_path/'trace.json',timeout=5)
    adapter=WAAAgentAdapter(native())
    environment=SimpleNamespace(reset=lambda **kwargs:{'initial':True},
        _get_obs=lambda:{'native_value':button.value},evaluate=lambda:0.75,action_history=[])
    bridge=WAAEnvironmentBridge(environment,adapter,lambda task,obs:native())
    assert bridge.reset({'id':'fixed'})=={'initial':True}
    response,actions,logs,updates=adapter.predict('Click Save',{})
    assert updates is None and len(actions)==1 and logs['native_steps']==0
    assert button.value!='pressed'
    with pytest.raises(BokkioError,match='terminal'):
        bridge.step('DONE')
    obs,reward,done,info=bridge.step(actions[0])
    assert obs['native_value']=='pressed' and not done and reward==0 and info['step']==1
    _,actions,_,_=adapter.predict('Click Save',obs)
    assert actions==['DONE']
    assert bridge.step(actions[0])[2]
    assert len(environment.action_history)==2 and bridge.evaluate()==0.75
    adapter.reset()


def test_blocked_agent_returns_fail_without_dispatch(tmp_path):
    backend, _, button = backend_with_button()
    arena = NativeArenaAgent(lambda: backend,
        lambda gated: DesktopAgent(gated, Planner({'goal':'Sensitive', 'steps':[
            {**Planner().result['steps'][0], 'risk':'external'}]}), Provider()),
        ['TextEdit'], tmp_path/'trace.json', timeout=5)
    assert arena.predict('Click Save', {}) == ['FAIL']
    assert not arena.steps and button.value != 'pressed'
    arena.close()
