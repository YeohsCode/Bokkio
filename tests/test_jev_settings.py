import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from bokkio.desktop_chat import instructions_for, mcp_arguments
from bokkio.desktop_decision import provider_from_environment
from bokkio.desktop_service import DesktopStudio
from bokkio.execution_log import architecture, chat_trace
from bokkio.jev import JevProvider
from bokkio.model import BokkioError


def test_custom_endpoint_key_and_model_sent_over_real_http():
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append((self.path,self.headers.get('Authorization'),body))
            self.send_response(200);self.end_headers();self.wfile.write(b'{"answers": {"ready": {"type":"noul", "noul":1}}}')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        endpoint=f'http://127.0.0.1:{server.server_port}/custom/v2/decide'
        client=JevProvider(api_key='custom-secret',model='my/jev-alias',source='custom',api_url=endpoint)
        result=client.ask({'goal':'test'},{'ready':{'type':'noul'}})
        path,auth,body=received[0]
        assert path=='/custom/v2/decide' and auth=='Bearer custom-secret'
        assert body=={'model':'my/jev-alias','state':{'goal':'test'},'questions':{'ready':{'type':'noul'}}}
        assert result['answers']['ready']['noul']==1 and result['source']=='custom'
    finally:server.shutdown();server.server_close();thread.join(2)


def test_settings_persist_mode_url_and_model_but_no_key(tmp_path):
    studio=DesktopStudio(tmp_path/'state')
    value=studio.route('POST','/api/settings',{'jev_enabled':False,'jev_source':'custom','jev_api_url':'http://localhost:8123/decide','jev_model':'local/alias','jev_api_key':'private-key'})
    loaded=DesktopStudio(studio.state)
    saved=loaded.route('GET','/api/settings',{})
    assert saved['jev_enabled'] is False and saved['jev_api_url']=='http://localhost:8123/decide' and saved['jev_model']=='local/alias'
    assert value['has_jev_api_key'] and not saved['has_jev_api_key']
    assert 'private-key' not in studio.config_path.read_text()
    assert studio.route('GET','/api/architecture',{})['selection']=='Harness SDK'


@pytest.mark.parametrize('enabled',['false',0,None])
def test_mode_requires_actual_boolean_without_mutating_settings(tmp_path,enabled):
    studio=DesktopStudio(tmp_path/'state')
    with pytest.raises(ValueError,match='boolean'):studio.route('POST','/api/settings',{'jev_enabled':enabled})
    assert studio.settings['jev_enabled'] is True


def test_can_disable_jev_without_filling_jev_configuration(tmp_path):
    studio=DesktopStudio(tmp_path/'state')
    saved=studio.route('POST','/api/settings',{'jev_enabled':False,'jev_source':'custom','jev_api_url':'','jev_model':''})
    assert saved['jev_enabled'] is False
    with pytest.raises(BokkioError):studio.route('POST','/api/settings',{'jev_enabled':True})
    assert studio.settings['jev_enabled'] is False


def test_custom_url_never_reuses_unrelated_private_or_planner_key(tmp_path,monkeypatch):
    private=tmp_path/'jev.json';private.write_text(json.dumps({'source':'openrouter','api_key':'private-upstream-key'}))
    monkeypatch.setenv('BOKKIO_JEV_CONFIG',str(private));monkeypatch.setenv('BOKKIO_JEV_API_URL','https://custom.example/decide');monkeypatch.setenv('BOKKIO_JEV_SOURCE','custom')
    monkeypatch.delenv('BOKKIO_JEV_API_KEY',raising=False);monkeypatch.setenv('OPENROUTER_API_KEY','environment-upstream-key')
    monkeypatch.setenv('BOKKIO_PROVIDER_KEY','planner-key');monkeypatch.setenv('BOKKIO_PROVIDER_BASE_URL','https://openrouter.ai/api/v1')
    with pytest.raises(BokkioError,match='Configure a Jev key'):provider_from_environment()
    monkeypatch.setenv('BOKKIO_JEV_API_KEY','custom-key');monkeypatch.setenv('BOKKIO_JEV_MODEL','my/custom')
    provider=provider_from_environment();assert provider.endpoint=='https://custom.example/decide' and provider.model=='my/custom' and provider._key=='custom-key'


def test_matching_custom_private_config_can_supply_key(tmp_path,monkeypatch):
    endpoint='http://localhost:8124/decision';private=tmp_path/'jev.json'
    private.write_text(json.dumps({'source':'custom','api_url':endpoint,'api_key':'matching-key'}))
    monkeypatch.setenv('BOKKIO_JEV_CONFIG',str(private));monkeypatch.setenv('BOKKIO_JEV_API_URL',endpoint);monkeypatch.setenv('BOKKIO_JEV_SOURCE','custom');monkeypatch.delenv('BOKKIO_JEV_API_KEY',raising=False)
    assert provider_from_environment()._key=='matching-key'


