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
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, session_id TEXT, operation_id TEXT, status TEXT,
            request TEXT, result TEXT, cancel INTEGER DEFAULT 0)""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
        for name, kind in (("worker_pid", "INTEGER"), ("worker_birth", "TEXT"),
                           ("process_pid", "INTEGER"), ("process_birth", "TEXT")):
            if name not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN " + name + " " + kind)


def _birth(pid):
    from .runtime import process_birth
    if os.name == "nt":
        import ctypes as c
        from ctypes import wintypes as w
        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
        kernel.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            raise ValueError("Worker is unavailable")
        try:
            code = w.DWORD()
            if not kernel.GetExitCodeProcess(handle, c.byref(code)) or code.value != 259:
                raise ValueError("Worker has exited")
        finally:
            kernel.CloseHandle(handle)
    else:
        state = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=3)
        if not state.stdout.strip() or state.stdout.strip().startswith("Z"):
            raise ValueError("Process is no longer running")
    return process_birth(pid)


def _identity(pid):
    from .runtime import process_birth
    return process_birth(pid)


def launch(store, session_id, operation_id, request):
    initialize(store)
    job_id = identifier()
    with store.connect() as db:
        db.execute("INSERT INTO jobs(id,session_id,operation_id,status,request) VALUES(?,?,?,?,?)",
                   (job_id, session_id, operation_id, "queued", canonical(request)))
    try:
        process = subprocess.Popen([sys.executable, "-m", "bokkio.executor", str(store.root), job_id],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}))
        born = _identity(process.pid)
        with store.connect() as db:
            db.execute("UPDATE jobs SET worker_pid=?,worker_birth=? WHERE id=?", (process.pid, born, job_id))
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
    if row["status"] in {"queued", "running"} and row["worker_pid"]:
        try:
            alive = _birth(row["worker_pid"]) == row["worker_birth"]
        except (ValueError, OSError, subprocess.TimeoutExpired):
            alive = False
        if not alive:
            # A lost worker cannot prove whether its child produced side effects.
            # Stop a still-identical tracked child, record unknown, never replay.
            cleanup = "no_tracked_live_child"
            if row["process_pid"]:
                try:
                    if _birth(row["process_pid"]) == row["process_birth"]:
                        _terminate_pid(row["process_pid"])
                        cleanup = "tracked_process_tree_terminated"
                except (ValueError, OSError, subprocess.TimeoutExpired):
                    cleanup = "tracked_child_unavailable"
            result = {"error": "worker_lost", "dispatched": "unknown", "cleanup": cleanup,
                      "message": "Worker exited without a durable result; inspect evidence before any new request"}
            with store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                changed = db.execute("UPDATE jobs SET status='completion_unknown',result=? WHERE id=? AND status IN ('queued','running')",
                                     (canonical(result), job_id)).rowcount
                if changed:
                    receipt = {"status": "completion_unknown", "session_id": session_id,
                               "operation_id": row["operation_id"], "dispatched": "unknown",
                               "result": {"job_id": job_id, "status": "completion_unknown"}, "error_code": "worker_lost"}
                    db.execute("UPDATE operations SET status=?,result=? WHERE id=?",
                               ("completion_unknown", canonical(receipt), row["operation_id"]))
                    store.emit("job.worker_lost", session_id=session_id, operation_id=row["operation_id"],
                               data={"job_id": job_id, "status": "completion_unknown", "dispatched": "unknown", "cleanup": cleanup}, db=db)
                row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return {"job_id": job_id, "status": row["status"], "result": json.loads(row["result"]) if row["result"] else None}


def cancel(store, job_id, session_id):
    get(store, job_id, session_id)
    with store.connect() as db:
        db.execute("UPDATE jobs SET cancel=1 WHERE id=? AND status IN ('queued','running')", (job_id,))
    store.emit("job.cancel_requested", session_id=session_id, data={"job_id": job_id})
    return get(store, job_id, session_id)


