"""Explicitly trusted-host jobs, with bounded output and process-tree cancellation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from .audit import AuditStore, canonical, identifier


def initialize(store):
    with store.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, session_id TEXT, operation_id TEXT, status TEXT,
            request TEXT, result TEXT, cancel INTEGER DEFAULT 0)""")


def launch(store, session_id, operation_id, request):
    initialize(store)
    job_id = identifier()
    with store.connect() as db:
        db.execute("INSERT INTO jobs(id,session_id,operation_id,status,request) VALUES(?,?,?,?,?)",
                   (job_id, session_id, operation_id, "queued", canonical(request)))
    try:
        subprocess.Popen([sys.executable, "-m", "bokkio.executor", str(store.root), job_id],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}))
    except Exception:
        with store.connect() as db:
            db.execute("UPDATE jobs SET status='failed',result=? WHERE id=?", (canonical({"error": "worker_start_failed"}), job_id))
        raise
    return {"job_id": job_id, "status": "queued", "execution_mode": "trusted-host"}


def get(store, job_id, session_id):
    initialize(store)
    with store.connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=? AND session_id=?", (job_id, session_id)).fetchone()
    if row is None:
        raise ValueError("Job is outside this session")
    return {"job_id": job_id, "status": row["status"], "result": json.loads(row["result"]) if row["result"] else None}


def cancel(store, job_id, session_id):
    get(store, job_id, session_id)
    with store.connect() as db:
        db.execute("UPDATE jobs SET cancel=1 WHERE id=? AND status IN ('queued','running')", (job_id,))
    store.emit("job.cancel_requested", session_id=session_id, data={"job_id": job_id})
    return get(store, job_id, session_id)


def _terminate(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def worker(root, job_id):
    store = AuditStore(root)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if job is None or job["status"] != "queued":
            return
        db.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
    request = json.loads(job["request"])
    session, operation = job["session_id"], job["operation_id"]
    start = time.monotonic()
    process = None
    result = {}
    status = "failed"
    try:
        with store.connect() as db:
            scope = db.execute("SELECT * FROM sessions WHERE id=?", (session,)).fetchone()
        if scope is None or scope["status"] != "open" or scope["expires"] <= time.time():
            raise ValueError("Session expired before worker start")
        if job["cancel"]:
            status = "cancelled"
            raise ValueError("Job cancelled before dispatch")
        folder = store.root / "jobs" / job_id
        folder.mkdir(parents=True, mode=0o700)
        language = request.get("language", "python")
        command = request.get("argv")
        if command is None:
            suffix, interpreter = {"python": (".py", [sys.executable]), "shell": (".sh", ["/bin/sh"]),
                                   "powershell": (".ps1", ["powershell.exe", "-NoProfile", "-File"])}[language]
            script = folder / ("script" + suffix)
            prefix = "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding\n$OutputEncoding = [Console]::OutputEncoding\n" if language == "powershell" else ""
            script.write_text(prefix + request["code"], encoding="utf-8-sig" if language == "powershell" else "utf-8")
            command = interpreter + [str(script)]
        # Do not inherit provider credentials. This is environment hygiene, not a sandbox.
        inherited = {k: v for k, v in os.environ.items() if k.upper() in {
            "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
            "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL", "PYTHONPATH"}}
        inherited.update(BOKKIO_STATE_DIR=str(store.root), BOKKIO_SESSION_ID=session, BOKKIO_PARENT_OPERATION=operation)
        store.emit("job.started", session_id=session, operation_id=operation,
                   data={"job_id": job_id, "channel": "process" if request.get("argv") else "code", "execution_mode": "trusted-host"})
        process = subprocess.Popen(command, cwd=request["cwd"], env=inherited, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}))
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        counts = {"stdout": 0, "stderr": 0}
        def consume(name, stream):
            while True:
                block = stream.read(4096)
                if not block:
                    break
                counts[name] += len(block)
                available = max(0, request.get("output_limit", 65536) - len(buffers[name]))
                buffers[name].extend(block[:available])
            stream.close()
        threads = [threading.Thread(target=consume, args=(name, stream), daemon=True)
                   for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
        for thread in threads:
            thread.start()
        status = "completed"
        while process.poll() is None:
            with store.connect() as db:
                current = db.execute("SELECT cancel FROM jobs WHERE id=?", (job_id,)).fetchone()
                scope = db.execute("SELECT status,expires FROM sessions WHERE id=?", (session,)).fetchone()
            if current["cancel"] or scope["status"] != "open" or scope["expires"] <= time.time():
                status = "cancelled"
                _terminate(process)
                break
            if time.monotonic() - start > request.get("timeout", 30):
                status = "timed_out"
                _terminate(process)
                break
            time.sleep(.05)
        process.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=1)
        if any(thread.is_alive() for thread in threads):
            _terminate(process)
            for thread in threads:
                thread.join(timeout=1)
        if status == "completed" and process.returncode != 0:
            status = "failed"
        result = {"exit_code": process.returncode, "stdout": buffers["stdout"].decode("utf-8", "replace"),
                  "stderr": buffers["stderr"].decode("utf-8", "replace"), "output_bytes": counts,
                  "truncated": {k: counts[k] > len(buffers[k]) for k in counts},
                  "duration_ms": round((time.monotonic() - start) * 1000, 3),
                  "execution_mode": "trusted-host", "dispatched": True}
    except Exception as error:
        result = {"error": type(error).__name__, "message": str(error), "dispatched": process is not None}
        if process is not None and process.poll() is None:
            _terminate(process)
    with store.connect() as db:
        db.execute("UPDATE jobs SET status=?,result=? WHERE id=?", (status, canonical(result), job_id))
        receipt = {"status": "executed" if status == "completed" else status, "session_id": session,
                   "operation_id": operation, "dispatched": result.get("dispatched", "unknown"),
                   "result": {"job_id": job_id, "status": status, "execution_mode": "trusted-host"}}
        db.execute("UPDATE operations SET status=?,result=? WHERE id=?", (receipt["status"], canonical(receipt), operation))
        store.emit("job.finished", session_id=session, operation_id=operation,
                   data={"job_id": job_id, "status": status, "duration_ms": result.get("duration_ms"),
                         "exit_code": result.get("exit_code"), "output_bytes": result.get("output_bytes"),
                         "dispatched": result.get("dispatched", "unknown")}, db=db)


if __name__ == "__main__":
    worker(sys.argv[1], sys.argv[2])
