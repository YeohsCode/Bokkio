"""Real process regressions for cancellation and crash receipts."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from bokkio.runtime import Runtime
from bokkio.sdk import Client


def wait_for(probe):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            value = probe()
            if value:
                return value
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(.05)
    raise TimeoutError("Test process did not become ready")


def running(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True)
    return bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


@pytest.fixture
def client(tmp_path):
    client = Client(Runtime(tmp_path / "state", {"paths": [str(tmp_path)], "write": True,
                                               "trusted_host": True, "require_approval": False}))
    client.open()
    yield client
    client.call("session.close")


def start_tree(client, tmp_path, operation):
    child = "import signal,time,os;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path('child.pid').write_text(str(os.getpid()));time.sleep(60)"
    code = "import subprocess,sys,time\nsubprocess.Popen([sys.executable,'-c'," + repr(child) + "],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\ntime.sleep(60)"
    args = {"code": code, "cwd": str(tmp_path)}
    queued = client.call("code.run", args, operation)
    assert queued["status"] == "queued", queued
    pid = wait_for(lambda: int((tmp_path / "child.pid").read_text()))
    return args, queued["result"]["job_id"], pid


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal/ps process-tree regression; Windows needs live taskkill verification")
def test_cancel_kills_descendant_even_when_parent_exits(client, tmp_path):
    args, job, pid = start_tree(client, tmp_path, "cancel-tree")
    try:
        client.call("job.cancel", {"job_id": job})
        result = client.wait_job(job, timeout=10)
        assert result["result"]["status"] == "cancelled", result
        assert not running(pid)
    finally:
        if running(pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.skipif(os.name == "nt", reason="POSIX worker SIGKILL regression; Windows needs live process verification")
def test_worker_crash_becomes_unknown_and_never_replays(client, tmp_path):
    args, job, pid = start_tree(client, tmp_path, "lost-worker")
    with client.runtime.store.connect() as db:
        worker = db.execute("SELECT worker_pid FROM jobs WHERE id=?", (job,)).fetchone()[0]
    try:
        os.kill(worker, signal.SIGKILL)
        wait_for(lambda: not running(worker))
        result = client.wait_job(job, timeout=10)
        assert result["result"]["status"] == "completion_unknown", result
        assert result["result"]["result"]["dispatched"] == "unknown"
        duplicate = client.call("code.run", args, "lost-worker")
        assert duplicate["status"] == "completion_unknown"
        assert duplicate["dispatched"] == "unknown"
        assert not running(pid)
        events = client.runtime.store.query(operation_id="lost-worker")
        assert len([e for e in events if e["kind"] == "job.started"]) == 1
        assert len([e for e in events if e["kind"] == "job.worker_lost"]) == 1
    finally:
        if running(pid):
            os.kill(pid, signal.SIGKILL)


def test_short_lived_job_receipt_survives_process_registration(client, tmp_path):
    queued = client.call("code.run", {"code": "print('fast')", "cwd": str(tmp_path)})
    result = client.wait_job(queued["result"]["job_id"], timeout=10)
    assert result["result"]["status"] == "completed", result
    assert result["result"]["result"]["stdout"].strip() == "fast"


def test_code_worker_does_not_write_bytecode_into_imported_packages(client,tmp_path):
    module=tmp_path/'bundled_module.py';module.write_text('value=42\n')
    code=f'import sys;sys.path.insert(0,{str(tmp_path)!r});import bundled_module;print(sys.dont_write_bytecode,bundled_module.value)'
    queued=client.call('code.run',{'code':code,'cwd':str(tmp_path)})
    result=client.wait_job(queued['result']['job_id'],timeout=10)
    assert result['result']['status']=='completed',result
    assert result['result']['result']['stdout'].strip()=='True 42'
    assert not (tmp_path/'__pycache__').exists()
