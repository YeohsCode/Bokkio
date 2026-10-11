"""Thin client for generated Python code; grants come from the host, never the model."""
from __future__ import annotations

import os
import time

from .runtime import Runtime, load_policy


class Client:
    def __init__(self, runtime, session_id=None):
        self.runtime, self.session_id = runtime, session_id

    @classmethod
    def from_environment(cls):
        from .audit import AuditStore
        import json
        state, session = os.environ["BOKKIO_STATE_DIR"], os.environ["BOKKIO_SESSION_ID"]
        store = AuditStore(state)
        with store.connect() as db:
            row = db.execute("SELECT policy FROM sessions WHERE id=?", (session,)).fetchone()
        if row is None:
            raise ValueError("Delegated session is unavailable")
        return cls(Runtime(state, json.loads(row["policy"])), session)

    @classmethod
    def from_policy(cls, state_dir, policy_path):
        return cls(Runtime(state_dir, load_policy(policy_path)))

    def call(self, tool, arguments=None, operation_id=None):
        return self.runtime.call(tool, arguments, session_id=self.session_id, operation_id=operation_id)

    def open(self, **request):
        response = self.runtime.call("session.open", request)
        if response["status"] != "completed":
            raise RuntimeError(response)
        self.session_id = response["result"]["session_id"]
        return response

    def wait_job(self, job_id, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self.call("job.get", {"job_id": job_id})
            if response["status"] != "completed" or response["result"]["status"] not in {"queued", "running"}:
                return response
            time.sleep(.1)
        raise TimeoutError("Job is still running; inspect or cancel it")
