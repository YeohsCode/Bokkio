"""Model-free Computer Use boundary shared by MCP, CLI and generated code."""
from __future__ import annotations
from .execution_context import parent_operation, workflow_step

from concurrent.futures import ThreadPoolExecutor
import getpass
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys
import time

from .audit import AuditStore, canonical, digest, identifier, summarize, identity
from .model import BokkioCompletionUnknown, BokkioStaleSnapshot, tree_digest


READ_TOOLS = {"capabilities", "desktop.list", "desktop.windows", "desktop.observe", "desktop.capture", "job.get", "artifact.read",
              "evidence.check", "audit.query", "audit.export", "events.follow", "metrics.summary", "approval.status", "browser.observe"}
WRITE_TOOLS = {"desktop.act", "desktop.input", "desktop.activate", "desktop.launch", "desktop.pixel", "code.run", "process.run", "browser.open", "browser.act"}
READ_TOOLS |= {"workflow.list", "workflow.get", "workflow.status"}
READ_TOOLS |= {"module.list", "capability.list", "capability.get"}
WRITE_TOOLS |= {"capability.invoke"}
TOOLS = READ_TOOLS | WRITE_TOOLS | {"session.open", "session.close", "job.cancel", "workflow.run", "workflow.resume", "workflow.cancel"}


def close_session(store,session_id):
    """Close a validated session without consulting the desktop or OS grants."""
    marker=store.root/'session-cancellations'/session_id;marker.parent.mkdir(exist_ok=True);marker.touch()
    with store.connect() as db:
        db.execute("UPDATE sessions SET status='closed' WHERE id=?",(session_id,))
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone():
            db.execute("UPDATE jobs SET cancel=1 WHERE session_id=? AND status IN ('queued','running')",(session_id,))


