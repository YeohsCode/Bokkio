import json
import os
from pathlib import Path
import sys
import time

import pytest

from bokkio.audit import AuditStore
from bokkio.model import BokkioStaleSnapshot, tree_digest
from bokkio.runtime import Runtime
from bokkio.sdk import Client


class Desktop:
    def __init__(self):
        self.value = "initial"
        self.dispatches = 0

    def apps(self):
        return [{"pid": os.getpid(), "name": "Contract", "is_foreground": True}]

    def snapshot(self, app, window=None):
        return {"app": {"pid": os.getpid(), "name": "Contract"}, "windows": [
            {"ref": "field", "role": "text_field", "name": "Input", "value": self.value,
             "state": {"enabled": True}, "actions": ["set_value"], "parent": None, "children": []}]}

    def perform(self, app, action, **kwargs):
        if tree_digest(self.snapshot(app)["windows"]) != kwargs["expected_snapshot"]:
            raise BokkioStaleSnapshot("Changed before dispatch")
        self.dispatches += 1
        self.value = kwargs["value"]
        return {"verification": {"status": "confirmed"}, "after": {"value": self.value}}


@pytest.fixture
def setup(tmp_path):
    desktop = Desktop()
    policy = {"apps": ["Contract"], "paths": [str(tmp_path)], "write": True,
              "trusted_host": True, "require_approval": True}
    runtime = Runtime(tmp_path / "state", policy, desktop, lambda pid: "birth")
    client = Client(runtime)
    client.open()
    return client, desktop, policy, tmp_path


def action(client, value="secret-text"):
    observation = client.call("desktop.observe", {"app": "Contract"})
    assert observation["status"] == "completed", observation
    return {"app": "Contract", "ref": "field", "action": "set_value", "value": value,
            "observation_id": observation["result"]["observation_id"]}


def test_approval_exact_request_and_idempotence(setup):
    client, desktop, _, _ = setup
    arguments = action(client)
    pending = client.call("desktop.act", arguments, "operation")
    assert pending["status"] == "approval_required"
    assert desktop.dispatches == 0
    client.runtime.store.decide(pending["approval_id"], "approved", "owned test")
    result = client.call("desktop.act", arguments, "operation")
    assert result["status"] == "verified", result
    assert desktop.value == "secret-text"
    assert client.call("desktop.act", arguments, "operation") == result
    assert desktop.dispatches == 1
    assert client.call("desktop.act", {**arguments, "value": "different"}, "operation")["status"] == "denied"
    assert desktop.dispatches == 1
    events = client.runtime.store.query(operation_id="operation")
    assert {e["kind"] for e in events} >= {"request.received", "approval.requested", "approval.approved", "approval.consumed", "execution.intent", "execution.finished"}
    assert "secret-text" not in json.dumps(events)
    import platform
    filtered = client.call("audit.query", {"tool": "desktop.act", "status": "verified", "platform": platform.system()})
    assert any(e["operation_id"] == "operation" for e in filtered["result"])


@pytest.mark.parametrize("decision", ["denied", "revoked", "expired"])
def test_denied_revoked_expired_approval_never_dispatches(setup, decision):
    client, desktop, _, _ = setup
    arguments = action(client)
    pending = client.call("desktop.act", arguments, "operation")
    if decision == "expired":
        with client.runtime.store.connect() as db:
            db.execute("UPDATE approvals SET expires=0 WHERE id=?", (pending["approval_id"],))
    elif decision == "revoked":
        client.runtime.store.decide(pending["approval_id"], "approved", "test")
        client.runtime.store.decide(pending["approval_id"], "revoked", "test")
    else:
        client.runtime.store.decide(pending["approval_id"], decision, "test")
    assert client.call("desktop.act", arguments, "operation")["status"] == "denied"
    assert desktop.dispatches == 0


def test_scope_and_restarted_process(setup):
    client, desktop, _, _ = setup
    assert client.call("desktop.observe", {"app": "Other"})["status"] == "denied"
    assert client.runtime.call("session.open", {"apps": ["Other"]})["status"] == "denied"
    arguments = action(client)
    client.runtime.birth_probe = lambda pid: "different-birth"
    assert client.call("desktop.act", arguments)["status"] == "denied"
    assert desktop.dispatches == 0


def test_stale_snapshot_never_replayed(setup):
    client, desktop, _, _ = setup
    client.runtime.policy["require_approval"] = False
    arguments = action(client)
    desktop.value = "changed"
    response = client.call("desktop.act", arguments, "stale")
    assert response["status"] == "failed"
    assert desktop.dispatches == 0
    assert client.call("desktop.act", arguments, "stale") == response


def test_claimed_operation_never_redispatched(setup):
    client, desktop, _, _ = setup
    client.runtime.policy["require_approval"] = False
    arguments = action(client)
    result = client.call("desktop.act", arguments, "claimed")
    with client.runtime.store.connect() as db:
        db.execute("UPDATE operations SET status='running',result=NULL WHERE id='claimed'")
    assert client.call("desktop.act", arguments, "claimed")["status"] == "completion_unknown"
    assert desktop.dispatches == 1


def test_log_failure_prevents_dispatch(setup, monkeypatch):
    client, desktop, _, _ = setup
    client.runtime.policy["require_approval"] = False
    arguments = action(client)
    original = client.runtime.store.emit
    def emit(kind, **kwargs):
        if kind == "execution.intent":
            raise OSError("Storage full")
        return original(kind, **kwargs)
    monkeypatch.setattr(client.runtime.store, "emit", emit)
    assert client.call("desktop.act", arguments)["status"] == "denied"
    assert desktop.dispatches == 0