def test_off_mode_uses_existing_model_free_mcp_entry_and_direct_instructions(tmp_path):
    config={'state':str(tmp_path),'jev_enabled':False}
    args=mcp_arguments(config)
    assert args==['-m','bokkio.runtime_cli','--state',str(tmp_path),'--local','serve']
    text=instructions_for('write editor',False)
    assert 'Jev is disabled' in text and 'Use desktop.observe' in text and 'For every new native UI interaction' not in text
    assert mcp_arguments({**config,'jev_enabled':True})[1]=='bokkio.desktop_decision'


def test_disabled_chat_log_does_not_claim_jev_selection(tmp_path):
    job={'id':'test','prompt':'write editor','status':'running','architecture':architecture(False),'choices':{}}
    tree=chat_trace(job,tmp_path)
    assert tree['architecture']['jev_enabled'] is False and tree['architecture']['jev_active'] is False
    assert '已关闭 Jev' in tree['detail'] and tree['counts']['jev_calls']==0


def test_task_uses_start_snapshot_when_settings_change(tmp_path,monkeypatch):
    studio=DesktopStudio(tmp_path/'state');studio.api_key='planner-test';studio.jev_api_key='jev-test';studio.settings['workspace']=str(tmp_path/'workspace')
    studio.route('POST','/api/settings',{'jev_enabled':False,'jev_source':'custom','jev_api_url':'','jev_model':''})
    captured={};real_popen=subprocess.Popen
    program='import json,sys,time;json.load(sys.stdin);time.sleep(.1);print(json.dumps({"kind":"result","status":"completed","response":"ok"}),flush=True)'
    def start(*args,**kwargs):
        captured['env']=kwargs['env'];return real_popen([sys.executable,'-c',program],**kwargs)
    monkeypatch.setattr('bokkio.desktop_service.subprocess.Popen',start)
    job=studio.route('POST','/api/chat/start',{'prompt':'owned task'})
    studio.route('POST','/api/settings',{'jev_enabled':True,'jev_api_url':'https://custom.example/decision','jev_model':'new/model'})
    assert job['architecture']['jev_enabled'] is False
    assert not any(k.startswith('BOKKIO_JEV_') for k in captured['env'])
    assert chat_trace({**job,'choices':{}},studio.state)['architecture']['jev_enabled'] is False
    studio.chat_processes[job['id']].wait(3)


@pytest.mark.parametrize('url',['ftp://example/decision','not a URL','https://user:secret@example/decision','https://example:invalid/decision'])
def test_invalid_custom_endpoint_fails_before_request(url):
    with pytest.raises(BokkioError):JevProvider(api_key='test-key',source='custom',api_url=url)


def test_mcp_credentials_are_explicit_env_references_never_patch_literals(monkeypatch):
    from bokkio.desktop_chat import mcp_environment_keys,patch_yaml
    monkeypatch.setenv('BOKKIO_JEV_API_KEY','must-never-be-persisted')
    text=patch_yaml([{'env':'__BOKKIO_MCP_ENV__'}],True)
    assert '!!js' in text and 'BOKKIO_JEV_API_KEY' in text and 'must-never-be-persisted' not in text
    assert mcp_environment_keys(False)==['BOKKIO_DESKTOP_TASK_ID','BOKKIO_DESKTOP_APP_PATH','PYTHONDONTWRITEBYTECODE']
    assert 'BOKKIO_JEV_API_KEY' not in patch_yaml([{'env':'__BOKKIO_MCP_ENV__'}],False)


def test_sdk_empty_answer_does_not_claim_task_completed():
    from types import SimpleNamespace
    from bokkio.desktop_chat import harness_result
    result=harness_result(SimpleNamespace(finish_reason='completed',final_response=''))
    assert result['status']=='failed' and 'without a visible final answer' in result['error']
    assert harness_result(SimpleNamespace(finish_reason='completed',final_response='Verified result'))['status']=='completed'


def test_desktop_model_failure_reports_actionable_status_without_upstream_secrets():
    from types import SimpleNamespace
    from bokkio.desktop_chat import harness_result
    result=harness_result(SimpleNamespace(finish_reason='error',final_response=''),'402: insufficient credits; private-url-and-account-id')
    assert result['status']=='failed' and '402' in result['error'] and '额度' in result['error']
    assert 'private-url' not in result['error']