def load_policy(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Policy must be an object")
    return value


def process_birth(pid):
    if sys.platform == "win32":
        import ctypes as c
        from ctypes import wintypes as w
        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
        kernel.GetProcessTimes.argtypes, kernel.GetProcessTimes.restype = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4, w.BOOL
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            raise ValueError("Authorized process is unavailable")
        try:
            created, exited, system, elapsed = (w.FILETIME() for _ in range(4))
            if not kernel.GetProcessTimes(handle, c.byref(created), c.byref(exited), c.byref(system), c.byref(elapsed)):
                raise ValueError("Could not bind process identity")
            return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    output = subprocess.run(["ps", "-p", str(int(pid)), "-o", "lstart="], capture_output=True, text=True, timeout=3)
    if not output.stdout.strip():
        raise ValueError("Authorized process is unavailable")
    return output.stdout.strip()


class Runtime:
    def __init__(self, state_dir, policy=None, backend=None, birth_probe=None):
        self.store = AuditStore(state_dir)
        self.policy = {"apps": [], "paths": [], "origins": [], "write": False, "trusted_host": False,
                       "require_approval": True, "ttl": 3600, **(policy or {})}
        for key in ("write", "trusted_host", "require_approval"):
            if type(self.policy[key]) is not bool:
                raise ValueError("Policy " + key + " must be a boolean")
        for key in ("apps", "paths", "origins"):
            if not isinstance(self.policy[key], list) or any(not isinstance(v, (str, int)) for v in self.policy[key]):
                raise ValueError("Policy " + key + " must be a list of resource identifiers")
        if not isinstance(self.policy.get("modules", []), list) or any(not isinstance(v, str) for v in self.policy.get("modules", [])):
            raise ValueError("Policy modules must be a list of module identifiers")
        if type(self.policy["ttl"]) is not int or not 1 <= self.policy["ttl"] <= 86400:
            raise ValueError("Policy ttl must be 1..86400 seconds")
        self._backend = backend
        # AX handle tables are mutable; Windows COM objects are apartment-bound.
        # Keep all native access on one dedicated thread even for concurrent MCP calls.
        self._native_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bokkio-native")
        self.birth_probe = birth_probe or process_birth
        with self.store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,session_id TEXT,payload TEXT)")

    @property
    def backend(self):
        if self._backend is None:
            if sys.platform == "win32":
                import comtypes
                comtypes.CoInitialize()
            from .xa11y_backend import Xa11yBackend
            self._backend = Xa11yBackend()
        return self._backend

    def _native_call(self, method, *args, _session_guard=None, _dispatch_request=None, **kwargs):
        def invoke():
            if _session_guard is not None:
                if _dispatch_request is not None:
                    self._dispatch_scope(*_dispatch_request, _session_guard)
                else:
                    self._session(_session_guard)
            if method == "perform":
                from .xa11y_backend import Xa11yBackend
                if isinstance(self.backend, Xa11yBackend):
                    from .desktop_input import require_input_session
                    require_input_session()
            return getattr(self.backend, method)(*args, **kwargs)
        return self._native_executor.submit(invoke).result()

    def _session(self, session_id):
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None or row["status"] != "open" or row["expires"] <= time.time() or row["owner"] != identity():
            raise ValueError("Session unavailable, expired or owned by another OS user")
        return json.loads(row["policy"])

    def _app(self, scope, app, window=None):
        bindings = scope["bindings"]
        matches = [(pid, info) for pid, info in bindings.items() if str(app) in {pid, info["name"]}]
        if len(matches) != 1:
            raise ValueError("Application is outside this session or ambiguous")
        pid, info = matches[0]
        if not any(str(v) in {pid, info["name"]} for v in self.policy["apps"]):
            raise ValueError("Application grant was revoked")
        if self.birth_probe(int(pid)) != info["birth"]:
            raise ValueError("Authorized process has restarted; open a new session")
        if info["windows"] and window not in info["windows"]:
            raise ValueError("An exact authorized window is required")
        current_windows = self.policy.get("windows", {}).get(info["name"], [])
        if current_windows and window not in current_windows:
            raise ValueError("Window grant was revoked")
        return pid

    def _path(self, scope, value):
        path = Path(value).expanduser().resolve()
        if path == self.store.root or self.store.root in path.parents:
            raise ValueError("Private runtime state is not available through file tools")
        roots = [Path(p).resolve() for p in scope["paths"]]
        if not any(path == root or root in path.parents for root in roots):
            raise ValueError("Path is outside session grants")
        current = [Path(p).expanduser().resolve() for p in self.policy["paths"]]
        if not any(path == root or root in path.parents for root in current):
            raise ValueError("Path grant was revoked")
        return path

    def _artifact(self, session_id, operation_id, path, mime="application/octet-stream"):
        path = Path(path).resolve()
        record = {"artifact_id": identifier(), "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                  "mime": mime, "bytes": path.stat().st_size}
        with self.store.connect() as db:
            db.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)", (record["artifact_id"], session_id, operation_id, str(path),
                                                                      record["sha256"], mime, record["bytes"]))
        return record

    def _observation(self, session_id, payload):
        observation_id = identifier()
        with self.store.connect() as db:
            db.execute("INSERT INTO observations VALUES(?,?,?)", (observation_id, session_id, canonical(payload)))
        return observation_id

    def _get_observation(self, session_id, observation_id):
        with self.store.connect() as db:
            row = db.execute("SELECT payload FROM observations WHERE id=? AND session_id=?", (observation_id, session_id)).fetchone()
        if row is None:
            raise ValueError("Observation is outside this session")
        payload = json.loads(row["payload"])
        if time.time() - payload["time"] > 15:
            raise BokkioStaleSnapshot("Observation expired; observe again")
        return payload

    def _dispatch_scope(self, tool, args, session_id):
        # Lock acquisition may wait while a session expires or a grant changes.
        # Revalidate immediately after acquiring the shared desktop lock.
        from .windows_capture import CaptureError
        try:
            scope = self._session(session_id)
            self._validate(tool, args, scope, session_id=session_id)
            if "observation_id" in args:
                self._get_observation(session_id, args["observation_id"])
            return scope
        except (ValueError, BokkioStaleSnapshot) as error:
            raise CaptureError("dispatch_scope_changed", str(error), dispatched=0) from error

    def call(self, tool, arguments=None, *, session_id=None, operation_id=None):
        arguments = json.loads(canonical(arguments if arguments is not None else {}))
        operation_id = operation_id or identifier()
        request_hash = digest({"tool": tool, "arguments": arguments, "session_id": session_id})
        started = time.monotonic()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            context = db.execute("SELECT policy,owner FROM sessions WHERE id=?", (session_id,)).fetchone()
            task_id = json.loads(context["policy"]).get("task_id") if context and context["owner"] == identity() else None
            existing = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            if existing:
                if existing["hash"] != request_hash:
                    self.store.emit("request.rejected", session_id=session_id, operation_id=operation_id,
                                    data={"reason": "operation_id_request_mismatch", "actor": identity(), "tool": tool,
                                          "request_sha256": request_hash, "attempt_id": identifier(), "dispatched_this_attempt": False}, db=db)
                    return {"status": "denied", "operation_id": operation_id, "error": "operation_id request mismatch", "dispatched": False}
                if existing["status"] not in {"approval_required"}:
                    cached_session = existing["session_id"]
                    if tool not in {"capabilities", "session.close"}:
                        try:
                            self._session(cached_session)
                        except ValueError as error:
                            self.store.emit("request.rejected", session_id=cached_session, operation_id=operation_id,
                                            data={"reason": "cached_session_unavailable", "tool": tool,
                                                  "request_sha256": request_hash, "attempt_id": identifier(),
                                                  "original_status": existing["status"], "dispatched_this_attempt": False}, db=db)
                            return {"status": "denied", "session_id": cached_session, "operation_id": operation_id,
                                    "dispatched": False, "original_status": existing["status"],
                                    "error_code": "cached_session_unavailable", "error": str(error)}
                    self.store.emit("request.cached", session_id=cached_session, operation_id=operation_id,
                                    data={"tool": tool, "request_sha256": request_hash, "attempt_id": identifier(),
                                          "original_status": existing["status"], "dispatched_this_attempt": False}, db=db)
                    return json.loads(existing["result"]) if existing["result"] else {
                        "status": "completion_unknown", "operation_id": operation_id, "dispatched": "unknown",
                        "error": "Operation already claimed; inspect audit evidence, do not redispatch"}
                db.execute("UPDATE operations SET status='running' WHERE id=?", (operation_id,))
            else:
                db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)", (operation_id, session_id, tool, request_hash,
                           canonical(arguments), "running", None, time.time(),))
            self.store.emit("request.received", session_id=session_id, operation_id=operation_id,
                            data={"tool": tool, "request_sha256": request_hash, "input": summarize(arguments),
                                  "actor": identity(), "platform": platform.system(), "architecture": platform.machine(),
                                  "device_id": digest({"node": platform.node(), "platform": platform.system()})[:20],
                                  "trace_id": session_id or operation_id, "attempt_id": identifier(),
                                  "task_id": task_id or arguments.get("task_id", operation_id) if isinstance(arguments, dict) else operation_id,
                                  "parent_operation": parent_operation.get() or os.environ.get("BOKKIO_PARENT_OPERATION"),
                                  "workflow_step": workflow_step.get()}, db=db)
        claimed = False
        try:
            if tool not in TOOLS:
                raise ValueError("Unknown tool")
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object")
            from .tool_schema import validate
            validate(tool, arguments)
            scope = self._session(session_id) if tool not in {"session.open", "capabilities"} else None
            self._validate(tool, arguments, scope, session_id=session_id)
            write = tool in WRITE_TOOLS
            if write and self.policy["require_approval"]:
                with self.store.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    approval = db.execute("SELECT * FROM approvals WHERE operation_id=?", (operation_id,)).fetchone()
                    if approval is None:
                        approval_id = identifier()
                        db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)", (approval_id, operation_id, request_hash,
                                   "pending", time.time(), time.time() + 300, None, None))
                        self.store.emit("approval.requested", session_id=session_id, operation_id=operation_id,
                                        data={"approval_id": approval_id, "request_sha256": request_hash}, db=db)
                        result = {"status": "approval_required", "operation_id": operation_id, "approval_id": approval_id, "dispatched": False}
                    elif approval["status"] == "pending" and approval["expires"] > time.time():
                        result = {"status": "approval_required", "operation_id": operation_id, "approval_id": approval["id"], "dispatched": False}
                    elif approval["hash"] != request_hash or approval["status"] != "approved" or approval["expires"] <= time.time():
                        result = {"status": "denied", "operation_id": operation_id, "error": "Approval is not valid", "dispatched": False}
                        if approval["expires"] <= time.time() and approval["status"] != "expired":
                            db.execute("UPDATE approvals SET status='expired' WHERE id=?", (approval["id"],))
                            self.store.emit("approval.expired", session_id=session_id, operation_id=operation_id,
                                            data={"approval_id": approval["id"]}, db=db)
                    else:
                        db.execute("UPDATE approvals SET status='consumed' WHERE id=?", (approval["id"],))
                        self.store.emit("approval.consumed", session_id=session_id, operation_id=operation_id,
                                        data={"approval_id": approval["id"], "actor": approval["actor"],
                                              "wait_ms": round((time.time()-approval["created"])*1000, 3)}, db=db)
                        result = None
                if result is not None:
                    return self._finish(tool, session_id, operation_id, result, started)
            self.store.emit("execution.intent", session_id=session_id, operation_id=operation_id,
                            data={"tool": tool, "request_sha256": request_hash, "policy_sha256": digest(self.policy), "write": write})
            claimed = True
            parent_token = parent_operation.set(operation_id)
            try:payload = self._execute(tool, arguments, scope, session_id, operation_id)
            finally:parent_operation.reset(parent_token)
            if tool == "session.open":
                session_id = payload["session_id"]
                with self.store.connect() as db:
                    db.execute("UPDATE operations SET session_id=? WHERE id=?", (session_id, operation_id))
                    db.execute("UPDATE events SET session_id=? WHERE operation_id=?", (session_id, operation_id))
            queued = tool in {"code.run", "process.run", "capability.invoke"}
            verification = payload.get("verification") if isinstance(payload, dict) else None
            verified = verification == "confirmed" or isinstance(verification, dict) and verification.get("status") == "confirmed"
            result = {"status": "queued" if queued else "verified" if write and verified else "executed" if write else "completed", "operation_id": operation_id,
                      "session_id": session_id, "dispatched": write and not queued, "result": payload}
        except Exception as error:
            details = getattr(error, "details", {})
            uncertain = isinstance(error, BokkioCompletionUnknown) or (claimed and tool in WRITE_TOOLS and not isinstance(error, BokkioStaleSnapshot))
            if details.get("dispatched") in (False, 0):
                uncertain = False
            result = {"status": "completion_unknown" if uncertain else "failed" if claimed else "denied",
                      "operation_id": operation_id, "session_id": session_id, "error": str(error),
                      "error_type": type(error).__name__, "error_code": getattr(error, "code", None),
                      **({"error_details": details} if details else {}),
                      "dispatched": details.get("dispatched", "unknown" if uncertain else False)}
        return self._finish(tool, session_id, operation_id, result, started)

    def _finish(self, tool, session_id, operation_id, result, started):
        try:
            with self.store.connect() as db:
                db.execute("UPDATE operations SET status=?,result=? WHERE id=? AND status IN ('running','approval_required')", (result["status"], canonical(result), operation_id))
                self.store.emit("execution.finished", session_id=session_id, operation_id=operation_id,
                                data={"tool": tool, "channel": tool.split(".")[0], "status": result["status"],
                                      "dispatched": result.get("dispatched"), "error_type": result.get("error_type"),
                                      "duration_ms": round((time.monotonic()-started)*1000, 3)}, db=db)
        except (OSError, sqlite3.Error):
            uncertain = result.get("dispatched") not in (False, 0) or result["status"] == "queued"
            return {"status": "completion_unknown" if uncertain else "failed", "operation_id": operation_id,
                    "session_id": session_id, "dispatched": "unknown" if uncertain else False,
                    "error_code": "audit_result_unavailable", "error": "Result could not be persisted; inspect the original operation before retrying"}
        return result

    def _validate(self, tool, args, scope, session_id=None):
        if tool == "capability.get":
            from .capability_registry import contract
            contract(args["capability_id"])
        if tool == "capability.list":
            from .capability_registry import discover
            discover(self.policy, scope, args.get("module_id"))
        if tool == "capability.invoke":
            from .capability_registry import prepare
            prepare(self, scope, args)
        if tool.startswith("workflow."):
            if tool in {"workflow.run", "workflow.resume"} and not (scope['write'] and self.policy['write']):
                raise ValueError('Workflow writes are not granted')
            if 'workflow_id' in args and args['workflow_id'] not in self.policy.get('workflows',[]):
                raise ValueError('Workflow is outside administrator grants')
        if tool == "desktop.act" and "expected_value" in args and args["action"] != "type":
            raise ValueError("expected_value is only valid for type; omit it for set_value")
        if tool == "desktop.act" and args["action"] in {"type", "set_value", "select_text"} and "value" not in args:
            raise ValueError("Text action requires a literal value")
        if tool == "desktop.pixel" and args["action"] == "type" and "value" not in args:
            raise ValueError("Pixel type requires a literal value")
        if tool == "browser.act" and ((args["action"] == "fill" and "value" not in args) or (args["action"] == "press" and "key" not in args)):
            raise ValueError("Browser fill/press requires value/key")
        if tool == "session.open":
            requested = args.get("apps", self.policy["apps"])
            if not isinstance(requested, list) or not {str(v) for v in requested}.issubset({str(v) for v in self.policy["apps"]}):
                raise ValueError("Requested apps exceed administrator policy")
            if "task_id" in args and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args["task_id"]):
                raise ValueError("task_id must be a bounded opaque identifier")
        if tool in WRITE_TOOLS and not (scope["write"] and self.policy["write"]):
            raise ValueError("Writes are not granted")
        if tool == "desktop.launch":
            from .app_launch import launch_grant
            launch_grant(self.policy, args["app"], scope)
        if tool.startswith("desktop.") and tool not in {"desktop.list", "desktop.launch"}:
            app = self._app(scope, args.get("app"), args.get("window"))
            if tool in {"desktop.act", "desktop.input", "desktop.pixel"}:
                observation = self._get_observation(session_id, args["observation_id"])
                if observation["app"] != app or observation["window"] != args.get("window"):
                    raise ValueError("Action scope differs from observation")
                required = "snapshot" if tool in {"desktop.act","desktop.input"} else "metadata"
                if required not in observation:
                    raise ValueError("Action requires the matching native/pixel observation type")
        if tool in {"code.run", "process.run"}:
            if not scope["trusted_host"] or not self.policy["trusted_host"]:
                raise ValueError("trusted-host execution is not granted")
            cwd = self._path(scope, args.get("cwd", scope["paths"][0] if scope["paths"] else "."))
            if not cwd.is_dir():
                raise ValueError("Working directory is not available")
            timeout, size = args.get("timeout", 30), args.get("output_limit", 65536)
            if type(timeout) not in {int, float} or not 0 < timeout <= 300 or type(size) is not int or not 1 <= size <= 1000000:
                raise ValueError("Invalid execution budget")
            if tool == "code.run":
                if not isinstance(args.get("code"), str) or not 0 < len(args["code"]) <= 100000:
                    raise ValueError("Code must be a bounded nonempty string")
                if args.get("language", "python") not in ({"python", "powershell"} if os.name == "nt" else {"python", "shell"}):
                    raise ValueError("Language unavailable on this platform")
            elif not isinstance(args.get("argv"), list) or not args["argv"] or any(not isinstance(v, str) for v in args["argv"]):
                raise ValueError("Process requires an argv list")
        if tool == "evidence.check":
            self._path(scope, args["path"])
        if tool == "artifact.read":
            with self.store.connect() as db:
                row = db.execute("SELECT path FROM artifacts WHERE id=? AND session_id=?", (args["artifact_id"], session_id)).fetchone()
            if row is None:
                raise ValueError("Artifact outside session")
            path = Path(row["path"]).resolve()
            if self.store.root not in path.parents:
                self._path(scope, str(path))
        if tool.startswith("browser."):
            if not scope["origins"]:
                raise ValueError("Browser origins are not granted")
            from .browser_driver import origin
            if not set(scope["origins"]).issubset({origin(u) for u in self.policy["origins"]}):
                raise ValueError("Browser origin grant was revoked")
            if tool == "browser.open":
                from .browser_driver import origin
                if origin(args["url"]) not in scope["origins"]:
                    raise ValueError("URL outside authorized origins")
            if tool == "browser.act" and origin(args["expected_url"]) not in scope["origins"]:
                raise ValueError("Expected browser page outside granted origins")
        if tool in {"audit.query", "metrics.summary", "approval.status"} and args.get("session_id") not in {None, args.get("_session_id")}:
            raise ValueError("Audit queries cannot choose another session")

    def _execute(self, tool, args, scope, session_id, operation_id):
        if tool in {"module.list", "capability.list", "capability.get", "capability.invoke"}:
            from . import capability_registry as registry
            if tool == "module.list":return registry.modules(self.policy, scope)
            if tool == "capability.list":return registry.discover(self.policy, scope, args.get("module_id"))
            if tool == "capability.get":
                c = registry.contract(args["capability_id"])
                return {**c, "enabled": registry.enabled(self.policy, scope), "health": registry.health()}
            request = registry.prepare(self, scope, args)
            self.store.emit("capability.resolved", session_id=session_id, operation_id=operation_id,
                            data={"capability": request["capability"], "implementation": request["implementation"],
                                  "contract_sha256": args["contract_sha256"]})
            from .executor import launch
            return {**launch(self.store, session_id, operation_id, request),
                    "capability": request["capability"], "implementation": request["implementation"]}
        if tool.startswith('workflow.'):
            from .runtime_workflow import WorkflowLibrary, RuntimeWorkflowRunner
            from .sdk import Client
            import threading
            library = WorkflowLibrary(self.store.root/'workflows')
            if tool == 'workflow.list':
                return [d for d in library.list() if d['id'] in self.policy.get('workflows',[])]
            if tool == 'workflow.get':return library.get(args['workflow_id'])
            runner = RuntimeWorkflowRunner(Client(self,session_id),self.store.root/'workflow-runs')
            if tool == 'workflow.run':
                run = runner.start(library.get(args['workflow_id']),args.get('mode','headed'),**{k:args[k] for k in ('parameters','repeat','speed') if k in args})
            else:
                run = runner.load(args['run_id'])
                if run['session_id'] != session_id or run['workflow']['id'] not in self.policy.get('workflows',[]):
                    raise ValueError('Workflow run is outside this session or revoked')
            if tool == 'workflow.status':return run
            if tool == 'workflow.cancel':runner.cancel(run['id']);return {'run_id':run['id'],'cancel_requested':True}
            if not hasattr(self,'_workflow_threads'):self._workflow_threads = {}
            if any(t.is_alive() for t in self._workflow_threads.values()):raise ValueError('A workflow is already active')
            def execute():
                try:runner.resume(run['id'])
                except Exception as error:
                    value=runner.load(run['id']);value.update(status='failed',error={'message':str(error)})
                    runner._save(value)
            from contextvars import copy_context
            execution_context=copy_context()
            thread=threading.Thread(target=lambda:execution_context.run(execute),daemon=True)
            self._workflow_threads[run['id']]=thread;thread.start()
            return {'run_id':run['id'],'status':'running'}
        if tool == "capabilities":
            return {"schema": "bokkio.runtime.v1", "platform": platform.system(), "architecture": platform.machine(),
                    "tools": sorted(TOOLS), "browser_installed": importlib.util.find_spec("playwright") is not None,
                    "execution_mode": "trusted-host", "approval": self.policy["require_approval"],
                    "module_discovery": {"schema": "bokkio.capability.v1", "summary_tool": "module.list", "detail_tool": "capability.get"},
                    "legacy_cli": "Legacy act/run/workflow are outside this enterprise boundary; use bokkio-runtime"}
        if tool == "session.open":
            granted_apps = [str(v) for v in self.policy["apps"]]
            requested = [str(v) for v in args.get("apps", granted_apps)]
            if not set(requested).issubset(set(granted_apps)):
                raise ValueError("Requested apps exceed administrator policy")
            bindings = {}
            if requested:
                for app in self._native_call("apps"):
                    if str(app["pid"]) in requested or app["name"] in requested:
                        windows = self.policy.get("windows", {}).get(app["name"], [])
                        bindings[str(app["pid"])] = {"name": app["name"], "birth": self.birth_probe(app["pid"]), "windows": windows}
                if any(not any(v in {pid, info["name"]} for pid, info in bindings.items()) for v in requested):
                    raise ValueError("Requested application is not running")
            from .browser_driver import origin
            paths = [str(Path(p).expanduser().resolve()) for p in self.policy["paths"]]
            policy = {**self.policy, "paths": paths, "bindings": bindings, "origins": [origin(u) for u in self.policy["origins"]],
                      "task_id": args.get("task_id", operation_id)}
            session_id = identifier()
            ttl = args.get("ttl", self.policy["ttl"])
            if type(ttl) is not int or not 1 <= ttl <= min(self.policy["ttl"], 86400):
                raise ValueError("Invalid session TTL")
            with self.store.connect() as db:
                db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (session_id, time.time(), time.time()+ttl,
                           identity(), canonical(policy), "open"))
                self.store.emit("session.opened", session_id=session_id, operation_id=operation_id,
                                data={"actor": identity(), "task_id": policy["task_id"], "grant_sha256": digest(policy), "ttl": ttl}, db=db)
            return {"session_id": session_id, "expires_in": ttl, "apps": bindings, "paths": paths, "origins": policy["origins"],
                    "task_id": policy["task_id"], "write": policy["write"], "trusted_host": policy["trusted_host"]}
        if tool == "session.close":
            close_session(self.store,session_id)
            return {"closed": True}
        if tool == "desktop.list":
            return [{"pid": int(pid), **info} for pid, info in scope["bindings"].items()]
        if tool == "desktop.windows":
            pid=self._app(scope,args["app"],args.get("window"));rows=self._native_call("windows",pid);allowed=scope["bindings"][pid]["windows"]
            return [n for n in rows if not allowed or n["name"] in allowed]
        if tool == "desktop.launch":
            from .app_launch import launch_grant, ensure_running
            grant = launch_grant(self.policy, args["app"], scope)
            receipt = ensure_running(grant,**({'background':True} if args.get('background') else {}))
            pid = str(receipt["pid"])
            scope["bindings"][pid] = {"name": grant["name"], "birth": self.birth_probe(int(pid)),
                                      "windows": self.policy.get("windows", {}).get(grant["name"], [])}
            with self.store.connect() as db:
                db.execute("UPDATE sessions SET policy=? WHERE id=?", (canonical(scope), session_id))
            return receipt
        if tool == "desktop.observe":
            app = self._app(scope, args["app"], args.get("window"))
            snapshot = self._native_call("snapshot", app, args.get("window"))
            if args.get("window") is not None and not any(
                    args["window"] in {n.get("name"), n.get("ref"), n.get("platform_data", {}).get("native_stable_id")}
                    for n in snapshot["windows"]):
                raise ValueError("Observation requires an exact window title/ref, not a substring")
            payload = {"time": time.time(), "app": app, "window": args.get("window"), "snapshot": snapshot}
            observation_id = self._observation(session_id, payload)
            limit = args.get("max_nodes", 240)
            if type(limit) is not int or not 1 <= limit <= 2000:
                raise ValueError("max_nodes must be 1..2000")
            from .selector import flatten
            nodes = list(flatten(snapshot["windows"]))
            full = self.store.root / (identifier() + ".json")
            full.write_text(canonical(snapshot), encoding="utf-8")
            artifact = self._artifact(session_id, operation_id, full, "application/json")
            def bounded(value):
                if isinstance(value, str):
                    return value[:4000]
                if isinstance(value, dict):
                    return {k: bounded(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [bounded(v) for v in value[:100]]
                return value
            budget = args.get("max_bytes", 256000)
            if type(budget) is not int or not 1000 <= budget <= 2000000:
                raise ValueError("max_bytes must be 1000..2000000")
            public, used, text_truncated = [], 0, False
            for node in nodes[:limit]:
                shallow = {k: v for k, v in node.items() if k != "children"}
                entry = bounded(shallow)
                size = len(canonical(entry).encode())
                if used + size > budget:
                    break
                public.append(entry)
                used += size
                text_truncated = text_truncated or entry != shallow
            return {"observation_id": observation_id, "snapshot_sha256": tree_digest(snapshot["windows"]),
                    "app": snapshot["app"], "nodes": public, "source": "native_accessibility", "content_trust": "untrusted_app_data",
                    "total_nodes": len(nodes), "truncated": len(public) < len(nodes) or text_truncated,
                    "snapshot_artifact": artifact, "returned_bytes": used}
        if tool == "desktop.act":
            observation = self._get_observation(session_id, args["observation_id"])
            app = self._app(scope, args["app"], args.get("window"))
            if observation["app"] != app or observation["window"] != args.get("window"):
                raise ValueError("Action scope differs from observation")
            from .desktop_input import desktop_lock
            with desktop_lock():
                self._dispatch_scope(tool, args, session_id)
                return self._native_call("perform", app, args["action"], ref=args["ref"], window=args.get("window"),
                                            _session_guard=session_id,
                                            _dispatch_request=(tool, args),
                                            expected_snapshot=tree_digest(observation["snapshot"]["windows"]),
                                            **{k: args[k] for k in ("value", "direction", "amount", "expected_value", "background") if k in args})
        if tool == "desktop.input":
            from .anchored_input import perform_anchored
            from .desktop_input import desktop_lock
            observation=self._get_observation(session_id,args['observation_id'])
            app=self._app(scope,args['app'],args.get('window'))
            with desktop_lock():
                self._dispatch_scope(tool,args,session_id)
                fresh=self._native_call('snapshot',app,args.get('window'))
                if args['action'] in {'key','type','replace_text'}:
                    from .anchored_input import prepare_target
                    target,_=prepare_target(observation['snapshot'],fresh,{**args,'app':str(app)})
                    if target.get('role') not in {'window','application'} and target.get('state',{}).get('focused') is not True:
                        if 'focus' not in target.get('actions',[]):raise ValueError('Keyboard target cannot receive focus')
                        self._native_call('perform',app,'focus',ref=target['ref'],window=args.get('window'),expected_snapshot=tree_digest(fresh['windows']))
                        fresh=self._native_call('snapshot',app,args.get('window'))
                return self._native_executor.submit(lambda:perform_anchored(int(app),args.get('window'),observation['snapshot'],fresh,{**args,'app':str(app)},cancel_path=self.store.root/'session-cancellations'/session_id)).result()
        if tool == "desktop.activate":
            from .desktop_input import desktop_lock, activate
            app = self._app(scope, args["app"], args["window"])
            with desktop_lock():
                self._dispatch_scope(tool, args, session_id)
                return activate(int(app), args["window"], args.get("window_id"))
        if tool == "desktop.capture":
            from .desktop_input import capture
            app = self._app(scope, args["app"], args.get("window"))
            metadata, png = capture(int(app), args.get("window_id"), args.get("window"))
            if args.get("window") is not None and metadata.get("window_title") != args["window"]:
                raise ValueError("Captured window differs from the authorized exact title")
            image = self.store.root / (identifier() + ".png")
            image.write_bytes(png)
            artifact = self._artifact(session_id, operation_id, image, "image/png")
            observation_id = self._observation(session_id, {"time": time.time(), "app": app, "window": args.get("window"),
                                                           "metadata": metadata, "artifact_id": artifact["artifact_id"]})
            return {"observation_id": observation_id, "metadata": metadata, "artifact": artifact}
        if tool == "desktop.pixel":
            from .desktop_input import desktop_lock, perform
            observation = self._get_observation(session_id, args["observation_id"])
            app = self._app(scope, args["app"], args.get("window"))
            if observation["app"] != app or observation["window"] != args.get("window"):
                raise ValueError("Pixel scope differs from capture")
            with self.store.connect() as db:
                image = db.execute("SELECT path FROM artifacts WHERE id=? AND session_id=?", (observation["artifact_id"], session_id)).fetchone()
            with desktop_lock():
                self._dispatch_scope(tool, args, session_id)
                return perform(observation["metadata"], Path(image["path"]).read_bytes(), args["action"], args["x"], args["y"], args.get("value"))
        if tool in {"code.run", "process.run", "job.get", "job.cancel"}:
            from . import executor
            if tool.endswith(".run"):
                cwd = self._path(scope, args.get("cwd", scope["paths"][0] if scope["paths"] else "."))
                return executor.launch(self.store, session_id, operation_id, {**args, "cwd": str(cwd)})
            return (executor.cancel if tool == "job.cancel" else executor.get)(self.store, args["job_id"], session_id)
        if tool.startswith("browser."):
            from .browser_driver import call
            from .desktop_input import desktop_lock
            action = "open" if tool == "browser.open" else "observe" if tool == "browser.observe" else args.get("action")
            with desktop_lock():
                self._dispatch_scope(tool, args, session_id)
                return call(self.store, session_id, {**args, "action": action}, scope["origins"])
        if tool == "evidence.check":
            path = self._path(scope, args["path"])
            if not path.is_file():
                return {"passed": False, "exists": False}
            if path.stat().st_size > 20000000:
                raise ValueError("Evidence file exceeds 20 MB")
            record = self._artifact(session_id, operation_id, path)
            passed = record["sha256"] == args["sha256"] if "sha256" in args else True
            checks = {"exists": True, "sha256": record["sha256"]}
            if "csv_rows" in args or "csv_columns" in args:
                import csv
                with path.open(encoding="utf-8", newline="") as file:
                    rows = list(csv.DictReader(file))
                checks.update(csv_rows=len(rows), csv_columns=list(rows[0]) if rows else [])
                passed = passed and ("csv_rows" not in args or len(rows) == args["csv_rows"])
                passed = passed and ("csv_columns" not in args or checks["csv_columns"] == args["csv_columns"])
            return {"passed": passed, "checks": checks, "artifact": record}
        if tool == "artifact.read":
            with self.store.connect() as db:
                row = db.execute("SELECT * FROM artifacts WHERE id=? AND session_id=?", (args["artifact_id"], session_id)).fetchone()
            if row is None:
                raise ValueError("Artifact outside session")
            path = Path(row["path"]).resolve()
            if self.store.root not in path.parents:
                self._path(scope, str(path))
            limit = args.get("max_bytes", 1000000)
            if type(limit) is not int or not 1 <= limit <= 20000000:
                raise ValueError("Invalid artifact budget")
            if path.stat().st_size > limit:
                raise ValueError("Artifact exceeds requested budget")
            import base64
            data = path.read_bytes()
            if __import__("hashlib").sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("Artifact changed since registration")
            return {"artifact_id": row["id"], "mime": row["mime"], "sha256": row["sha256"], "data_base64": base64.b64encode(data).decode()}
        if tool == "audit.query":
            return self.store.query(session_id=session_id, **args)
        if tool == "audit.export":
            format = args.get("format", "jsonl")
            target = self.store.root / (identifier() + "." + format)
            target.write_text(self.store.export(format, session_id=session_id), encoding="utf-8")
            return {"format": format, "artifact": self._artifact(session_id, operation_id, target,
                                                                 "text/csv" if format == "csv" else "application/x-ndjson")}
        if tool == "events.follow":
            after, wait = args.get("after", 0), args.get("wait_ms", 1000)
            if type(wait) is not int or not 0 <= wait <= 5000:
                raise ValueError("wait_ms must be 0..5000")
            deadline = time.monotonic() + wait / 1000
            while True:
                events = self.store.query(session_id=session_id, after=after, limit=args.get("limit", 100))
                if events or time.monotonic() >= deadline:
                    return {"events": events, "cursor": events[-1]["seq"] if events else after}
                time.sleep(.05)
        if tool == "metrics.summary":
            return self.store.stats(session_id)
        if tool == "approval.status":
            return self.store.approvals(args.get("approval_id"), session_id=session_id)
        raise ValueError("Unsupported operation")
