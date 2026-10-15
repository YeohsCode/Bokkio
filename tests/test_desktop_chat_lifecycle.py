"""A terminal SDK result must unblock the next task despite inherited pipe handles."""
import json,os,signal,subprocess,sys,time
import pytest
from bokkio.desktop_service import DesktopStudio


def test_terminal_result_does_not_wait_for_descendant_pipe_eof(tmp_path,monkeypatch):
    studio=DesktopStudio(tmp_path/'state');studio.api_key='test-only';studio.settings['workspace']=str(tmp_path/'workspace');child_file=tmp_path/'child.pid';real_popen=subprocess.Popen
    program="""import json,subprocess,sys,pathlib
json.load(sys.stdin)
p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
pathlib.Path(sys.argv[1]).write_text(str(p.pid))
print(json.dumps({'kind':'result','status':'completed','response':'checked'}),flush=True)
"""
    def start(*args,**kwargs):return real_popen([sys.executable,'-c',program,str(child_file)],**kwargs)
    monkeypatch.setattr('bokkio.desktop_service.subprocess.Popen',start)
    try:
        job=studio.route('POST','/api/chat/start',{'prompt':'owned fixture'})
        deadline=time.monotonic()+3
        while job['status']=='running' and time.monotonic()<deadline:time.sleep(.02)
        assert job['status']=='completed' and job['response']=='checked'
        assert studio.chat_processes[job['id']].poll() is not None
    finally:
        if child_file.exists():os.kill(int(child_file.read_text()),signal.SIGTERM)
        for process in studio.chat_processes.values():
            if process.poll() is None:process.kill();process.wait()


def test_emergency_finalizes_dispatched_job_before_sdk_tree_kill(tmp_path,monkeypatch):
    from test_runtime_workflow import Desktop
    from bokkio.local_runtime import LocalRuntime
    from bokkio.sdk import Client
    from bokkio.executor import get
    cid='a'*32;studio=DesktopStudio(tmp_path/'runtime');runtime=LocalRuntime(studio.state,Desktop(),lambda _: 'birth');client=Client(runtime);client.open(task_id=cid)
    target=tmp_path/'must-not-exist.txt'
    queued=client.call('code.run',{'language':'python','code':f'import time;from pathlib import Path;time.sleep(12);Path({str(target)!r}).write_text("late write")','timeout':30})
    jid=queued['result']['job_id'];deadline=time.monotonic()+5
    while get(runtime.store,jid,client.session_id)['status']=='queued' and time.monotonic()<deadline:time.sleep(.02)
    assert get(runtime.store,jid,client.session_id)['status']=='running'
    while time.monotonic()<deadline:
        with runtime.store.connect() as db:pid=db.execute('SELECT process_pid FROM jobs WHERE id=?',(jid,)).fetchone()[0]
        if pid:break
        time.sleep(.02)
    assert pid, 'the code child must actually start before cancellation'
    class SDK:
        pid=123456
        def poll(self):return None
    studio.chat_processes[cid]=SDK();studio.chats[cid]={'id':cid,'status':'running'}
    def kill_sdk(_):assert get(runtime.store,jid,client.session_id)['status']=='cancelled'
    monkeypatch.setattr('bokkio.executor._terminate_pid',kill_sdk)
    assert studio.route('POST','/api/emergency-stop',{})['status']=='stopped'
    assert get(runtime.store,jid,client.session_id)['status']=='cancelled' and not target.exists()
    assert (studio.state/'task-cancellations'/cid).exists()
    monkeypatch.setenv('BOKKIO_DESKTOP_TASK_ID',cid)
    with pytest.raises(RuntimeError,match='stopped'):client.open()