def test_event_cursor_export_and_metrics(setup):
    client, _, _, _ = setup
    client.call("desktop.observe", {"app": "Contract"})
    store = client.runtime.store
    page = store.query(session_id=client.session_id, limit=2)
    more = store.query(session_id=client.session_id, after=page[-1]["seq"])
    assert not set(e["seq"] for e in page) & set(e["seq"] for e in more)
    exported = [json.loads(line) for line in store.export(session_id=client.session_id).splitlines()]
    assert exported == store.query(session_id=client.session_id)
    assert store.export("csv", session_id=client.session_id).startswith("seq,event_id,")
    assert client.call("metrics.summary")["result"]["logical_operations"] >= 1


def test_artifact_scope_and_changed_bytes(setup):
    client, _, _, root = setup
    file = root / "data.csv"
    file.write_text("name,value\na,1\nb,2\n")
    result = client.call("evidence.check", {"path": str(file), "csv_rows": 2, "csv_columns": ["name", "value"]})
    assert result["result"]["passed"]
    artifact = result["result"]["artifact"]["artifact_id"]
    assert client.call("artifact.read", {"artifact_id": artifact})["status"] == "completed"
    another = Client(client.runtime)
    another.open()
    assert another.call("artifact.read", {"artifact_id": artifact})["status"] == "failed"
    file.write_text("changed")
    assert client.call("artifact.read", {"artifact_id": artifact})["status"] == "failed"


def job(client, root, code, **options):
    response = client.call("code.run", {"code": code, "cwd": str(root), **options})
    assert response["status"] == "queued", response
    return response["result"]["job_id"]


def test_real_job_output_truncation_and_evidence(setup):
    client, _, _, root = setup
    client.runtime.policy["require_approval"] = False
    code = "from pathlib import Path\nPath('made.csv').write_text('a,b\\n1,2\\n')\nprint('x'*10000)"
    result = client.wait_job(job(client, root, code, output_limit=100), timeout=15)
    assert result["result"]["status"] == "completed", result
    assert len(result["result"]["result"]["stdout"]) == 100
    assert result["result"]["result"]["truncated"]["stdout"]
    assert client.call("evidence.check", {"path": str(root / "made.csv"), "csv_rows": 1})["result"]["passed"]


def test_real_job_timeout_and_cancel(setup):
    client, _, _, root = setup
    client.runtime.policy["require_approval"] = False
    timeout_job = job(client, root, "import time; time.sleep(5)", timeout=.2)
    assert client.wait_job(timeout_job, timeout=15)["result"]["status"] == "timed_out"
    cancelled = job(client, root, "import time; time.sleep(10)")
    assert client.call("job.cancel", {"job_id": cancelled})["status"] == "completed"
    assert client.wait_job(cancelled, timeout=15)["result"]["status"] == "cancelled"


def test_revoked_grants_and_closed_session(setup):
    client, _, _, root = setup
    client.runtime.policy["apps"] = []
    assert client.call("desktop.observe", {"app": "Contract"})["status"] == "denied"
    client.runtime.policy["paths"] = []
    assert client.call("evidence.check", {"path": str(root / "x")})["status"] == "failed"
    client.call("session.close")
    assert client.call("metrics.summary")["status"] == "denied"


def test_agent_cannot_approve(setup):
    client, _, _, _ = setup
    assert client.call("approval.approve", {"decision": "approved"})["status"] == "denied"
    result = client.call("session.open", {"apps": ["Contract"], "trusted_host": False, "write": False})
    assert result["status"] == "denied"  # request fields never override host policy


def test_private_database_is_not_a_file_artifact(setup):
    client, _, _, _ = setup
    response = client.call("evidence.check", {"path": str(client.runtime.store.path)})
    assert response["status"] == "failed"
    assert "Private runtime state" in response["error"]


def test_malformed_host_policy_cannot_grant_writes(tmp_path):
    with pytest.raises(ValueError, match="boolean"):
        Runtime(tmp_path, {"write": "false"})


def test_pending_poll_does_not_destroy_later_approval(setup):
    client, desktop, _, _ = setup
    arguments = action(client)
    pending = client.call("desktop.act", arguments, "pending")
    again = client.call("desktop.act", arguments, "pending")
    assert again["status"] == "approval_required"
    assert again["approval_id"] == pending["approval_id"]
    client.runtime.store.decide(pending["approval_id"], "approved", "test")
    assert client.call("desktop.act", arguments, "pending")["status"] == "verified"
    assert desktop.dispatches == 1


def test_post_dispatch_log_failure_reports_unknown_without_repeat(setup, monkeypatch):
    client, desktop, _, _ = setup
    client.runtime.policy["require_approval"] = False
    arguments = action(client)
    original = client.runtime.store.emit
    def fail_result(kind, **kwargs):
        if kind == "execution.finished":
            raise OSError("Disk full after dispatch")
        return original(kind, **kwargs)
    monkeypatch.setattr(client.runtime.store, "emit", fail_result)
    response = client.call("desktop.act", arguments, "lost-result")
    assert response["status"] == "completion_unknown"
    assert response["operation_id"] == "lost-result"
    assert desktop.dispatches == 1
    assert client.call("desktop.act", arguments, "lost-result")["status"] == "completion_unknown"
    assert desktop.dispatches == 1
