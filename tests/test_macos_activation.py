import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from bokkio import macos_activation as activation
from bokkio.model import BokkioError


def test_activation_refuses_wrong_pid_or_title_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    calls=[]
    def run(command,**kwargs):
        calls.append(command)
        if 'swiftc' in command:
            Path(command[-1]).write_bytes(b'fake helper');return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'status':'activated','pid':99,'title':'Owned','foreground_confirmed':True}).encode())
    monkeypatch.setattr(activation.subprocess,'run',run)
    with pytest.raises(BokkioError,match='activation failed'):activation.activate_window(10,'Owned')
    assert len(calls)==2


def test_activation_requires_window_confirmation_not_only_front_process(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    def run(command,**kwargs):
        if 'swiftc' in command:
            Path(command[-1]).write_bytes(b'fake helper');return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0,stdout=json.dumps({'status':'activated','pid':10,'title':'Owned','foreground_confirmed':True}).encode())
    monkeypatch.setattr(activation.subprocess,'run',run)
    with pytest.raises(BokkioError,match='activation failed'):activation.activate_window(10,'Owned')


def test_unconfirmed_front_window_is_zero_input_stale_not_a_retry_of_target_command(tmp_path,monkeypatch):
    from bokkio.model import BokkioStaleSnapshot
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    def run(command,**kwargs):
        if 'swiftc' in command:
            Path(command[-1]).write_bytes(b'fake helper');return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=1,stdout=json.dumps({'error':'front_window_unconfirmed'}).encode())
    monkeypatch.setattr(activation.subprocess,'run',run)
    with pytest.raises(BokkioStaleSnapshot,match='no target input'):activation.activate_window(10,'Owned')


@pytest.mark.parametrize('pid,title',[(True,'Owned'),(0,'Owned'),(10,''),(10,'a'*1025)])
def test_invalid_activation_scope_never_starts_helper(pid,title,monkeypatch):
    monkeypatch.setattr(activation.subprocess,'run',lambda *a,**k:pytest.fail('invalid scope must not dispatch'))
    with pytest.raises(BokkioError,match='exact PID'):activation.activate_window(pid,title)
