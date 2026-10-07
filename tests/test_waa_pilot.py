"""Pinned scoring rejects runtime completion without persisted correct output."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import verify_waa_pilot as pilot
sys.path.pop(0)

BUNDLE=Path(__file__).parents[1]/'fixtures/waa-pilot'


def test_fixed_manifest_and_task_hashes():
    assert pilot.hash_file(BUNDLE/'manifest.json')==pilot.MANIFEST_SHA256
    manifest=json.loads((BUNDLE/'manifest.json').read_text())
    catalog=json.loads((Path(__file__).parents[1]/'docs/benchmarks/windows-arena-catalog.json').read_text())
    selection=json.loads((Path(__file__).parents[1]/'docs/benchmarks/windows-arena-pilot.json').read_text())
    assert [t['path'] for t in manifest['tasks']]==[t['path'] for t in selection['tasks']]
    for task in manifest['tasks']:
        assert pilot.hash_file(BUNDLE/str(task['index'])/'original.json')==task['sha256']
        for asset in task['assets']:
            assert pilot.hash_file(BUNDLE/str(task['index'])/asset['file'])==asset['sha256']
    assert catalog['revision']==manifest['revision']


def test_modified_evaluator_is_rejected_before_import(tmp_path):
    (tmp_path/'upstream_evaluator.py').write_text('raise AssertionError("must not import")')
    with pytest.raises(ValueError,match='export changed'):
        pilot.load_evaluator(tmp_path)


def test_upstream_evaluation_and_fail_semantics(tmp_path):
    module=pilot.load_evaluator(BUNDLE)
    original=json.loads((BUNDLE/'4/original.json').read_text())
    config=pilot.bind_paths(original,tmp_path)
    expected=tmp_path/'Desktop/example.txt';expected.parent.mkdir()
    expected.write_text('original\n')
    actual=tmp_path/'Documents/example_renamed.txt';actual.parent.mkdir()
    cache=tmp_path/'cache';cache.mkdir()
    controller=pilot.Controller(tmp_path,None)
    setup=SimpleNamespace(setup=lambda entries:None)
    score=lambda history:pilot.evaluate(module,config,controller,setup,cache,history)
    assert score(['DONE'])==0
    actual.write_text('wrong\n');assert score(['DONE'])==0
    actual.write_text('original\n');assert score(['DONE'])==1
    assert score(['FAIL'])==0
    with pytest.raises(ValueError,match='outside'):
        controller.get_file(str(tmp_path.parent/'private.txt'))


def test_two_metric_notepad_task_requires_both_existence_and_gold(tmp_path):
    module=pilot.load_evaluator(BUNDLE)
    config=pilot.bind_paths(json.loads((BUNDLE/'1/original.json').read_text()),tmp_path)
    artifact=tmp_path/'Documents/draft.txt';artifact.parent.mkdir()
    cache=tmp_path/'cache';cache.mkdir()
    gold=(BUNDLE/'1/draft_gold.txt').read_bytes()
    (cache/'draft_gold.txt').write_bytes(gold)
    env_setup=SimpleNamespace(setup=lambda entries:None)
    controller=pilot.Controller(tmp_path,None)
    score=lambda:pilot.evaluate(module,config,controller,env_setup,cache,['DONE'])
    assert score()==0
    artifact.write_text('wrong');assert score()==0
    artifact.write_bytes(gold);assert score()==1


def test_pilot_factory_budgets_are_accepted_by_the_runtime():
    from bokkio.agent import DesktopAgent
    # The harness must respect the actual runtime contract before starting UI.
    agent=DesktopAgent(SimpleNamespace(),None,None,**pilot.BUDGETS)
    assert agent.max_actions>0 and agent.max_replans>=0 and agent.max_phases>0


def test_settings_caption_waits_for_registered_application_and_reenumerates(monkeypatch):
    old={'title':'Settings','pid':1,'hwnd':10};new={'title':'Settings','pid':2,'hwnd':20}
    states=iter([[old],[new],[new]]);calls=[]
    ticks=iter([0,0,0.1])
    monkeypatch.setattr(pilot.time,'monotonic',lambda:next(ticks))
    monkeypatch.setattr(pilot.time,'sleep',lambda _:None)
    def resolve(pid,timeout):
        calls.append(pid)
        if pid==1:raise RuntimeError('Application discovery is not ready')
    assert pilot.wait_ready_window('Settings',discover=lambda:next(states),resolve=resolve)==new
    assert calls==[1,2]


def test_window_that_retires_during_binding_is_not_accepted(monkeypatch):
    old={'title':'Settings','pid':1,'hwnd':10};new={'title':'Settings','pid':2,'hwnd':20}
    states=iter([[old],[new],[new],[new]]);calls=[]
    ticks=iter([0,0,0.1])
    monkeypatch.setattr(pilot.time,'monotonic',lambda:next(ticks))
    monkeypatch.setattr(pilot.time,'sleep',lambda _:None)
    assert pilot.wait_ready_window('Settings',discover=lambda:next(states),resolve=lambda pid,timeout:calls.append(pid))==new
    assert calls==[1,2]


def test_ambiguous_ready_windows_are_not_selected_and_deadline_is_sanitized(monkeypatch):
    ticks=iter([0,0,2]);calls=[]
    monkeypatch.setattr(pilot.time,'monotonic',lambda:next(ticks))
    monkeypatch.setattr(pilot.time,'sleep',lambda _:None)
    windows=[{'title':'Settings','pid':1,'hwnd':10},{'title':'Settings','pid':2,'hwnd':20}]
    with pytest.raises(RuntimeError,match='startup deadline'):
        pilot.wait_ready_window('Settings',timeout=1,discover=lambda:windows,resolve=lambda *a,**k:calls.append(a))
    assert calls==[(1,),(2,)]


def test_same_caption_unregistered_core_is_not_a_second_ready_app(monkeypatch):
    core={'title':'Settings','pid':1,'hwnd':10};frame={'title':'Settings','pid':2,'hwnd':20}
    monkeypatch.setattr(pilot.time,'monotonic',lambda:0)
    def resolve(pid,timeout):
        if pid==1:raise RuntimeError('Hidden CoreWindow has no app root')
    assert pilot.wait_ready_window('Settings',discover=lambda:[core,frame],resolve=resolve)==frame


def test_settings_frame_requires_native_focus_before_content_is_available(monkeypatch):
    class Backend:
        focused=False
        calls=[]
        def snapshot(self,app):
            frame={'role':'window','name':'Settings','ref':'frame','actions':['focus'],
                   'state':{},'children':[]}
            if self.focused:
                frame['children']=[{'role':'button','name':'Notifications','ref':'toggle',
                                    'actions':['click'],'state':{'checked':True},'children':[]}]
            return {'windows':[frame]}
        def perform(self,app,action,ref):
            self.calls.append((action,ref));self.focused=True
            return {'action':action,'ref':ref}
    backend=Backend()
    monkeypatch.setattr(pilot,'Xa11yBackend',lambda:backend)
    monkeypatch.setattr(pilot.time,'sleep',lambda _:None)
    result=pilot.notification_native_fixture('owned',True)
    assert backend.calls==[('focus','frame')]
    assert result['before'] is True and result['receipt'] is None
    assert result['navigation']==[{'action':'focus','ref':'frame'}]