def _terminate_pid(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
            deadline = time.monotonic() + 1
            # The group leader may exit while a descendant ignores SIGTERM.
            while time.monotonic() < deadline:
                os.killpg(pid, 0)
                time.sleep(.05)
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Some Mac hosts reject a signal to a process group even when its
            # children belong to this user. Enumerate that exact group and signal
            # its live members by PID, preserving each birth identity.
            def members():
                output=subprocess.run(['ps','-axo','pid=,pgid=,uid=,stat='],capture_output=True,text=True,timeout=3)
                if output.returncode:raise PermissionError('Cannot inspect job process group')
                rows=[]
                for line in output.stdout.splitlines():
                    fields=line.split()
                    if len(fields)==4 and fields[1]==str(pid) and fields[2]==str(os.getuid()) and not fields[3].startswith('Z'):rows.append(int(fields[0]))
                return rows
            tracked={p:_birth(p) for p in members()}
            for p,born in tracked.items():
                try:
                    if _birth(p)==born:os.kill(p,signal.SIGTERM)
                except (ProcessLookupError,ValueError):pass
            deadline=time.monotonic()+1
            while time.monotonic()<deadline and members():time.sleep(.05)
            for p in members():
                if p not in tracked:tracked[p]=_birth(p)
                try:
                    if _birth(p)==tracked[p]:os.kill(p,signal.SIGKILL)
                except (ProcessLookupError,ValueError):pass


def _terminate(process):
    _terminate_pid(process.pid)
    process.wait(timeout=10)


def worker(root, job_id):
    store = AuditStore(root)
    initialize(store)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if job is None or job["status"] != "queued":
            return
        db.execute("UPDATE jobs SET status='running',worker_pid=?,worker_birth=? WHERE id=?",
                   (os.getpid(), _birth(os.getpid()), job_id))
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
            "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL", "PYTHONPATH", "PYTHONUTF8", "PYTHONIOENCODING"}}
        inherited.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        inherited.update(BOKKIO_STATE_DIR=str(store.root), BOKKIO_SESSION_ID=session, BOKKIO_PARENT_OPERATION=operation)
        store.emit("job.started", session_id=session, operation_id=operation,
                   data={"job_id": job_id, "channel": "process" if request.get("argv") else "code", "execution_mode": "trusted-host"})
        process = subprocess.Popen(command, cwd=request["cwd"], env=inherited, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}))
        with store.connect() as db:
            db.execute("UPDATE jobs SET process_pid=?,process_birth=? WHERE id=?", (process.pid, _identity(process.pid), job_id))
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
        if request.get("structured_output") and status == "completed":
            try:
                if result["truncated"]["stdout"]:
                    raise ValueError("Structured job output was truncated")
                output = json.loads(result["stdout"])
                if not isinstance(output, dict):
                    raise ValueError("Structured job output must be an object")
                result["output"] = output
                if output.get("status") == "completion_unknown":
                    status = "completion_unknown"
                else:
                    contract = request.get("output_schema", {})
                    if set(contract.get("required", [])) - set(output):
                        raise ValueError("Structured job output omitted required evidence")
                    for key, definition in contract.get("properties", {}).items():
                        if key not in output:continue
                        if definition.get("type") == "object" and not isinstance(output[key], dict):
                            raise ValueError("Invalid structured output field")
                        if "enum" in definition and output[key] not in definition["enum"]:
                            raise ValueError("Invalid structured output status")
                    if any(output.get(k) != v for k, v in request.get("output_bindings", {}).items()):
                        raise ValueError("Structured output binding differs from its request")
            except (ValueError, TypeError):
                # A process ran but no durable module result survived: do not replay.
                status = "completion_unknown"
                result["output_error"] = "Structured job result unavailable; inspect evidence"
    except Exception as error:
        result = {"error": type(error).__name__, "message": str(error), "dispatched": process is not None}
        if process is not None and process.poll() is None:
            try:_terminate(process)
            except Exception as cleanup:
                status='completion_unknown';result['cleanup_error']=type(cleanup).__name__
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
