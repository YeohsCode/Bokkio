import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

from bokkio.outlook_graph import GraphPowerShell, GraphError, interval
from bokkio.local_runtime import LocalRuntime
from bokkio.sdk import Client


def test_graph_session_and_query_do_not_enumerate_desktop(tmp_path,monkeypatch):
    class NoDesktop:
        def apps(self):raise AssertionError('API task touched desktop Accessibility')
    runtime=LocalRuntime(tmp_path,NoDesktop())
    monkeypatch.setattr(GraphPowerShell,'account',lambda _: 'owned@example.invalid')
    monkeypatch.setattr(GraphPowerShell,'unread',lambda _,start,end:{'count':7,'account':'owned@example.invalid','source':'fixture'})
    client=Client(runtime);client.open(apps=[])
    assert client.call('outlook.status')['result']['configured']
    result=client.call('outlook.unread',{'start':'2026-10-12T00:00:00+08:00','end':'2026-10-16T12:00:00+08:00'})
    assert result['status']=='completed' and result['result']['count']==7
    assert client.call('session.close')['status']=='completed'
    assert runtime._backend.__class__ is NoDesktop


def test_graph_dates_require_timezone_and_preserve_exact_interval():
    assert interval('2026-10-12T00:00:00+08:00','2026-10-16T12:00:00+08:00')==('2026-10-11T16:00:00+00:00','2026-10-16T04:00:00+00:00')
    for start,end in [('2026-10-12','2026-10-16'),('2026-10-12T00:00:00Z','2026-10-11T00:00:00Z'),("'; Remove-Item /",'2026-10-16T00:00:00Z')]:
        with pytest.raises(ValueError):interval(start,end)


@pytest.fixture
def graph_process(tmp_path,monkeypatch):
    # A real child process models a blocked external authentication challenge.
    script=tmp_path/'bridge.py'
    script.write_text("""import sys,json,time
r=json.loads(sys.stdin.readline())
print(json.dumps({'kind':'challenge','code':'OWNED-FIXTURE','url':'https://microsoft.com/devicelogin'}),flush=True)
time.sleep(30)
""")
    from bokkio import outlook_graph
    real=outlook_graph.subprocess.Popen
    monkeypatch.setattr(GraphPowerShell,'executable',lambda _:sys.executable)
    monkeypatch.setattr(outlook_graph.subprocess,'Popen',lambda argv,**kw:real([sys.executable,str(script)],**kw))
    return GraphPowerShell(tmp_path/'state')


def test_background_query_stops_device_challenge_without_user_prompt(graph_process):
    seen=[];started=time.monotonic()
    result=graph_process.run('check',challenge=seen.append)
    assert result['status']=='needs_login' and seen==[]
    assert time.monotonic()-started<5


def test_explicit_login_exposes_challenge_and_can_be_cancelled(graph_process):
    stop=threading.Event();seen=[]
    def challenge(value):seen.append(value);stop.set()
    assert graph_process.run('connect',challenge=challenge,stop=stop)['status']=='cancelled'
    assert seen==[{'url':'https://microsoft.com/devicelogin','code':'OWNED-FIXTURE'}]
    assert not graph_process.profile.exists()


def test_login_result_after_non_newline_console_prompt(graph_process):
    (graph_process.state.parent/'bridge.py').write_text("""import sys,json,time
json.loads(sys.stdin.readline())
print('To sign in, use https://microsoft.com/devicelogin and enter the code OWNEDTEST to authenticate.',end='',flush=True)
time.sleep(.05)
print(json.dumps({'kind':'result','status':'connected','account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.ReadBasic']}),flush=True)
""")
    challenges=[]
    assert graph_process.run('connect',challenge=challenges.append)['status']=='connected'
    assert challenges[0]['code']=='OWNEDTEST'
    assert graph_process.account()=='fixture@example.invalid'


def test_connected_profile_saves_only_public_identity(tmp_path,monkeypatch):
    from bokkio import outlook_graph
    script=tmp_path/'bridge.py';script.write_text("import sys,json\njson.loads(sys.stdin.readline())\nprint(json.dumps({'kind':'result','status':'connected','account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.ReadBasic'],'access_token':'must-not-persist'}))")
    real=outlook_graph.subprocess.Popen
    monkeypatch.setattr(GraphPowerShell,'executable',lambda _:sys.executable)
    monkeypatch.setattr(outlook_graph.subprocess,'Popen',lambda argv,**kw:real([sys.executable,str(script)],**kw))
    graph=GraphPowerShell(tmp_path/'state');graph.run('connect')
    assert json.loads(graph.profile.read_text())=={'account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.ReadBasic']}


def test_unconnected_graph_does_not_start_authentication(tmp_path,monkeypatch):
    monkeypatch.setattr(GraphPowerShell,'run',lambda *a,**k:pytest.fail('Unexpected login'))
    with pytest.raises(GraphError,match='连接 Outlook'):
        GraphPowerShell(tmp_path).unread('2026-10-12T00:00:00Z','2026-10-16T00:00:00Z')
