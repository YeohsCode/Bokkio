import json
import os
from pathlib import Path
import sys
import threading
import time

import pytest

from bokkio.outlook_graph import GraphPowerShell, GraphError, graph_request
from bokkio.local_runtime import LocalRuntime
from bokkio.sdk import Client


def test_graph_session_and_query_do_not_enumerate_desktop(tmp_path,monkeypatch):
    class NoDesktop:
        def apps(self):raise AssertionError('API task touched desktop Accessibility')
    runtime=LocalRuntime(tmp_path,NoDesktop())
    monkeypatch.setattr(GraphPowerShell,'account',lambda _: 'owned@example.invalid')
    monkeypatch.setattr(GraphPowerShell,'request',lambda _,path,query,max_pages:{'data':{'value':[{'id':'owned','body':{'content':'actual fixture body'}}]},'complete':True,'source':'fixture'})
    client=Client(runtime);client.open(apps=[])
    assert client.call('outlook.status')['result']['configured']
    result=client.call('outlook.request',{'path':'/me/messages','query':{'$select':'id,body'}})
    assert result['status']=='completed' and result['result']['data']['value'][0]['body']['content']=='actual fixture body'
    assert client.call('session.close')['status']=='completed'
    assert runtime._backend.__class__ is NoDesktop


def test_graph_query_preserves_caller_parameters_and_opaque_next_link():
    from urllib.parse import parse_qs,urlsplit
    query={'$filter':"receivedDateTime ge 2026-10-16T00:00:00Z and isRead eq false",'$select':'id,body','$search':'"budget"'}
    uri=graph_request('/me/messages',query)
    assert '%20' in uri and '+' not in uri
    assert parse_qs(urlsplit(uri).query)=={k:[v] for k,v in query.items()}
    link='https://graph.microsoft.com/v1.0/me/messages?$skiptoken=opaque%2Babc%3D'
    assert graph_request(link)==link
    with pytest.raises(ValueError):graph_request(link,{'$top':'5'})


@pytest.mark.parametrize('path,query,pages',[
    ('https://attacker.invalid/v1.0/me',None,1),('https://graph.microsoft.com@attacker.invalid/v1.0/me',None,1),
    ('https://graph.microsoft.com:444/v1.0/me',None,1),('/me/messages#fragment',None,1),
    ('/me/messages',{'$filter':{'unexpected':'object'}},1),('/me/messages',None,0),
    ('/me/messages',None,True),('/me/messages',None,21),
])
def test_invalid_graph_requests_never_start_a_process(tmp_path,monkeypatch,path,query,pages):
    monkeypatch.setattr(GraphPowerShell,'run',lambda *a,**k:pytest.fail('Invalid request reached process'))
    with pytest.raises(ValueError):GraphPowerShell(tmp_path).request(path,query,pages)


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
print(json.dumps({'kind':'result','status':'connected','account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.Read']}),flush=True)
""")
    challenges=[]
    assert graph_process.run('connect',challenge=challenges.append)['status']=='connected'
    assert challenges[0]['code']=='OWNEDTEST'
    assert graph_process.account()=='fixture@example.invalid'


def test_connected_profile_saves_only_public_identity(tmp_path,monkeypatch):
    from bokkio import outlook_graph
    script=tmp_path/'bridge.py';script.write_text("import sys,json\njson.loads(sys.stdin.readline())\nprint(json.dumps({'kind':'result','status':'connected','account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.Read'],'access_token':'must-not-persist'}))")
    real=outlook_graph.subprocess.Popen
    monkeypatch.setattr(GraphPowerShell,'executable',lambda _:sys.executable)
    monkeypatch.setattr(outlook_graph.subprocess,'Popen',lambda argv,**kw:real([sys.executable,str(script)],**kw))
    graph=GraphPowerShell(tmp_path/'state');graph.run('connect')
    assert json.loads(graph.profile.read_text())=={'account':'fixture@example.invalid','tenant':'fixture','scopes':['Mail.Read']}


def test_unconnected_graph_does_not_start_authentication(tmp_path,monkeypatch):
    monkeypatch.setattr(GraphPowerShell,'run',lambda *a,**k:pytest.fail('Unexpected login'))
    with pytest.raises(GraphError,match='连接 Outlook'):
        GraphPowerShell(tmp_path).request('/me/messages')


def test_large_message_json_is_not_dropped_at_old_console_buffer_limit(graph_process):
    (graph_process.state.parent/'bridge.py').write_text("import sys,json\njson.loads(sys.stdin.readline())\nprint(json.dumps({'kind':'result','status':'completed','data':{'body':'x'*90000}}))")
    assert len(graph_process.run('request')['data']['body'])==90000


def test_graph_request_keeps_partial_result_and_error_codes(tmp_path,monkeypatch):
    graph=GraphPowerShell(tmp_path)
    monkeypatch.setattr(graph,'account',lambda:'fixture@example.invalid')
    monkeypatch.setattr(graph,'run',lambda *a,**k:{'status':'completed','data':{'value':[{'id':'1'}]},'complete':False,'next_link':'opaque'})
    assert graph.request('/me/messages')['complete'] is False
    monkeypatch.setattr(graph,'run',lambda *a,**k:{'status':'failed','error_code':'InefficientFilter','message':'Correct filter order'})
    with pytest.raises(GraphError) as error:graph.request('/me/messages')
    assert error.value.code=='InefficientFilter'


def test_old_business_tool_and_desktop_route_are_removed(tmp_path):
    from bokkio.runtime import TOOLS
    from bokkio.tool_schema import SCHEMAS
    from bokkio.desktop_service import DesktopStudio
    assert 'outlook.unread' not in TOOLS and 'outlook.unread' not in SCHEMAS
    studio=DesktopStudio(tmp_path)
    with pytest.raises(ValueError,match='Unknown Outlook route'):
        studio.route('POST','/api/outlook/unread',{})
    studio.close()
